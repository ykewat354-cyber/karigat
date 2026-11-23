import json
import os
import sys
import time


class Events:
    def __init__(self,stream,kind):self.stream=stream;self.kind=kind;self.buf=''
    def write(self,text):
        self.buf+=text
        while '\n' in self.buf:
            line,self.buf=self.buf.split('\n',1)
            if line:self.stream.write(json.dumps(dict(time=time.time(),kind=self.kind,message=line),ensure_ascii=False)+'\n');self.stream.flush()
        return len(text)
    def flush(self):self.stream.flush()
    def isatty(self):return False


def interactive(main):
    from .journal import Journal
    brand='K> KARIGAT'
    if sys.stdout.isatty() and 'NO_COLOR' not in os.environ:
        brand='\033[38;2;34;211;238mK> \033[38;2;167;139;250mKARIGAT\033[0m'
    print(brand+' · cloud only\nType a task, /models, /runs, /checks ID, /diff ID or /exit.')
    while True:
        try: text=input('K> ').strip()
        except (KeyboardInterrupt,EOFError):return 0
        if not text:continue
        if text=='/exit':return 0
        if text=='/models':main(['providers']);continue
        if text=='/runs':main(['runs']);continue
        if text.startswith(('/diff ','/checks ')):
            cmd,key=text.split(maxsplit=1)
            try:
                r=Journal().load(key);print(r.get('diff','No Git diff.') if cmd=='/diff' else json.dumps([a.get('checks',[]) for a in r['attempts']],indent=2))
            except ValueError as e:print(e)
            continue
        if text.startswith('/resume '):main(['resume',text.split(maxsplit=1)[1]]);continue
        if text.startswith('/'): print('/models /runs /checks ID /diff ID /resume ID /exit');continue
        main(['run',text])
