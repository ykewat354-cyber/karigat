import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from .cloud import PROVIDERS as ROUTES, ask
from .artifacts import save, check
from .webreview import inspect_html
from .evidence import contract, verify
from .journal import Journal
from .workspace import capture, materialize, changes
from .design import design
from . import release
from .runner import execute
from .project import project_root,shortlist
from . import settings
from importlib.resources import files as resources
import shlex

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if '--jsonl' in argv:
        from contextlib import redirect_stdout,redirect_stderr
        from .terminal import Events
        argv.remove('--jsonl');dest=sys.stdout
        with redirect_stdout(Events(dest,'output')), redirect_stderr(Events(dest,'activity')):return main(argv)
    parser = argparse.ArgumentParser(prog='karigat', description='K> Cloud-only creation harness')
    from importlib.metadata import version
    parser.add_argument('--version',action='version',version='Karigat '+version('karigat'))
    sub = parser.add_subparsers(dest='cmd')
    sub.add_parser('providers'); sub.add_parser('doctor')
    release.register(sub)
    browser=sub.add_parser('browser-check');browser.add_argument('folder',type=Path);browser.add_argument('--screenshot',type=Path,required=True)
    browser.add_argument('--journey',type=Path,help='Local JSON list of fill, click, reload and visible text checks')
    run = sub.add_parser('run'); run.add_argument('task'); run.add_argument('--provider',choices=ROUTES)
    run.add_argument('--checks',type=Path,help='Local acceptance checks, not included in generation prompt')
    run.add_argument('--quick',action='store_true',help='Skip planner and independent test designer')
    run.add_argument('--browser',action='store_true',help='Inspect trusted HTML deliverables in isolated-profile mobile Chromium')
    run.add_argument('--journey',type=Path,help='Frozen browser actions to check during generation and repair')
    run.add_argument('--repo',type=Path,help='Trusted Git repository; work from committed HEAD')
    run.add_argument('--edit',action='append',default=[],help='Tracked path to include and allow editing (relative to repo root)')
    run.add_argument('--auto-context',action='store_true',help='Allow uploading up to six matching tracked source files from this repository')
    run.add_argument('--verify',action='append',default=[],metavar='COMMAND',help='Run this command on trusted baseline and generated candidates (shell disabled)')
    run.add_argument('--share-check-feedback',action='store_true',help='Include bounded FAIL: lines from approved verifier output in hosted repair requests')
    run.add_argument('--pack',choices=['general','change','create'])
    run.add_argument('--team',action='store_true',help='Delegate initial build to a coordinator and up to two parallel file owners')
    run.add_argument('--fallback',action='append',choices=ROUTES,default=[],help='Allow this additional hosted route for this task')
    sub.add_parser('runs'); sub.add_parser('report').add_argument('id');sub.add_parser('resume').add_argument('id')
    run.add_argument('--planner',choices=ROUTES); run.add_argument('--context',type=Path,action='append',default=[],help='Text file to send to the selected cloud providers')
    args = parser.parse_args(argv)
    try: result=release.handle(args)
    except (OSError,ValueError) as exc: print('Karigat:',exc,file=sys.stderr);return 1
    except KeyboardInterrupt:return 130
    if result is not None:return result
    if args.cmd in ('providers','doctor'):
        for name,(var,model,_) in ROUTES.items():
            if var is None:
                print(f'{name:10} {model:20} via OpenCode CLI (explicit selection)');continue
            print(f'{name:10} {model:20} {"key present" if os.getenv(var) else "set "+var}')
        return 0
    try:
        if args.cmd=='browser-check':
            from .preview import audit
            return audit(args.folder,args.screenshot,args.journey)
        if args.cmd=='runs':
            for row in Journal().recent(): print(row['id'],row['status'],row['task'][:70])
            return 0
        if args.cmd=='report':
            record=Journal().load(args.id);record.pop('checkpoint',None)
            print(json.dumps(record,ensure_ascii=False,indent=2)); return 0
        if args.cmd=='resume':
            journal=Journal()
            with journal.lease(args.id):
                row=journal.load(args.id)
                if not row.get('checkpoint'): raise ValueError('No pending checkpoint; see karigat report '+args.id)
                return drive(journal,row)
        if args.cmd is None:
            if not sys.stdin.isatty(): parser.print_help(); return 0
            from .terminal import interactive
            return interactive(main)
        if not args.task.strip(): raise ValueError('Enter a task.')
        prefs=settings.read();args.planner=args.planner or prefs.get('planner')
        route = args.provider or prefs.get('provider') or next((p for p,(key,_,_) in ROUTES.items() if key and os.getenv(key)),None)
        if not route: raise ValueError('No hosted provider configured. Run karigat providers.')
        brief = args.task
        project=None
        if args.repo or args.edit or args.auto_context:
            repo=project_root(args.repo or Path.cwd())
            if not repo:raise ValueError('No Git repository found')
            selected=list(dict.fromkeys(args.edit+(shortlist(repo,args.task) if args.auto_context else [])))
            project,refs=capture(repo,selected)
            brief+='\nSelected source files at '+project['base']+':\n'+json.dumps(refs)
        for path in args.context:
            if not path.is_file() or path.stat().st_size>64000: raise ValueError('Context must be a text file under 64 KB.')
            brief += '\nREFERENCE '+path.name+'\n'+path.read_text()
        if len(brief)>128000: raise ValueError('Task and references exceed 128k characters.')
        supplied=brief
        frozen=contract(json.loads(args.checks.read_text())) if args.checks else []
        journey=''
        if not args.quick and not args.checks:
            print(f'PLAN + CHECK DESIGN · 2 active · {args.planner or route} / {route}',file=sys.stderr)
            plan,frozen,journey=design(brief,ask,args.planner or route,route)
            if plan: brief+='\nImplementation plan:\n'+plan
        elif args.planner:
            print(f'PLAN {args.planner}',file=sys.stderr)
            brief += '\nPLAN\n'+ask(args.planner,'Give a concise implementation plan and observable success checks for:\n'+brief)
        journal=Journal(); row=journal.start(task=args.task,provider=route,base=project,journey=journey)
        commands=[shlex.split(c) for c in args.verify]
        if any(not cmd for cmd in commands):raise ValueError('Empty verification command')
        row['baseline']=release.baseline(project,commands)
        print('Run:',row['id'],file=sys.stderr)
        routes=list(dict.fromkeys([route,*args.fallback]))
        print(f'BUILD {route} / {ROUTES[route][1]}',file=sys.stderr)
        prompt='Fulfil the following free-form request. Return only JSON: {"summary":"...","files":[{"path":"relative/name","content":"complete text"}]}. Choose deliverables appropriate to the request; use summary alone for a direct answer.\n'+brief
        pack=args.pack or prefs.get('pack') or ('change' if project else 'general'); row['pack']=pack
        prompt+='\nWorkflow guidance:\n'+resources('karigat').joinpath('packs',pack+'.txt').read_text()
        prompt+='\n'+resources('karigat').joinpath('packs','behavior.txt').read_text()
        steps=json.loads(args.journey.read_text()) if args.journey else None
        if args.journey and (not isinstance(steps,list) or not 1<=len(steps)<=40 or any(not isinstance(s,dict) or s.get('op') not in ('first-screen','fill','click','text','reload','checked','painted','turntable') for s in steps)):raise ValueError('Invalid browser journey')
        row['checkpoint']=dict(prompt=prompt,brief=supplied,cwd=str(Path.cwd()),routes=routes,frozen=frozen,attempt=0,original_pages=[],browser=args.browser or bool(steps),steps=steps)
        row['checkpoint']['commands']=commands
        row['checkpoint']['team']=args.team
        row['checkpoint']['share_feedback']=args.share_check_feedback
        with journal.lease(row['id']):journal.store(row);return drive(journal,row)
    except (OSError,ValueError,EOFError) as e:
        print(f'Karigat: {e}',file=sys.stderr); return 1
    except KeyboardInterrupt:
        print('Interrupted.',file=sys.stderr); return 130

def drive(journal,row):
        cp=row['checkpoint'];project=row['base'];frozen=cp['frozen'];brief=cp['brief'];routes=cp['routes']
        original_pages={Path(p) for p in cp['original_pages']};prompt=cp['prompt']
        for attempt in range(cp['attempt'],2):
            ready=cp.get('pending')
            if ready: raw,candidate=ready['raw'],ready['provider'];data=json.loads(raw)
            for candidate in routes:
                if ready: candidate=ready['provider'];break
                try:
                    if cp.get('team') and attempt==0:
                        from .team import build
                        raw,row['team_plan']=build(candidate,prompt,ask)
                    else:raw = ask(candidate,prompt).strip()
                    if raw.startswith('```') and raw.endswith('```'): raw = '\n'.join(raw.splitlines()[1:-1])
                    data=json.loads(raw)
                    if not isinstance(data,dict) or not isinstance(data.get('summary'),str): raise ValueError('Invalid deliverable response.')
                    break
                except (OSError, ValueError) as e:
                    row['attempts'].append(dict(provider=candidate,error=str(e))); journal.store(row)
                    print(f'WAIT {candidate}: {e}',file=sys.stderr)
            else:
                row['status']='blocked'; journal.store(row); return 1
            root=Path(ready['root']) if ready else Path(tempfile.mkdtemp(prefix='karigat-run-',dir=None if project else cp['cwd']))
            print(f'Output: {root}')
            files=data.get('files',[])
            if ready and any(root.iterdir()):
                if not all((root/x['path']).resolve().is_relative_to(root) and (root/x['path']).is_file() and (root/x['path']).read_text()==x['content'] for x in files): raise ValueError('Interrupted or modified workspace; original artifacts retained. Inspect before starting a fresh run.')
            else:
                cp['pending']=dict(raw=raw,root=str(root),provider=candidate);journal.store(row);materialize(root,files,project)
            paths=[root/x['path'] for x in files]; checks=check(root,paths)+verify(root,frozen)
            diff=changes(root,project,files)
            if project: row['diff']=diff
            command_results=[execute(root,cmd) for cmd in cp.get('commands',[])]
            for result in command_results:
                checks.append(f'{result["status"]} command {shlex.join(result["argv"])} (exit {result["exit"]})')
                if result['status']=='FAIL' and cp.get('share_feedback'):
                    checks.extend(line[:300] for line in result['tail'].splitlines() if line.startswith('FAIL: '))
            pages={p.relative_to(root) for p in paths if p.suffix.lower() in ('.html','.htm')}
            for path in sorted(pages):
                checks.extend('FAIL '+str(path)+': '+issue for issue in inspect_html((root/path).read_text(),brief))
            if cp.get('browser') and (Path('index.html') in pages or (len(pages)==1 and len(next(iter(pages)).parts)==1)):
                from .preview import audit
                png=Path(str(root)+'.mobile.png'); journey_path=None
                if cp.get('steps'):
                    journey_path=Path(str(root)+'.journey.json');journey_path.write_text(json.dumps(cp['steps']))
                rc=audit(root,png,journey_path)
                checks.append(('PASS' if rc==0 else 'FAIL' if rc==1 else 'UNCHECKED')+' mobile viewport, heading and sampled navigation')
                row['screenshot']=str(png)
                details=Path(str(png)+'.json')
                if details.exists():
                    report=json.loads(details.read_text());layout=report.get('layout',[])
                    checks.extend(f'FAIL viewport {v["width"]}: {msg}' for v in layout for msg in v['issues'])
                    for s in report.get('steps',[]):
                        checks.append(f'{"PASS" if s["ok"] else "FAIL"} browser {s["op"]} {s.get("selector", "")} {s.get("measurement", "")}')
                if cp.get('steps') and (rc not in (0,1) or not details.exists()):checks.append('FAIL required browser evidence unavailable')
            elif cp.get('steps'): checks.append('FAIL required browser journey: no index.html to test')
            renamed_entry=(len(original_pages)==len(pages)==1 and Path('index.html') in pages and bool(cp.get('steps')) and any(c.startswith('PASS browser ') for c in checks))
            if original_pages-pages and not renamed_entry: checks.append('FAIL: repair removed HTML deliverable(s)')
            failures=[c for c in checks if c.startswith('FAIL')]
            row['attempts'].append(dict(provider=candidate,output=str(root),commands=command_results,checks=checks,stage='repair' if attempt else 'build'));row['status']='checking'
            if not failures or attempt: break
            original_pages=pages
            print('REPAIR (1/1): '+'; '.join(failures)[:2000],file=sys.stderr)
            prompt+='\nRepair the previous deliverable. Return ALL complete files in the same JSON format. Preserve useful features and address the observed failures. Do not invent unavailable business facts or imply a form sent data when it did not.\nPrevious output:\n'+raw+'\nObserved failures:\n'+'\n'.join(failures)
            cp.pop('pending',None);cp.update(prompt=prompt,attempt=1,original_pages=[str(p) for p in pages]);journal.store(row)
        print(''.join(c for c in data['summary'] if c.isprintable() or c=='\n'))
        for line in checks: print(line)
        print('UNCHECKED: end-to-end behavior')
        row.pop('checkpoint',None);row['status']='failed' if failures else ('checks-passed' if checks and all(c.startswith('PASS') for c in checks) else 'unchecked');journal.store(row)
        return int(bool(failures) or any(c.startswith('UNCHECKED') for c in checks))
