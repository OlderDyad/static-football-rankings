import csv,glob,os,collections,datetime as dt
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/FL/')
f=sorted(glob.glob(D+'FL_q_fl_dump_1_*.csv'))[-1]
G=collections.defaultdict(list)
for r in csv.DictReader(open(f,encoding='utf-8-sig')):
    try: d=dt.date.fromisoformat(r['Dt'])
    except: continue
    h,v=r['Home'].strip(),r['Visitor'].strip()
    G[h].append((int(r['Season']),d,v,r['Home_Score'],r['Visitor_Score']))
    G[v].append((int(r['Season']),d,h,r['Visitor_Score'],r['Home_Score']))
for line in open('pairs.txt'):
    a,t=line.strip().split('|')
    A,T=G.get(a,[]),G.get(t,[])
    by=collections.defaultdict(list)
    for g in T: by[g[0]].append(g)
    dup=clash=0
    for s,d,o,x,y in A:
        near=[g for g in by.get(s,[]) if abs((g[1]-d).days)<=3]
        if not near: continue
        if any(g[2]==o or (g[3],g[4])==(x,y) for g in near): dup+=1
        else: clash+=1
    flag='  <<<' if clash>max(3,0.15*len(A)) else ''
    print(f"{len(A):5} {len(T):5} dup {dup:4} clash {clash:4}  {a} -> {t}{flag}" if A else f"   -- missing {a}" )
    if not T: print('      TARGET MISSING',t)
