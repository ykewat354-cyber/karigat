import json
import os
from pathlib import Path
import sqlite3
import uuid
from contextlib import closing
from contextlib import contextmanager
import fcntl


class Journal:
    def __init__(self):
        base=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'karigat'
        base.mkdir(mode=0o700, parents=True,exist_ok=True)
        self.path=base/'runs.sqlite'
        with self.connect() as db: db.execute('create table if not exists runs(id text primary key, payload text not null)');db.commit()

    def connect(self):
        return closing(sqlite3.connect(self.path,timeout=10))

    def store(self, row):
        with self.connect() as db: db.execute('insert or replace into runs values (?,?)',(row['id'],json.dumps(row)));db.commit()

    def start(self, **fields):
        row=dict(id=uuid.uuid4().hex[:12],status='started',attempts=[],**fields); self.store(row); return row

    def load(self, key):
        with self.connect() as db: hit=db.execute('select payload from runs where id=?',(key,)).fetchone()
        if not hit: raise ValueError('Unknown run ID')
        return json.loads(hit[0])

    def recent(self):
        with self.connect() as db: return [json.loads(x[0]) for x in db.execute('select payload from runs order by rowid desc limit 25')]

    @contextmanager
    def lease(self, key):
        self.load(key)
        with (self.path.parent / (key+'.lock')).open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('Run already active in another terminal') from None
            yield
