"""Run both detailed prompts against the installed harness with identical call budgets."""
import getpass
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

here=Path(__file__).resolve().parent
prompts=json.loads((here/'prompts.json').read_text())
env=os.environ.copy()
if not env.get('OPENROUTER_API_KEY') and sys.stdin.isatty():
    env['OPENROUTER_API_KEY']=getpass.getpass('OpenRouter test key (hidden; this run only): ')
if not env.get('OPENROUTER_API_KEY'):sys.exit('BLOCKED: OPENROUTER_API_KEY missing; no generation attempted.')
base=Path(tempfile.mkdtemp(prefix='karigat-stress-')); print(base,flush=True)
results={}
for case,prompt in prompts.items():
    wd=base/case;wd.mkdir(); checks=wd/'required.json';names=['index.html','lantern.obj'] if case=='lantern' else ['ledger.sql']
    checks.write_text(json.dumps([dict(op='exists',path=n) for n in names]));args=['karigat','run','--quick','--provider','openrouter','--checks',str(checks),'--verify',shlex.join([sys.executable,'-I',str(here/'grade.py'),case])]
    args+=['--share-check-feedback']
    if case=='lantern':args+=['--journey',str(here/'lantern-journey.json')]
    p=subprocess.run(args+[prompt],env=env,cwd=wd,capture_output=True,text=True);results[case]=dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr);(base/'results.json').write_text(json.dumps(results,indent=2));print(case,p.returncode,flush=True)
sys.exit(int(any(r['exit'] for r in results.values())))
