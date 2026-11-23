"""Bounded, local-only project discovery and source ranking."""
import re
from pathlib import Path
from .workspace import git


def project_root(folder):
    folder=folder.resolve()
    return next((p for p in (folder,*folder.parents) if (p/'.git').exists()),None)


def shortlist(repo, task):
    terms=set(re.findall(r'[a-z0-9_]{3,}',task.lower()))-{'the','and','please','make','this','with','from','that'}
    ranks=[]
    for raw in git(repo,'ls-files','-z').split(b'\0')[:4000]:
        if not raw:continue
        name=raw.decode(errors='replace');rel=Path(name)
        if any(p.startswith('.') or p in ('node_modules','vendor','dist','build') for p in rel.parts):continue
        if rel.suffix.lower() not in {'.py','.js','.ts','.tsx','.jsx','.go','.rs','.java','.kt','.css','.html','.md','.sql'}:continue
        if any(t in name.lower() for t in ('credential','secret','private_key')):continue
        path=repo/rel
        if path.resolve()!=path or not path.is_file() or path.stat().st_size>64000:continue
        with path.open('rb') as f:body=f.read(12000).decode(errors='ignore').lower()
        score=sum(4*(t in name.lower())+(t in body) for t in terms)
        if score:ranks.append((-score,name))
    return [name for _,name in sorted(ranks)[:6]]
