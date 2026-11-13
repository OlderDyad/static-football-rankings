import pickle,collections,os,re
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/SC/')
res=pickle.load(open('/tmp/sc_hsfha_res.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/sc_hsfha_AB.pkl','rb'))
keep=pickle.load(open('/tmp/sc_hsfha_keepmv.pkl','rb'))
keep={k:v for k,v in keep.items() if len(v)>=5 and 'Health Sciences' not in k[0]}
nb=collections.defaultdict(list)
for o,h,ch,cv,sc in res:
    if not h: continue
    for side,code in (('Home',ch),('Visitor',cv)):
        n=o[side]
        if n.endswith('(SC)') or '(' not in n or not code.startswith('SC.'): continue
        t=canon.get(code)
        if t and t.endswith('(SC)'): nb[(n,t)].append(o['ID'])
nb={k:v for k,v in nb.items() if len(v)>=5}
for k,v in sorted(nb.items(),key=lambda x:-len(x[1])): print(len(v),k)
allm={**keep,**nb}
L=[]
for i,((n,t),ids) in enumerate(sorted(allm.items(),key=lambda x:-len(x[1]))):
    fn=f'hsfha_mv_{i:02d}.csv'
    open(D+fn,'w').write('ID\n'+'\n'.join(sorted(set(ids)))+'\n')
    st=n[n.rfind('(')+1:-1] if n.endswith(')') else 'NC'
    L.append(f'move-team SC --from "{n}" --to "{t}" --seasons 1880-2026 --ids {fn} --reason "HSFHA-SC match: game belongs to {t} (hsfha.org school code)"')
open('/tmp/sc_mv_lines.txt','w').write('\n'.join(L)+'\n')
print(len(L),sum(len(set(v)) for v in allm.values()))
