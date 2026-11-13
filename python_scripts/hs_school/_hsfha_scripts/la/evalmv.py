import pickle,csv,glob,collections,statistics,math,datetime as dt,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/LA/')
co,pos,G=pickle.load(open('/tmp/la_geo.pkl','rb'))
keep=pickle.load(open('/tmp/la_hsfha_keepmv.pkl','rb'))
O={o['ID']:o for o in csv.DictReader(open(sorted(glob.glob(D+'LA_q_la_dump_1_*.csv'))[-1],encoding='utf-8-sig'))}
games=collections.defaultdict(list)
for o in O.values():
    for t in (o['Home'],o['Visitor']): games[t].append(o)
def opp(o,t): return o['Visitor'] if o['Home']==t else o['Home']
def km(a,b): return 111*math.hypot(a[0]-b[0],(a[1]-b[1])*math.cos(math.radians(31)))
def cen(L):
    p=[pos[x] for x in L if x in pos]
    return (statistics.median(a for a,b in p),statistics.median(b for a,b in p)) if len(p)>=3 else None
def d(s):
    try: return dt.date.fromisoformat(s[:10])
    except: return None
rows=[]
for (n,t),ids in sorted(keep.items(),key=lambda x:-len(x[1])):
    if len(ids)<10: continue
    ids=[i for i in ids if i in O]; S=set(ids)
    mo=cen([opp(O[i],n) for i in ids])
    fo=cen([opp(o,n) for o in games[n] if o['ID'] not in S])
    to=cen([opp(o,t) for o in games[t]])
    # date conflicts
    tdates=collections.defaultdict(list)
    for o in games[t]:
        if d(o['Dt']): tdates[o['Season']].append(d(o['Dt']))
    fdates=collections.defaultdict(list)
    for o in games[n]:
        if o['ID'] not in S and d(o['Dt']): fdates[o['Season']].append(d(o['Dt']))
    clash_to=sum(1 for i in ids if d(O[i]['Dt']) and any(abs((x-d(O[i]['Dt'])).days)<=2 for x in tdates[O[i]['Season']]))
    clash_from=sum(1 for i in ids if d(O[i]['Dt']) and any(abs((x-d(O[i]['Dt'])).days)<=2 for x in fdates[O[i]['Season']]))
    dm_f=round(km(mo,fo)) if mo and fo else None; dm_t=round(km(mo,to)) if mo and to else None
    rows.append((len(ids),n,t,dm_f,dm_t,clash_from,clash_to))
    print(len(ids),n,'->',t,'| moved-opps km from FROM',dm_f,'from TO',dm_t,'| from double-booked',clash_from,'to clash',clash_to)
pickle.dump(rows,open('/tmp/la_eval.pkl','wb'))
