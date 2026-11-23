"""Trusted, data-only checks. Never execute a command from a model reply."""
import csv
import json
import sqlite3
import time
from pathlib import Path
from xml.etree import ElementTree


def contract(raw):
    if not isinstance(raw, list) or len(raw) > 100:
        raise ValueError('Checks must be a list of at most 100 objects.')
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get('path'),str): raise ValueError('Invalid check path')
        path = Path(item['path'])
        if not path.parts or path.is_absolute() or any(x.startswith('.') for x in path.parts): raise ValueError('Unsafe check path')
        op=item.get('op')
        if op not in ('exists','json_equals','text_contains','csv_rows','xml_root','sql_query'): raise ValueError('Unknown check')
        if op!='exists' and 'value' not in item: raise ValueError('Missing check value')
        if op in ('text_contains','xml_root') and not isinstance(item['value'],str): raise ValueError('Expected string')
        if op=='sql_query' and not isinstance(item.get('query'),str):raise ValueError('Expected a local evaluator query')
    return raw


def verify(root, checks):
    evidence=[]
    for item in contract(checks):
        path=root/item['path']; op=item['op']; expected=item.get('value')
        passed=path.is_file() and path.resolve().is_relative_to(root.resolve())
        detail=''
        if passed and op!='exists':
            try:
                text=path.read_text()
                if op=='json_equals':
                    actual=json.loads(text);passed=actual==expected
                    if type(actual) is not type(expected):detail=f' (expected {type(expected).__name__}, found {type(actual).__name__})'
                elif op=='text_contains': passed=expected in text
                elif op=='csv_rows': passed=list(csv.reader(text.splitlines()))==expected
                elif op=='xml_root': passed=ElementTree.fromstring(text).tag.split('}')[-1]==expected
                elif op=='sql_query': passed=sql_rows(text,item.get('setup',''),item['query'])==expected
            except (ValueError,OSError,ElementTree.ParseError,csv.Error,sqlite3.Error): passed=False
        evidence.append(f'{"PASS" if passed else "FAIL"} {op}: {item["path"]}{detail}')
    return evidence


def sql_rows(script,setup,query):
    from contextlib import closing
    with closing(sqlite3.connect(':memory:')) as db:
        db.execute('pragma temp_store=memory');db.execute('pragma max_page_count=2048')
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,1_000_000);db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED,0)
        expire=time.monotonic()+2;db.set_progress_handler(lambda: int(time.monotonic()>expire),1000)
        denied={sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_PRAGMA,sqlite3.SQLITE_CREATE_VTABLE,sqlite3.SQLITE_DROP_VTABLE}
        def authorize(action,a,b,*_):
            if action==sqlite3.SQLITE_PRAGMA and a.lower()=='foreign_keys' and (b or '').upper() in ('1','ON','TRUE'):return sqlite3.SQLITE_OK
            if action in denied or (action==sqlite3.SQLITE_FUNCTION and b in ('load_extension','writefile','readfile','zeroblob','randomblob')):return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        db.set_authorizer(authorize)
        db.executescript(script);db.executescript(setup);return [list(row) for row in db.execute(query).fetchmany(1000)]
