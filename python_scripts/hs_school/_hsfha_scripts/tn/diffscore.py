import pickle,csv,os,collections,datetime as dt,random
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/TN/')
res=pickle.load(open('/tmp/hsfha_res.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/hsfha_AB.pkl','rb'))
pair=collections.defaultdict(list)
for h in csv.DictReader(open(D+'hsfha_TN_games.csv',encoding='utf-8')):
    pair[(h['Season'],)+tuple(sorted([h['TeamCode'],h['OppCode']]))].append(h)
def d(s):
    try: return dt.date.fromisoformat(s[:10])
    except: return None
c=collections.Counter(); ex=collections.defaultdict(list)
for o,h,ch,cv,sc in res:
    if h: continue
    a,b=dom.get(o['Home']),dom.get(o['Visitor'])
    if not (a and b): continue
    hs=[x for x in pair.get((o['Season'],)+tuple(sorted([a,b])),[]) if x['Played']=='1']
    if not hs: continue
    best=None
    for x in hs:
        ts,os_=(x['TeamScore'],x['OppScore']) if x['TeamCode']==a else (x['OppScore'],x['TeamScore'])
        same=(ts==o['Home_Score'] and os_==o['Visitor_Score']); swap=(ts==o['Visitor_Score'] and os_==o['Home_Score'])
        gap=abs((d(x['Date'])-d(o['Dt'])).days) if d(x['Date']) and d(o['Dt']) else None
        k='SAME_SCORE_FAR_DATE' if same else 'SWAPPED_SCORE' if swap else ('HSFHA_NO_SCORE' if ts=='' else 'DIFF_SCORE')
        best=k if not best else best
    c[best]+=1
    if len(ex[best])<6: ex[best].append((o['Season'],o['Dt'],o['Home'],o['Home_Score'],o['Visitor'],o['Visitor_Score'],o['Src'][:20],'| HSFHA',[(x['Date'],x['Team'],x['TeamScore'],x['Opp'],x['OppScore']) for x in hs][:2]))
print(c)
for k,v in ex.items():
    print('##',k)
    for e in v: print('  ',e)
