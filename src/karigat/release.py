"""Release-facing commands for inspecting and integrating a candidate."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

from .journal import Journal
from .project import project_root, shortlist
from .runner import discover, execute
from .workspace import git


def register(sub):
    sub.add_parser('init',help='Create a user configuration file')
    context=sub.add_parser('context',help='Find relevant tracked source files locally');context.add_argument('task');context.add_argument('--repo',type=Path,default=Path.cwd())
    commands=sub.add_parser('commands',help='List candidate build/test commands without executing them');commands.add_argument('folder',type=Path,nargs='?',default=Path.cwd())
    status=sub.add_parser('status');status.add_argument('id')
    diff=sub.add_parser('diff');diff.add_argument('id')
    apply=sub.add_parser('apply',help='Integrate a reviewed, passing patch into a clean original repository');apply.add_argument('id')
    serve=sub.add_parser('serve',help='Serve a generated directory on loopback');serve.add_argument('folder',type=Path);serve.add_argument('--port',type=int,default=8000)


def handle(args):
    if args.cmd=='init':
        from .settings import init
        print(init())
    elif args.cmd=='context':
        repo=project_root(args.repo)
        if not repo: raise ValueError('No Git repository at that location')
        for name in shortlist(repo,args.task):print(name)
    elif args.cmd=='commands':
        for cmd in discover(project_root(args.folder) or args.folder):print(shlex.join(cmd))
    elif args.cmd=='doctor':
        for cmd in ('karigat','git','python','node','proot-distro'):print(f'{cmd}: {shutil.which(cmd) or "unavailable"}')
        print('Journal:',Journal().path)
        return None
    elif args.cmd in ('status','diff','apply'):
        row=Journal().load(args.id)
        if args.cmd=='status':print(row['id'],row['status'],'·',len(row['attempts']),'attempt records')
        elif args.cmd=='diff':print(row.get('diff','No Git diff recorded.'))
        else:
            project=row.get('base');diff=row.get('diff')
            if row['status']!='checks-passed' or not project or not diff:raise ValueError('No passing project patch to apply')
            repo=project['repo']
            if git(repo,'rev-parse','HEAD').decode().strip()!=project['base'] or git(repo,'status','--porcelain'):raise ValueError('Original HEAD or working tree changed; inspect the diff manually')
            for flags in (['--check'],[]):
                p=subprocess.run(['git','-C',repo,'apply',*flags,'-'],input=diff.encode(),capture_output=True)
                if p.returncode: raise ValueError('Git could not apply the recorded diff')
            print('Applied reviewed changes to',repo)
    elif args.cmd=='serve':
        from functools import partial
        from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
        root=args.folder.resolve()
        if not root.is_dir() or root==Path.home():raise ValueError('Select a generated artifact directory')
        class Handler(SimpleHTTPRequestHandler):
            def send_head(self):
                dest=Path(self.translate_path(self.path)).resolve()
                if not dest.is_relative_to(root) or any(s.startswith('.') for s in dest.relative_to(root).parts):self.send_error(403);return None
                return super().send_head()
            def list_directory(self,path):self.send_error(403)
        with ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(root))) as server:
            print(f'http://127.0.0.1:{server.server_port}/',flush=True);server.serve_forever()
    else:return None
    return 0


def baseline(project, commands):
    if not project or not commands:return []
    with tempfile.TemporaryDirectory() as tmp:
        tree=Path(tmp)/'baseline';git(project['repo'],'worktree','add','--detach',str(tree),project['base'])
        try:return [execute(tree,argv) for argv in commands]
        finally:git(project['repo'],'worktree','remove','--force',str(tree))
