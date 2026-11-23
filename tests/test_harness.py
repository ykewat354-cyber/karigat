import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class HarnessTests(unittest.TestCase):
    def test_cloud_hosts_even_with_local_environment(self):
        from karigat.cloud import ROUTES, request_for
        from urllib.parse import urlsplit
        with patch.dict(os.environ, {'OLLAMA_HOST':'http://localhost:11434'}):
            self.assertEqual({urlsplit(request_for(k,'task','dummy').full_url).hostname for k in ROUTES},
                             {'ollama.com','generativelanguage.googleapis.com','openrouter.ai'})

    def test_general_task_and_no_overwrite(self):
        from karigat.artifacts import save
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            files = [{'path':'glossary/terms.tsv','content':'word\tmeaning'}]
            save(root, files)
            with self.assertRaises(ValueError): save(root, files)
            self.assertEqual((root/'glossary/terms.tsv').read_text(),'word\tmeaning')

    def test_escape_rejected_before_any_write(self):
        from karigat.artifacts import save
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError): save(root,[{'path':'ok','content':'first'}, {'path':'../outside','content':'bad'}])
            self.assertFalse((root/'ok').exists())
