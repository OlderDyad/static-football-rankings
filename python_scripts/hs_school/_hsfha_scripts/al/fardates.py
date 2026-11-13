import pickle,csv,os,collections,datetime as dt
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/AL/')
res=pickle.load(open('/tmp/al_hsfha_res.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/al_hsfha_AB.pkl','rb'))
pair=collections.defaultdict(list)
for h in csv.DictReader(open(D+'hsfha_AL_games.csv',encoding='utf-8')):
    if h['Played']=='1': pair[(h['Season'],)+tuple(sorted([h['TeamCode'],h['OppCode']]))].append(h)
EST=('hsfdatabase','classmates','e-yearbook','cebyrd')
out=[];c=collections.Counter(); diff=[]
for o,h,ch,cv,sc in res:
    if h: continue
    a,b=dom.get(o['Home']),dom.get(o['Visitor'])
    if not (a and b): continue
    hs=pair.get((o['Season'],)+tuple(sorted([a,b])),[])
    m=[]
    for x in hs:
        ts,os_=(x['TeamScore'],x['OppScore']) if x['TeamCode']==a else (x['OppScore'],x['TeamScore'])
        if ts==o['Home_Score'] and os_==o['Visitor_Score']: m.append(x)
        else: diff.append((o['Season'],o['Dt'],o['Home'],o['Home_Score'],o['Visitor'],o['Visitor_Score'],o['Src'],o['ID'],x['Date'],ts,os_,x['GameID']))
    if len(m)!=1 or not m[0]['Date']: continue
    s=o['Src'].lower(); est=s.strip() in ('','ref!','0') or any(e in s for e in EST)
    nd=dt.date.fromisoformat(m[0]['Date']); yr=int(o['Season'])
    if not (dt.date(yr,8,1)<=nd<=dt.date(yr+1,1,31)): continue
    c['est' if est else 'dated:'+o['Src'][:18]]+=1
    if est: out.append((o['ID'],m[0]['Date'],f"hsfha.org game {m[0]['GameID']} (same teams+score)"))
print(c.most_common(10)); print(len(out))
with open(D+'hsfha_dates_far.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['ID','NewDate','Note']); w.writerows(out)
with open(D+'AL_score_disagreements.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['Season','Date','Home','HS','Visitor','VS','Source','ID','HSFHA_Date','HSFHA_HomeScore','HSFHA_VisScore','HSFHA_GameID']); w.writerows(sorted(diff))
print('disagreements',len(diff))
