import csv,collections,datetime as dt,pickle,glob,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/NC/')
H=[r for r in csv.DictReader(open(D+'hsfha_NC_games.csv',encoding='utf-8'))]
O=list(csv.DictReader(open(sorted(glob.glob(D+'NC_q_nc_dump_1_*.csv'))[-1],encoding='utf-8-sig')))
def d(s):
    try: return dt.date.fromisoformat(s[:10])
    except: return None
idx=collections.defaultdict(list)
for o in O:
    if o['Home_Score']=='' or o['Visitor_Score']=='': continue
    idx[(o['Season'],o['Home_Score'],o['Visitor_Score'])].append((o,0))
    idx[(o['Season'],o['Visitor_Score'],o['Home_Score'])].append((o,1))
votes=collections.defaultdict(collections.Counter)
for h in H:
    if h['TeamScore']=='' or h['OppScore']=='' or h['Played']!='1': continue
    hd=d(h['Date'])
    for o,flip in idx.get((h['Season'],h['TeamScore'],h['OppScore']),[]):
        od=d(o['Dt'])
        if hd and od and abs((hd-od).days)>10: continue
        tn,on=(o['Home'],o['Visitor']) if not flip else (o['Visitor'],o['Home'])
        w=1 if (hd and od) else 0.3
        if h['TeamCode']: votes[h['TeamCode']][tn]+=w
        if h['OppCode']: votes[h['OppCode']][on]+=w
names={}
for r in csv.DictReader(open(D+'hsfha_NC_games.csv',encoding='utf-8')):
    names[r['TeamCode']]=r['Team']; names[r['OppCode']]=r['Opp']
mp={}
rows=[]
for c,v in votes.items():
    tot=sum(v.values()); (n1,s1),*rest=v.most_common(3)
    s2=rest[0][1] if rest else 0
    rows.append((c,names.get(c,''),n1,round(s1),round(s2),rest[0][0] if rest else '',round(tot)))
    mp[c]=(n1,s1,s2)
pickle.dump((mp,votes),open('/tmp/nc_hsfha_map.pkl','wb'))
w=csv.writer(open(D+'hsfha_code_map.csv','w',newline='',encoding='utf-8'))
w.writerow(['Code','HSFHA_Name','OurName','Votes','SecondVotes','Second','Total'])
for r in sorted(rows,key=lambda r:r[1]): w.writerow(r)
weak=[r for r in rows if r[0].startswith('NC.') and (r[3]<2*r[4] or r[3]<15)]
print(len(rows),'TN codes',sum(1 for r in rows if r[0].startswith('NC.')),'weak',len(weak))
for r in weak[:40]: print(r)
