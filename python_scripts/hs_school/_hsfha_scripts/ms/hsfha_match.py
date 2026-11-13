import csv,collections,datetime as dt,pickle,glob,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/MS/')
mp,votes=pickle.load(open('/tmp/ms_hsfha_map.pkl','rb'))
canon={c:v[0] for c,v in mp.items()}
import os.path
if os.path.exists('/tmp/ms_hsfha_AB.pkl'):
    _A,_B,_c,_d=pickle.load(open('/tmp/ms_hsfha_AB.pkl','rb')); canon.update(_c)
    canon[[c for c in _c if 0] and 0 or 'x']='x'
H=[r for r in csv.DictReader(open(D+'hsfha_MS_games.csv',encoding='utf-8')) if r['Played']=='1' and r['TeamScore']!='' and r['OppScore']!='']
O=list(csv.DictReader(open(sorted(glob.glob(D+'MS_q_ms_dump_1_*.csv'))[-1],encoding='utf-8-sig')))
def d(s):
    try: return dt.date.fromisoformat(s[:10])
    except: return None
hidx=collections.defaultdict(list)
for h in H:
    hidx[(h['Season'],h['TeamScore'],h['OppScore'])].append((h,h['TeamCode'],h['OppCode']))
    hidx[(h['Season'],h['OppScore'],h['TeamScore'])].append((h,h['OppCode'],h['TeamCode']))
res=[]; used=collections.Counter()
stat=collections.Counter()
for o in O:
    if o['Home_Score']=='' or o['Visitor_Score']=='': stat['noscore']+=1; continue
    od=d(o['Dt']); best=None
    for h,ch,cv in hidx.get((o['Season'],o['Home_Score'],o['Visitor_Score']),[]):
        hd=d(h['Date'])
        if hd and od and abs((hd-od).days)>10: continue
        a=canon.get(ch)==o['Home']; b=canon.get(cv)==o['Visitor']
        sc=(2 if a and b else 1 if (a or b) else 0)
        if sc==0: continue
        gap=abs((hd-od).days) if hd and od else 5
        k=(sc,-gap)
        if not best or k>best[0]: best=(k,h,ch,cv)
    if not best: stat['nomatch']+=1; res.append((o,None,None,None,0)); continue
    (sc,ng),h,ch,cv=best
    stat['both' if sc==2 else 'one']+=1
    res.append((o,h,ch,cv,sc))
print(stat)
pickle.dump(res,open('/tmp/ms_hsfha_res.pkl','wb'))
# name disagreements on one-side matches
dis=collections.Counter()
for o,h,ch,cv,sc in res:
    if sc==1:
        if canon.get(ch)!=o['Home']: dis[(o['Home'],canon.get(ch),ch)]+=1
        else: dis[(o['Visitor'],canon.get(cv),cv)]+=1
w=csv.writer(open(D+'hsfha_name_disagree.csv','w',newline='',encoding='utf-8'))
w.writerow(['OurName','HSFHA_Canon','Code','Games'])
for k,v in dis.most_common(): w.writerow(list(k)+[v])
print(len(dis)); 
for k,v in dis.most_common(60): print(v,k)
