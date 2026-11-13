import csv,glob,os,collections,datetime as dt,sys
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/AL/')
f=sorted(glob.glob(D+'AL_q_al_dump_1_*.csv'))[-1]
G=collections.defaultdict(list)
for r in csv.DictReader(open(f,encoding='utf-8-sig')):
    try: d=dt.date.fromisoformat(r['Dt'])
    except: continue
    h,v=r['Home'].strip(),r['Visitor'].strip()
    G[h].append((int(r['Season']),d,v,r['Home_Score'],r['Visitor_Score'],r['Src'][:25],r['ID']))
    G[v].append((int(r['Season']),d,h,r['Visitor_Score'],r['Home_Score'],r['Src'][:25],r['ID']))
a,t=sys.argv[1],sys.argv[2]; n=0
by=collections.defaultdict(list)
for g in G[t]: by[g[0]].append(g)
for g in sorted(G[a]):
    near=[x for x in by.get(g[0],[]) if abs((x[1]-g[1]).days)<=3]
    if near and not any(x[2]==g[2] or (x[3],x[4])==(g[3],g[4]) for x in near):
        print(g,'||',near[0]); n+=1
        if n>=int(sys.argv[3]): break
