import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch
from karigat.cli import main
from karigat.evidence import sql_rows


class CalibrationPack(unittest.TestCase):
    def test_grader_can_enable_but_not_disable_constraints(self):
        self.assertEqual(sql_rows('pragma foreign_keys=on;','','select 1'),[[1]])
        with self.assertRaises(sqlite3.DatabaseError):sql_rows('pragma foreign_keys=off;','','select 1')

    def test_failing_behavior_reaches_repair_only(self):
        responses=[json.dumps({'summary':'fixture','files':[{'path':'count.txt','content':v}]}) for v in ('0','3')]
        with tempfile.TemporaryDirectory() as d,chdir(d),patch.dict('os.environ',{'XDG_STATE_HOME':d,'XDG_CONFIG_HOME':d}),patch('karigat.cli.ask',side_effect=responses) as ask:
            Path('grade.py').write_text("from pathlib import Path\nimport sys\nif Path('count.txt').read_text()!='3':sys.exit('FAIL: repeated input lost')")
            rc=main(['run','--quick','--provider','openrouter','--verify',f'{sys.executable} {d}/grade.py','--share-check-feedback','count the inputs'])
            first,repair=[c.args[1] for c in ask.call_args_list];self.assertEqual(rc,0)
            self.assertIn('observable result',first);self.assertNotIn('repeated input lost',first);self.assertIn('FAIL: repeated input lost',repair)
