"""Paired development pilot, not a leaderboard: keep results even on failure."""
import json,subprocess,tempfile,time
from pathlib import Path


def main():
    root=Path(tempfile.mkdtemp(prefix='team-pilot-')); results=[]
    cases=[('Produce inventory.json mapping each supplied item to stock, and stock.csv with item,stock rows sorted alphabetically. Kite 2, Cap 5, Kite 1.',[dict(path='inventory.json',op='json_equals',value={'Kite':3,'Cap':5}),dict(path='stock.csv',op='csv_rows',value=[['item','stock'],['Cap','5'],['Kite','3']])]),('Create records.sql defining tickets(id INTEGER PRIMARY KEY, minutes INTEGER NOT NULL CHECK(minutes>0)) and summary.json giving total_minutes for tickets of 8, 11 and 6 minutes.',[dict(path='records.sql',op='sql_query',setup='insert into tickets values(1,8),(2,11),(3,6);',query='select sum(minutes) from tickets',value=[[25]]),dict(path='summary.json',op='json_equals',value={'total_minutes':25})])]
    for i,(task,checks) in enumerate(cases):
        for mode in (('single','team') if i==0 else ('team','single')):
            wd=root/f'{i}-{mode}';wd.mkdir();(wd/'checks.json').write_text(json.dumps(checks));start=time.monotonic()
            p=subprocess.run(['karigat','run','--provider','chatgpt','--quick','--checks','checks.json',*(['--team'] if mode=='team' else []),task],cwd=wd,capture_output=True,text=True)
            results.append(dict(case=i,mode=mode,seconds=round(time.monotonic()-start,1),rc=p.returncode,stdout=p.stdout,stderr=p.stderr));(root/'results.json').write_text(json.dumps(results,indent=2));print(wd,p.returncode,results[-1]['seconds'],flush=True)
    return int(any(r['rc'] for r in results))

if __name__=='__main__':raise SystemExit(main())
