import pickle,collections,csv,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/TN/')
res=pickle.load(open('/tmp/hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/hsfha_by.pkl','rb'))
dom={n:c.most_common(1)[0][0] for n,c in by.items() if c}
canon={}
for code,c in codeto.items():
    st='('+('TN' if code.startswith('TN.') else code[:2])+')'
    for n,v in c.most_common():
        if dom.get(n)==code and n.endswith(st): canon[code]=n; break
print('== A: TN aliases (whole name merges)')
A=[]
for n,c in by.items():
    if not n.endswith('(TN)') and '(' in n: continue
    code=dom[n]; t=canon.get(code)
    if not t or t==n or not code.startswith('TN.'): continue
    tot=sum(c.values()); share=c[code]/tot
    if share<0.8 or c[code]<5: continue
    A.append((c[code],tot,n,t,hn.get(code)))
for a in sorted(A,reverse=True): print(a)
print('== B: non-TN names holding TN schools games')
B=[]
for n,c in by.items():
    if n.endswith('(TN)') or '(' not in n: continue
    for code,v in c.items():
        if code.startswith('TN.') and v>=5 and canon.get(code): B.append((v,sum(c.values()),n,canon[code],hn.get(code)))
for b in sorted(B,reverse=True): print(b)
pickle.dump((A,B,canon,dom),open('/tmp/hsfha_AB.pkl','wb'))
