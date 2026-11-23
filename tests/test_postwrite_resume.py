import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PostWriteRecovery(unittest.TestCase):
    def test_sigkill_after_materialize_resumes_without_second_candidate(self):
        child='''
import json,os,signal
from karigat import cli
orig=cli.materialize
def interrupt(*args):
    orig(*args)
    os.kill(os.getpid(),signal.SIGKILL)
cli.materialize=interrupt
cli.ask=lambda *args:json.dumps({'summary':'ok','files':[{'path':'count.json','content':'3'}]})
cli.main(['run','--quick','--provider','openrouter','--checks','spec.json','count'])
'''
        with tempfile.TemporaryDirectory() as d:
            env={**os.environ,'XDG_STATE_HOME':d,'XDG_CONFIG_HOME':d};env.pop('OPENROUTER_API_KEY',None)
            root=Path(d);(root/'spec.json').write_text('[{"op":"json_equals","path":"count.json","value":3}]')
            p=subprocess.run([sys.executable,'-c',child],cwd=d,env=env,capture_output=True,text=True);self.assertEqual(p.returncode,-signal.SIGKILL,p.stderr)
            run=p.stderr.split('Run: ')[1].splitlines()[0]; file,=root.glob('*/count.json');before=file.stat().st_mtime_ns
            p=subprocess.run(['karigat','resume',run],env=env,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);self.assertIn('PASS json_equals',p.stdout)
            self.assertEqual(list(root.glob('*/count.json')),[file]);self.assertEqual(file.stat().st_mtime_ns,before)
