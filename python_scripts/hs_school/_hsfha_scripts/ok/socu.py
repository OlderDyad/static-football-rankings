import csv,glob,collections,os,datetime as dt
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/OK/')
O=list(csv.DictReader(open(sorted(glob.glob(D+'OK_q_ok_dump_1_*.csv'))[-1],encoding='utf-8-sig')))
N='South Coffeyville Oklahoma Union (OK)'
g=[o for o in O if N in (o['Home'],o['Visitor'])]
opp=lambda o:o['Visitor'] if o['Home']==N else o['Home']
d=lambda o:dt.date.fromisoformat(o['Dt']) if o['Dt'] else None
# opponents' "class": count of games of opponent per season & their other opponents -> use co-play graph: opponents that play each other often are same league
byop=collections.Counter(opp(o) for o in g)
# build opponent-opponent links from all OK games
og=collections.defaultdict(collections.Counter)
for o in O:
    og[o['Home']][o['Visitor']]+=1; og[o['Visitor']][o['Home']]+=1
ops=[k for k,v in byop.items()]
# cluster ops into 2 groups via conflicts: two games same week -> different groups
conf=collections.Counter()
seas=collections.defaultdict(list)
for o in g: seas[o['Season']].append(o)
for s,L in seas.items():
    for i in range(len(L)):
        for j in range(i+1,len(L)):
            a,b=L[i],L[j]
            if d(a) and d(b) and abs((d(a)-d(b)).days)<=2 and opp(a)!=opp(b): conf[tuple(sorted([opp(a),opp(b)]))]+=1
# greedy 2-coloring of opponents by conflict graph
adj=collections.defaultdict(list)
for (a,b),c in conf.items(): adj[a].append(b); adj[b].append(a)
col={}
for start in sorted(ops,key=lambda x:-byop[x]):
    if start in col: continue
    col[start]=0; st=[start]
    while st:
        x=st.pop()
        for y in adj[x]:
            if y not in col: col[y]=1-col[x]; st.append(y)
bad=sum(1 for (a,b) in conf if col.get(a)==col.get(b))
print('opps',len(ops),'conflict pairs',len(conf),'violations',bad)
for c in (0,1):
    print(c,sorted([(byop[o],o) for o in ops if col.get(o)==c],reverse=True)[:15])
print('uncolored',[(byop[o],o) for o in ops if o not in col][:20])
ids=[o['ID'] for o in g if col.get(opp(o))==1]
open(D+'ok_south_coffeyville_ids.csv','w').write('ID\n'+'\n'.join(ids)+'\n')
print('to South Coffeyville',len(ids), collections.Counter(o['Season'][:3] for o in g if col.get(opp(o))==1))
