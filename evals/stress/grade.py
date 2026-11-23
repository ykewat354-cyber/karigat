"""Independent mesh/ledger checks; read text artifacts only. Run from candidate cwd."""
import collections
import math
from pathlib import Path
import sqlite3
import sys
from karigat.evidence import sql_rows


def lantern():
    vertices=[]; groups=collections.defaultdict(list); name=None
    for line in Path('lantern.obj').read_text().splitlines():
        fields=line.partition('#')[0].split()
        if not fields: continue
        if fields[0]=='v':
            v=tuple(map(float,fields[1:4])); assert len(v)==3 and all(math.isfinite(x) for x in v),'invalid vertex';vertices.append(v)
        elif fields[0]=='o': name=' '.join(fields[1:]).lower()
        elif fields[0]=='f':
            assert len(fields)==4,'face is not a triangle';idx=[int(s.split('/')[0]) for s in fields[1:]]
            ids=[n-1 if n>0 else len(vertices)+n for n in idx];assert all(0<=n<len(vertices) for n in ids),'invalid vertex index';groups[name].append(ids)
    bounds=[]
    for name in ['base','glass','cap']:
        faces=groups[name]; assert faces,f'missing {name} geometry'; edges=collections.Counter();vol=0;ys=[]
        for ids in faces:
            a,b,c=[vertices[n] for n in ids];ys.extend([a[1],b[1],c[1]])
            for i,j in zip(ids,ids[1:]+ids[:1]):edges[(vertices[i],vertices[j])]+=1
            v=[b[i]-a[i] for i in range(3)];w=[c[i]-a[i] for i in range(3)]
            cross=[v[(i+1)%3]*w[(i+2)%3]-v[(i+2)%3]*w[(i+1)%3] for i in range(3)];assert any(abs(n)>1e-10 for n in cross),f'{name}: degenerate face';vol+=sum(a[i]*cross[i] for i in range(3))
        assert all(n==1 and edges[(j,i)]==1 for (i,j),n in edges.items()),f'{name}: open surface or inconsistent winding'; assert abs(vol)>1e-8,f'{name}: zero volume';bounds.append((min(ys),max(ys)))
    a,b,c=bounds;assert a[1]<=b[0]+1e-5 and b[1]<=c[0]+1e-5,'pieces not vertically stacked';assert b[1]-b[0]>a[1]-a[0]+c[1]-c[0],'glass too short'


def returns():
    schema=Path('ledger.sql').read_text(); seed="INSERT INTO sales(receipt,qty,unit_paise) VALUES ('A',3,125),('B',1,99);"; first="INSERT INTO returns(event_id,receipt,qty) VALUES ('x','A',2);"; last="INSERT INTO returns(event_id,receipt,qty) VALUES ('y','A',1);"; query='SELECT receipt,refunded_paise FROM refunds ORDER BY receipt'
    assert sql_rows(schema,seed+first,query)==[['A',250],['B',0]],'partial refund or untouched sale wrong'
    errors=[]
    try:
        if sql_rows(schema,seed+first+last+first,query)!=[['A',375],['B',0]]:errors.append('refund replay changed balance')
    except sqlite3.IntegrityError:errors.append('refund replay rejected')
    for event in ["('z','A',2)","('z','A',0)","('z','A',-1)","('z','missing',1)"]:
        try:sql_rows(schema,seed+first+'INSERT INTO returns(event_id,receipt,qty) VALUES '+event,query)
        except sqlite3.IntegrityError:continue
        errors.append('unknown receipt accepted' if 'missing' in event else 'invalid quantity accepted')
    if errors:raise ValueError('; '.join(dict.fromkeys(errors)))


if __name__=='__main__':
    try:{'returns':returns,'lantern':lantern}[sys.argv[1]]()
    except (OSError,ValueError,IndexError,AssertionError,sqlite3.Error) as e:sys.exit('FAIL: '+str(e))
    print('PASS: '+sys.argv[1]+' artifact checks')
