import json
from pathlib import Path
import tempfile
import unittest
from karigat.cloud import completion, request_for
from karigat.evidence import verify


class Calibration(unittest.TestCase):
    def test_sql_behavior_on_disposable_database(self):
        import sqlite3
        from karigat.evidence import sql_rows
        self.assertEqual(sql_rows('create table orders(id primary key);', 'insert or ignore into orders values(1),(1);','select count(*) from orders'),[[1]])
        with self.assertRaises(sqlite3.Error):sql_rows("attach database 'forbidden.db' as other;",'','select 1')
    def test_worktree_does_not_touch_original(self):
        from karigat.workspace import capture, materialize, changes, git
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)/'repo';repo.mkdir();git(repo,'init','-q');(repo/'a.txt').write_text('original');git(repo,'add','a.txt');git(repo,'-c','user.name=test','-c','user.email=test@example.org','commit','-qm','initial')
            project,refs=capture(repo,['a.txt']);self.assertEqual(refs['a.txt'],'original')
            root=Path(tmp)/'candidate'; files=[dict(path='a.txt',content='changed')]; materialize(root,files,project)
            self.assertIn('+changed',changes(root,project,files));self.assertEqual((repo/'a.txt').read_text(),'original')

    def test_blocked_run_resumes_with_frozen_checks(self):
        import os
        from contextlib import chdir
        from unittest.mock import patch
        from karigat.cli import main
        from karigat.journal import Journal
        with tempfile.TemporaryDirectory() as tmp, chdir(tmp), patch.dict(os.environ,{'XDG_STATE_HOME':tmp}):
            Path('checks').write_text('[{"op":"json_equals","path":"out.json","value":7}]')
            with patch('karigat.cli.ask',side_effect=ValueError('quota exhausted')): self.assertEqual(main(['run','--provider','openrouter','--checks','checks','task']),1)
            row=Journal().recent()[0]; self.assertEqual(row['status'],'blocked')
            with patch('karigat.cli.ask',return_value=json.dumps(dict(summary='ok',files=[dict(path='out.json',content='7')]))): self.assertEqual(main(['resume',row['id']]),0)
            self.assertEqual(Journal().load(row['id'])['status'],'checks-passed')

    def test_reasoning_without_answer_is_not_a_deliverable(self):
        with self.assertRaisesRegex(ValueError,'finish=length'):
            completion('openrouter',{'choices':[{'finish_reason':'length','message':{'reasoning':'unfinished','content':None}}]})

    def test_structured_output_requested_only_for_deliverables(self):
        for prompt,expected in [('Give a plan',False),('Return only JSON: {}',True)]:
            self.assertEqual('response_format' in json.loads(request_for('openrouter',prompt,'test').data),expected)

    def test_frozen_check_catches_semantics_not_just_syntax(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'data.json').write_text('{"count":4}')
            self.assertEqual(verify(root,[{'op':'json_equals','path':'data.json','value':{'count':5}}]),['FAIL json_equals: data.json'])
