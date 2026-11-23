import json,threading,unittest
from karigat.team import build

class Team(unittest.TestCase):
    def test_parallel_owners(self):
        barrier=threading.Barrier(2,timeout=3)
        def ask(route,prompt):
            if prompt.startswith('Act as coordinator'):return json.dumps({'contract':'utf8','jobs':[{'task':n,'paths':[n]} for n in ['a','b']]})
            barrier.wait();return 'content'
        data,_=build('fixture','Test',ask);self.assertEqual([f['path'] for f in json.loads(data)['files']],['a','b'])
    def test_extra_worker_file_rejected(self):
        replies=iter(['{"contract":"x","jobs":[{"task":"answer","paths":[]}]}','{"summary":"x","files":[{"path":"extra","content":"x"}]}'])
        with self.assertRaisesRegex(ValueError,'ownership'):build('fixture','q',lambda *args:next(replies))
