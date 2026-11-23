"""Three short prompts with independent, frozen, local acceptance checks."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

CASES=[
    ('Make stock.json with total quantities: pen 2, tape 1, pen 5.',[{'op':'json_equals','path':'stock.json','value':{'pen':7,'tape':1}}]),
    ('Make scores.csv with columns name,points: Jo 8 and Kim 13, highest first.',[{'op':'csv_rows','path':'scores.csv','value':[['name','points'],['Kim','13'],['Jo','8']]}]),
    ('Draw a compass rose in north.svg.',[{'op':'xml_root','path':'north.svg','value':'svg'}]),
]

def main():
    p=argparse.ArgumentParser();p.add_argument('--provider',default='openrouter');p.add_argument('--fallback',action='append',default=[]);args=p.parse_args()
    root=Path(tempfile.mkdtemp(prefix='karigat-pilot-',dir=Path.cwd())); results=[]
    for i,(prompt,checks) in enumerate(CASES):
        wd=root/str(i);wd.mkdir(); spec=wd/'checks.json';spec.write_text(json.dumps(checks))
        r=subprocess.run(['karigat','run','--provider',args.provider,*[a for f in args.fallback for a in ('--fallback',f)],'--checks',str(spec),prompt],cwd=wd,capture_output=True,text=True)
        results.append(dict(prompt=prompt,exit=r.returncode,out=r.stdout,events=r.stderr));(root/'results.json').write_text(json.dumps(results,indent=2))
    print(root, [r['exit'] for r in results]);return int(any(r['exit'] for r in results))

if __name__=='__main__':sys.exit(main())
