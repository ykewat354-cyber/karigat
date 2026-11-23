from pathlib import Path
import json

def save(root, files):
    if not isinstance(files,list) or len(files)>100: raise ValueError('Invalid file list.')
    pending = {}
    root = root.resolve()
    for item in files:
        if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not isinstance(item.get('content'),str):
            raise ValueError('Expected text files with path and content.')
        rel = Path(item['path'])
        if not rel.parts or rel.is_absolute() or any(p.startswith('.') or not p.isprintable() for p in rel.parts):
            raise ValueError('Unsafe file path.')
        dest = root/rel
        if dest.resolve()!=dest or dest.exists() or dest in pending: raise ValueError('Conflicting or unsafe destination.')
        pending[dest]=item['content']
    if any(parent in pending for dest in pending for parent in dest.parents): raise ValueError('File/directory conflict.')
    for dest, content in pending.items():
        dest.parent.mkdir(exist_ok=True, parents=True)
        with dest.open('x', encoding='utf8') as f: f.write(content)

def check(root, paths=None):
    results = []
    for dest in sorted(root.rglob('*') if paths is None else paths):
        if not dest.is_file(): continue
        if dest.suffix not in ('.json','.py'): continue
        try:
            text = dest.read_text()
            if dest.suffix == '.py': compile(text,str(dest),'exec')
            else: json.loads(text)
            result = 'PASS'
        except (SyntaxError,ValueError) as e: result = f'FAIL: {e}'
        results.append(f'{result} syntax {dest.relative_to(root)}')
    return results
