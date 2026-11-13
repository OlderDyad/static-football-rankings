import pickle,collections,csv,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/AR/')
res=pickle.load(open('/tmp/ar_hsfha_res.pkl','rb'))
mp,votes=pickle.load(open('/tmp/ar_hsfha_map.pkl','rb'))
hn={}
for r in csv.DictReader(open(D+'hsfha_AR_schools.csv',encoding='utf-8')): hn[r['Code']]=r['Name']
by=collections.defaultdict(collections.Counter)   # our name -> code counts
for o,h,ch,cv,sc in res:
    if not h: continue
    if ch: by[o['Home']][ch]+=1
    if cv: by[o['Visitor']][cv]+=1
codeto=collections.defaultdict(collections.Counter)
for n,c in by.items():
    for k,v in c.items(): codeto[k][n]+=v
# 1) split candidates: our TN name whose games go to 2+ TN codes substantially
print('== SPLITS (our name -> several HSFHA schools)')
for n,c in sorted(by.items(),key=lambda x:-sum(x[1].values())):
    if not n.endswith('(AR)'): continue
    tot=sum(c.values()); tc=[(k,v) for k,v in c.most_common() if k.startswith('AR.') and v>=8 and v>=0.05*tot]
    if len(tc)>=2: print(n,tot,[(hn.get(k,k),v) for k,v in tc[:4]])
print('== ALIASES (HSFHA school -> several of our names)')
for k,c in sorted(codeto.items(),key=lambda x:-sum(x[1].values())):
    if not k.startswith('AR.'): continue
    tot=sum(c.values()); nn=[(n,v) for n,v in c.most_common() if v>=8 and v>=0.05*tot]
    if len(nn)>=2: print(hn.get(k,k),'|',nn[:4])
pickle.dump((by,codeto,hn),open('/tmp/ar_hsfha_by.pkl','wb'))
