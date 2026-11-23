"""Derive a small build plan and independent executable checks from a short brief."""
from concurrent.futures import ThreadPoolExecutor
import json
from .evidence import contract


def design(brief, ask, plan_route, test_route):
    instruction=('Choose acceptance checks justified by the request. Return only JSON: '
                 '{"checks":[],"journey":"one real-world action to verify"}. Checks are data: '
                 '{"path":"requested filename","op":"exists|json_equals|csv_rows|xml_root|text_contains","value":...}. '
                 'Do not invent a filename, schema, copy or facts. Use [] for behavior these checks cannot establish.\n')
    with ThreadPoolExecutor(max_workers=2) as pool:
        planner=pool.submit(ask,plan_route,'Brief implementer handoff: smallest complete deliverable, main interaction and one failure case. Up to 100 words.\n'+brief)
        tester=pool.submit(ask,test_route,instruction+brief)
        try: plan=planner.result()[:2400]
        except (ValueError,OSError): plan=''
        try:
            raw=tester.result().strip();raw='\n'.join(raw.splitlines()[1:-1]) if raw.startswith('```') else raw
            result=json.loads(raw)
            return plan,contract(result['checks']),str(result['journey'])[:500]
        except (ValueError,OSError,KeyError,TypeError): return plan,[],'Independent acceptance design unavailable'
