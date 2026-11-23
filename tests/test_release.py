import tempfile
import unittest
from pathlib import Path
import os,sys
from unittest.mock import patch


class Release(unittest.TestCase):
    def test_fix_verified_in_worktree_and_explicitly_applied(self):
        import json
        from karigat.workspace import git
        from karigat.cli import main
        from karigat.journal import Journal
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'XDG_STATE_HOME':d,'XDG_CONFIG_HOME':d}):
            repo=Path(d)/'project';repo.mkdir();git(repo,'init','-q')
            (repo/'calc.py').write_text('def double(n): return n\n')
            (repo/'test_calc.py').write_text('from calc import double\nassert double(3)==6\n')
            git(repo,'add','.');git(repo,'-c','user.name=fixture','-c','user.email=a@example.invalid','commit','-qm','fixture')
            answer=json.dumps({'summary':'fixed double','files':[{'path':'calc.py','content':'def double(n): return 2*n\n'}]})
            with patch('karigat.cli.ask',return_value=answer):
                self.assertEqual(main(['run','--quick','--provider','openrouter','--repo',str(repo),'--edit','calc.py','--verify',sys.executable+' test_calc.py','fix double']),0)
            row=Journal().recent()[0]; self.assertEqual(row['baseline'][0]['status'],'FAIL');self.assertEqual(row['attempts'][-1]['commands'][0]['status'],'PASS')
            self.assertEqual((repo/'calc.py').read_text(),'def double(n): return n\n')
            (repo/'local-note').touch();self.assertEqual(main(['apply',row['id']]),1);(repo/'local-note').unlink()
            self.assertEqual(main(['apply',row['id']]),0);self.assertIn('2*n',(repo/'calc.py').read_text());git(repo,'worktree','remove','--force',row['attempts'][-1]['output'])

    def test_checks_discovered_but_run_only_when_selected(self):
        from karigat.runner import discover,execute
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'package.json').write_text('{"scripts":{"build":"false","test":"false"}}')
            self.assertIn(['npm','run','build'],discover(root))
            with patch.dict(os.environ,{'GEMINI_API_KEY':'private'}):
                r=execute(root,[sys.executable,'-c',"import os; assert 'GEMINI_API_KEY' not in os.environ;print('tested')"])
            self.assertEqual(r['status'],'PASS');self.assertIn('tested',r['tail'])
            self.assertEqual(execute(root,['no-such-karigat-command'])['status'],'UNCHECKED')
            self.assertEqual(execute(root,[sys.executable,'-c','import time;time.sleep(5)'],timeout=.1)['status'],'FAIL')
