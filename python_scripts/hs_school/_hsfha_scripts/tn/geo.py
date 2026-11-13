import csv,glob,collections,math,statistics,sys
D='/'.join(sys.argv[1:2]) or '.'
co={}
for x in csv.DictReader(open(sorted(glob.glob(D+'/TN_q_tn_geo_all_1_*.csv'))[-1],encoding='utf-8-sig')):
    try: co[x['Team_Name']]=(float(x['Latitude']),float(x['Longitude']))
    except: pass
G=list(csv.DictReader(open(sorted(glob.glob(D+'/TN_q_tn_geo_all_2_*.csv'))[-1],encoding='utf-8-sig')))
nb=collections.defaultdict(list)
for g in G: nb[g['Home']].append(g['Visitor']); nb[g['Visitor']].append(g['Home'])
pos=dict(co)
for it in range(3):
    new={}
    for t,ns in nb.items():
        if t in co: continue
        p=[pos[n] for n in ns if n in pos]
        if len(p)>=3: new[t]=(statistics.median(a for a,b in p),statistics.median(b for a,b in p))
    pos.update({k:v for k,v in new.items()})
def km(a,b): 
    return 111*math.hypot(a[0]-b[0],(a[1]-b[1])*math.cos(math.radians(36)))
import pickle; pickle.dump((co,pos,G),open('/tmp/tn_geo.pkl','wb'))
out=[]
for t,ns in nb.items():
    if not t.endswith('(TN)') or len(ns)<60: continue
    me=co.get(t) or pos.get(t)
    if not me: continue
    # team "home" = median of opponents (robust), compare to own coords
    op=[pos[n] for n in ns if n in pos]
    cen=(statistics.median(a for a,b in op),statistics.median(b for a,b in op))
    far=[n for n in ns if n in pos and km(pos[n],cen)>300]
    if len(far)>=8:
        fc=(statistics.median(pos[n][0] for n in far),statistics.median(pos[n][1] for n in far))
        out.append((len(far),len(ns),t,'own' if t in co else 'est',round(km(me,cen)),round(cen[1],1),round(fc[1],1)))
for o in sorted(out,reverse=True)[:70]: print(o)
print(len(out))
