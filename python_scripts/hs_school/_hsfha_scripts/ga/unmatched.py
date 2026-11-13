import pickle,csv,os,collections,datetime as dt
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/GA/')
res=pickle.load(open('/tmp/ga_hsfha_res.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/ga_hsfha_AB.pkl','rb'))
H=list(csv.DictReader(open(D+'hsfha_GA_games.csv',encoding='utf-8')))
cov=set(); pair=collections.defaultdict(list); teamdate=collections.defaultdict(list)
for h in H:
    for c in (h['TeamCode'],h['OppCode']):
        if c: cov.add((c,h['Season']))
    k=(h['Season'],)+tuple(sorted([h['TeamCode'],h['OppCode']]))
    pair[k].append(h)
def d(s):
    try: return dt.date.fromisoformat(s[:10])
    except: return None
out=[];cat=collections.Counter(); srccat=collections.defaultdict(collections.Counter)
for o,h,ch,cv,sc in res:
    if h: continue
    a,b=dom.get(o['Home']),dom.get(o['Visitor'])
    s=o['Season']
    if not a and not b: k='NO_CODE_EITHER'
    elif not (a and b):
        c=a or b
        k='ONE_TEAM_KNOWN_NOT_COVERED' if (c,s) not in cov else 'ONE_TEAM_KNOWN_COVERED'
    else:
        hs=pair.get((s,)+tuple(sorted([a,b])),[])
        if hs:
            sc2=[(x['TeamScore'],x['OppScore'],x['Date'],x['Played']) for x in hs]
            k='SAME_TEAMS_DIFF_SCORE' if any(x['Played']=='1' for x in hs) else 'SAME_TEAMS_NOT_PLAYED'
        elif (a,s) not in cov or (b,s) not in cov: k='SEASON_NOT_COVERED'
        else: k='BOTH_COVERED_NO_GAME'
    cat[k]+=1
    sr=o['Src'][:22]; srccat[k][sr]+=1
    out.append((k,o['Season'],o['Dt'],o['Home'],o['Home_Score'],o['Visitor'],o['Visitor_Score'],o['Src'],o['ID']))
print(cat)
for k,v in srccat.items(): print(k, v.most_common(5))
with open(D+'GA_unmatched_classified.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['Class','Season','Date','Home','HS','Visitor','VS','Source','ID']); w.writerows(sorted(out))
