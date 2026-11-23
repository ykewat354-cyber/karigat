"""Discover likely checks without executing them; run explicit argv on trusted code."""
import json
import os
import selectors
import signal
import subprocess
import sys
import time


def discover(root):
    found = []
    manifest = root / 'package.json'
    if manifest.is_file() and not manifest.is_symlink() and manifest.stat().st_size < 512_000:
        try:
            scripts = json.loads(manifest.read_text()).get('scripts', {})
            found.extend(['npm', 'run', key] for key in ('test', 'build') if key in scripts)
        except (ValueError, AttributeError, TypeError):
            pass
    if (root / 'tests').is_dir():
        found.append([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'])
    if (root/'Cargo.toml').is_file(): found.append(['cargo','test','--offline'])
    if (root/'go.mod').is_file(): found.append(['go','test','./...'])
    return found


def execute(root, argv, timeout=60):
    started = time.monotonic()
    env = {k: os.environ[k] for k in ('PATH','HOME','PREFIX','LANG','TMPDIR','ANDROID_ROOT','ANDROID_DATA') if k in os.environ}
    result = dict(argv=argv, status='UNCHECKED', exit=None, tail='')
    try:
        p = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as e:
        result['tail']=str(e);return result
    tail = b''
    try:
        with p.stdout as stream, selectors.DefaultSelector() as sel:
            sel.register(stream, selectors.EVENT_READ)
            while True:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0: raise subprocess.TimeoutExpired(argv, timeout)
                if not sel.select(remaining): continue
                data=os.read(stream.fileno(),8192)
                if not data: break
                tail=(tail+data)[-4096:]
            result['exit']=p.wait(timeout=max(.001,timeout-(time.monotonic()-started)))
        result['status']='PASS' if result['exit']==0 else 'FAIL'
    except subprocess.TimeoutExpired:
        result['status']='FAIL';tail+=b'\nTimed out'
    finally:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.wait()
    result['tail']=''.join(ch for ch in tail.decode(errors='replace') if ch.isprintable() or ch=='\n')
    result['seconds']=round(time.monotonic()-started,3)
    return result
