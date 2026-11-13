import pickle,collections,csv,os,re
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/SC/')
out=pickle.load(open('/tmp/sc_hsfha_missing.pkl','rb'))
mp,votes=pickle.load(open('/tmp/sc_hsfha_map.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/sc_hsfha_AB.pkl','rb'))
def strong(code):
    v=votes.get(code); n=canon.get(code)
    if not v or not n: return False
    return v[n]>=10 and v[n]>=2*max([x for k,x in v.items() if k!=n] or [0])
ok=[];c=collections.Counter()
for x in out:
    if not (strong(x['TeamCode']) and strong(x['OppCode'])): c['weakmap']+=1; continue
    if not x['Date']: c['undated']+=1
    ok.append(x)
print(c,len(ok))
def city(n): return n.split(' (')[0].lower()
rows=[];hc=collections.Counter()
for x in ok:
    t,o=x['OurTeam'],x['OurOpp']; ts,os_=x['TeamScore'],x['OppScore']; site=x.get('TeamSite','')
    if site=='a': home,vis,hs,vs,neu=o,t,os_,ts,None; hc['opp home']+=1
    elif site=='n': home,vis,hs,vs,neu=t,o,ts,os_,1; hc['neutral']+=1
    else: home,vis,hs,vs,neu=t,o,ts,os_,None; hc['team home' if site=='h' else 'unknown']+=1
    rows.append([x['Season'],x['Date'],home,hs,vis,vs,'' if neu is None else neu,x['Location'],f"hsfha.org HSFHA-SC game {x['GameID']}"])
print(hc)
with open(D+'hsfha_import_SC.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['Season','Date','Home','Home_Score','Visitor','Visitor_Score','Neutral','Location','Source']); w.writerows(rows)
print(len(rows))
