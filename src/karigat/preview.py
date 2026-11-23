from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import threading


def audit(folder, png, journey=None):
    root=folder.resolve()
    entry=root/'index.html'
    if not entry.is_file():
        pages=[p for p in root.iterdir() if p.suffix.lower() in ('.html','.htm') and p.is_file()]
        if len(pages)!=1:raise ValueError('Expected an unambiguous HTML entry page')
        entry=pages[0]
    from urllib.parse import quote
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
        def send_head(self):
            if not Path(self.translate_path(self.path)).resolve().is_relative_to(root):
                self.send_error(403);return None
            return super().send_head()
        def list_directory(self,path):self.send_error(403)
    with ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(root))) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        env={k:os.environ[k] for k in ('PATH','HOME','PREFIX','TMPDIR','LANG','ANDROID_ROOT','ANDROID_DATA') if k in os.environ}
        try:return subprocess.run(['node',str(Path(__file__).with_name('browser.mjs')),f'http://127.0.0.1:{server.server_port}/{quote(entry.name)}',str(png),*([str(journey)] if journey else [])],env=env,timeout=55).returncode
        finally:server.shutdown()
