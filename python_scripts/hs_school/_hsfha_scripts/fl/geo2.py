import csv,glob,collections,statistics,pickle
co={}
rows=list(csv.DictReader(open(sorted(glob.glob('FL_q_fl_geo_all_1_*.csv'))[-1],encoding='utf-8-sig')))
cnt=collections.Counter((x['Latitude'],x['Longitude']) for x in rows)
for x in rows:
    if cnt[(x['Latitude'],x['Longitude'])]>=4: continue   # city-centroid fallbacks
    try: co[x['Team_Name']]=(float(x['Latitude']),float(x['Longitude']))
    except: pass
G=list(csv.DictReader(open(sorted(glob.glob('FL_q_fl_geo_all_2_*.csv'))[-1],encoding='utf-8-sig')))
nb=collections.defaultdict(list)
for g in G: nb[g['Home']].append(g['Visitor']); nb[g['Visitor']].append(g['Home'])
pos=dict(co)
for it in range(4):
    new={}
    for t,ns in nb.items():
        if t in co: continue
        p=[pos[n] for n in ns if n in pos]
        if len(p)>=3: new[t]=(statistics.median(a for a,b in p),statistics.median(b for a,b in p))
    pos.update(new)
pickle.dump((co,pos,G),open('/tmp/fl_geo.pkl','wb'))
print(len(co),len(pos))
