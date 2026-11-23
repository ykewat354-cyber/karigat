"""One coordinator, at most two parallel file owners, one trusted materializer."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath


def decode(raw):
    text=raw.strip()
    if text.startswith('```') and text.endswith('```'):text='\n'.join(text.splitlines()[1:-1])
    return json.loads(text)


def build(route,prompt,ask):
    context=prompt.split('direct answer.\n',1)[-1]
    plan=decode(ask(route,'Act as coordinator. Allocate every needed file to exactly one of 1 or 2 workers. For two requested files assign one to each. Keep independent work parallel. Specify shared interfaces precisely. Return only JSON: {"contract":"...","jobs":[{"task":"...","paths":["name"]}]}. For a text-only answer assign one worker with empty paths. The following is the task; do not implement it yourself.\n'+context))
    if not isinstance(plan,dict) or not isinstance(plan.get('contract'),str):raise ValueError('Invalid team contract')
    jobs=plan.get('jobs');owned=set()
    if not isinstance(jobs,list) or not 1<=len(jobs)<=2:raise ValueError('Expected one or two owners')
    for job in jobs:
        if not isinstance(job,dict) or not isinstance(job.get('task'),str) or not isinstance(job.get('paths'),list):raise ValueError('Invalid team job')
        for p in job['paths']:
            if not isinstance(p,str) or not p or PurePosixPath(p).is_absolute() or str(PurePosixPath(p))!=p or any(s.startswith('.') for s in p.split('/')) or p in owned:raise ValueError('Invalid or overlapping ownership')
            owned.add(p)
    def worker(job):
        packet={'contract':plan['contract'],'assignment':job}
        if len(job['paths'])==1:
            path=job['paths'][0]
            raw=ask(route,'Generate the literal contents of just '+path+'. No envelope or markdown fences. Other files have different owners. Do not seed example data unless requested. You cannot choose a destination path.\nShared contract and assignment:\n'+json.dumps(packet)+'\nTask context:\n'+prompt.split('direct answer.\n',1)[-1]+'\nOutput only the file contents of '+path+'.').strip()
            if raw.startswith('```') and raw.endswith('```'):raw='\n'.join(raw.splitlines()[1:-1])
            return {'summary':'Generated '+path,'files':[{'path':path,'content':raw}]}
        data=decode(ask(route,'You are one implementation worker. The overall brief below is context, not your scope. Your sole deliverable is the final assignment. Do not implement siblings, add examples or seed application state unless explicitly requested. Return only JSON: {"summary":"...","files":[{"path":"exact assigned path","content":"complete text"}]}.\nOVERALL CONTEXT:\n'+prompt+'\nEND CONTEXT. Implement exactly these assigned paths, one entry per path:\n'+json.dumps(packet)))
        if not isinstance(data,dict) or not isinstance(data.get('summary'),str) or not isinstance(data.get('files'),list):raise ValueError('Invalid worker answer')
        files=data['files'];paths=[]
        for item in files:
            if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not isinstance(item.get('content'),str):raise ValueError('Invalid worker file')
            paths.append(item['path'])
        if sorted(paths)!=sorted(job['paths']):raise ValueError('Worker violated ownership contract')
        return data
    with ThreadPoolExecutor(max_workers=2) as pool:parts=list(pool.map(worker,jobs))
    return json.dumps({'summary':'\n'.join(p['summary'] for p in parts),'files':[f for p in parts for f in p['files']]}),plan
