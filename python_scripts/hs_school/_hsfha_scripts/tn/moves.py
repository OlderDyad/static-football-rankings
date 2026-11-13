import pickle,collections,csv,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/TN/')
res=pickle.load(open('/tmp/hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/hsfha_by.pkl','rb'))
span={}
for r in csv.DictReader(open(D+'hsfha_TN_games.csv',encoding='utf-8')):
    if r['Played']!='1': continue
    s=int(r['Season'])
    for c in (r['TeamCode'],r['OppCode']):
        if c: a,b=span.get(c,(9999,0)); span[c]=(min(a,s),max(b,s))
dom={n:c.most_common(1)[0][0] for n,c in by.items() if c}
canon={}
for code,c in codeto.items():
    for n,v in c.most_common():
        if dom.get(n)==code: canon[code]=n; break
cty=lambda c:c.split('-')[0] if c else ''
mv=collections.defaultdict(list)
for o,h,ch,cv,sc in res:
    if sc!=1: continue
    for side,code in (('Home',ch),('Visitor',cv)):
        n=o[side]
        if not code or dom.get(n)==code: continue
        t=canon.get(code)
        if not t or t==n: continue
        mv[(n,t)].append((o['ID'],o['Season'],side))
def kind(n,t):
    a,b=dom.get(n),dom.get(t)
    if not a or not b: return 'AUTO'
    if not (a.startswith('TN.') and b.startswith('TN.')): return 'AUTO'
    if cty(a)!=cty(b): return 'AUTO'
    sa,sb=span.get(a,(0,0)),span.get(b,(0,0))
    if sa[1]>=sb[0]+1 and sb[1]>=sa[0]+1: return 'AUTO'   # overlapping = two schools at once
    return 'LINEAGE'
rows=[]
for (n,t),g in mv.items():
    tot=sum(by[n].values())
    rows.append((kind(n,t),len(g),n,t,tot,hn.get(dom.get(n)),hn.get(dom.get(t)),min(x[1] for x in g),max(x[1] for x in g)))
rows.sort(key=lambda r:(r[0],-r[1]))
w=csv.writer(open(D+'hsfha_moves_summary.csv','w',newline='',encoding='utf-8'))
w.writerow(['Kind','Games','From','To','FromTotalMatched','FromHSFHA','ToHSFHA','MinSeason','MaxSeason'])
w.writerows(rows)
pickle.dump((mv,rows),open('/tmp/hsfha_mv.pkl','wb'))
print(collections.Counter(r[0] for r in rows), sum(r[1] for r in rows if r[0]=='AUTO'), sum(r[1] for r in rows if r[0]=='LINEAGE'))
for r in rows:
    if r[1]>=10: print(r)
