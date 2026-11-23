"""Prepare an isolated candidate tree for a user-selected Git revision."""
import os
from pathlib import Path
import subprocess
from .artifacts import save


def git(cwd,*args):
    env={k:v for k,v in os.environ.items() if k not in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE') and not k.endswith('_API_KEY')}
    proc=subprocess.run(['git','-c','core.hooksPath=/dev/null','-C',str(cwd),*args],capture_output=True,env=env)
    if proc.returncode: raise ValueError('Git operation failed: '+proc.stderr.decode(errors='replace')[:300])
    return proc.stdout


def capture(folder, selection):
    repo=Path(git(folder,'rev-parse','--show-toplevel').decode().strip()); base=git(repo,'rev-parse','HEAD').decode().strip()
    refs={}
    for name in selection:
        path=Path(name)
        if path.is_absolute() or not path.parts or any(p.startswith('.') for p in path.parts) or path.suffix.lower() in ('.key','.pem','.p12'): raise ValueError('Invalid selected source path')
        entry=git(repo,'ls-tree','-z',base,'--',str(path)); mode=entry.split(b' ',1)[0]
        if mode not in (b'100644',b'100755'): raise ValueError('Select a tracked regular file: '+name)
        if int(git(repo,'cat-file','-s',base+':'+str(path)))>64000: raise ValueError('Selected file too large')
        refs[str(path)]=git(repo,'show',base+':'+str(path)).decode()
    return dict(repo=str(repo),base=base,selected=list(refs)),refs


def materialize(root, files, project):
    if not project: save(root,files); return
    # Validate model paths/content in an empty directory before touching the tree.
    import tempfile
    with tempfile.TemporaryDirectory() as stage:
        save(Path(stage),files)
        git(project['repo'],'worktree','add','--detach',str(root),project['base'])
        for item in files:
            dest=root/item['path']
            if dest.resolve()!=dest or (dest.exists() and (item['path'] not in project['selected'] or not dest.is_file())):
                raise ValueError('Patch outside selected write scope: '+item['path'])
        for item in files:
            dest=root/item['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(item['content'])


def changes(root,project,files):
    if not project:return ''
    if files: git(root,'add','-N','--',*[x['path'] for x in files])
    return git(root,'diff','--no-ext-diff','--no-textconv','--').decode(errors='replace')
