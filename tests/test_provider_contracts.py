import json
import os
import unittest
from unittest.mock import patch
from karigat.cloud import ROUTES,ask,completion,request_for


class ProviderContracts(unittest.TestCase):
    def test_accept_only_answer_text_and_request_correct_host(self):
        samples={'openrouter':('openrouter.ai',{'choices':[{'message':{'content':'answer'}}]}),'ollama':('ollama.com',{'message':{'content':'answer'}}),'gemini':('generativelanguage.googleapis.com',{'candidates':[{'content':{'parts':[{'thought':True,'text':'private reasoning'},{'text':'answer'}]}}]})}
        for provider,(host,wire) in samples.items():
            with self.subTest(provider=provider):
                req=request_for(provider,'Return only JSON: {}','fixture');self.assertEqual(req.host,host);self.assertTrue(req.full_url.startswith('https://'));self.assertNotIn('fixture',req.full_url)
                self.assertEqual(completion(provider,wire),'answer');self.assertTrue(json.loads(req.data));
                with self.assertRaises(ValueError):completion(provider,{})

    def test_nonverified_billing_prevents_request(self):
        for provider in ('ollama','gemini'):
            with patch.dict(os.environ,{ROUTES[provider][0]:'fixture'},clear=True),patch('karigat.cloud.build_opener') as net:
                with self.assertRaisesRegex(ValueError,'free-only'):ask(provider,'ping')
                net.assert_not_called()
