import pickle,collections,csv,os,re
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/SC/')
res=pickle.load(open('/tmp/sc_hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/sc_hsfha_by.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/sc_hsfha_AB.pkl','rb'))
span={}
for r in csv.DictReader(open(D+'hsfha_SC_games.csv',encoding='utf-8')):
    if r['Played']!='1': continue
    s=int(r['Season'])
    for c in (r['TeamCode'],r['OppCode']):
        if c: a,b=span.get(c,(9999,0)); span[c]=(min(a,s),max(b,s))
cty=lambda c:c.split('-')[0]
aliasnames={a[2] for a in A}
mv=collections.defaultdict(list)
for o,h,ch,cv,sc in res:
    if sc!=1: continue
    for side,code in (('Home',ch),('Visitor',cv)):
        n=o[side]
        if not code or not code.startswith('SC.') or dom.get(n)==code: continue
        t=canon.get(code)
        if not t or t==n or n in aliasnames: continue
        a=dom.get(n)
        # lineage hold: same county, non-overlapping spans
        if a and a.startswith('SC.') and cty(a)==cty(code):
            sa,sb=span.get(a,(0,0)),span.get(code,(0,0))
            if not (sa[1]>=sb[0]+1 and sb[1]>=sa[0]+1): continue
        mv[(n,t)].append(o['ID'])
keep={k:v for k,v in mv.items() if len(v)>=3}
print('pairs',len(keep),'games',sum(len(v) for v in keep.values()),'dropped small',sum(len(v) for k,v in mv.items() if len(v)<3))
for (n,t),v in sorted(keep.items(),key=lambda x:-len(x[1])): print(len(v),n,'->',t)
pickle.dump(keep,open('/tmp/sc_hsfha_keepmv.pkl','wb'))
