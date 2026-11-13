import csv,glob,os,sys,collections
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/GA/')
f=sorted(glob.glob(D+'GA_q_ga_dump_1_*.csv'))[-1]
c=collections.defaultdict(list)
for r in csv.DictReader(open(f,encoding='utf-8-sig')):
    s=int(r['Season'])
    for k in ('Home','Visitor'): c[r[k].strip()].append(s)
for n in sys.argv[1:]:
    v=c.get(n,[]); 
    if not v: print(n,'-- none'); continue
    h=collections.Counter(x//10*10 for x in v)
    print(f"{n}: {len(v)} {min(v)}-{max(v)}", dict(sorted(h.items())))
