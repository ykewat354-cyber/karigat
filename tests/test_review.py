import unittest
from karigat.webreview import inspect_html


class WebReview(unittest.TestCase):
    def test_incomplete_copy_and_unwired_actions(self):
        issues = inspect_html('<p>...</p><button>Start Now</button><a href="#missing">Join</a>', '')
        self.assertEqual(len(issues), 3)

    def test_native_navigation_and_supplied_price(self):
        self.assertEqual(inspect_html('<a href="#plans">See plans</a><section id="plans">$29/month</section>', '$29/month'), [])

    def test_unverified_business_terms(self):
        self.assertTrue(inspect_html('<p>Call: 555-0100</p><p>$29/month</p>', 'make a website'))

    def test_cli_preserves_both_attempts_and_rechecks_repair(self):
        import json
        import tempfile
        from pathlib import Path
        from contextlib import chdir
        from unittest.mock import patch
        from karigat.cli import main
        def response(html):
            return json.dumps({'summary':'fixture','files':[{'path':'index.html','content':html}]})
        for repaired, expected in [('<p>...</p>',1),('<p>Open training session</p>',0)]:
            with tempfile.TemporaryDirectory() as folder, chdir(folder), patch('karigat.cli.ask', side_effect=[response('<button>Join</button>'),response(repaired)]) as api:
                self.assertEqual(main(['run','--quick','--provider','openrouter','fixture']),expected)
                self.assertIn('button has no apparent action',api.call_args.args[1])
                self.assertEqual(len(list(Path('.').glob('*/index.html'))),2)
