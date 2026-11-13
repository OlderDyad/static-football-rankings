import pickle,csv,os,collections,glob
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/AL/')
A,B,canon,dom=pickle.load(open('/tmp/al_hsfha_AB.pkl','rb'))
O=list(csv.DictReader(open(sorted(glob.glob(D+'AL_q_al_dump_1_*.csv'))[-1],encoding='utf-8-sig')))
have=set(); teamseason=collections.Counter()
for o in O:
    a,b=dom.get(o['Home']),dom.get(o['Visitor'])
    if a and b: have.add((o['Season'],)+tuple(sorted([a,b])))
    for n in (o['Home'],o['Visitor']): teamseason[(n,o['Season'])]+=1
c=collections.Counter(); out=[]; byseas=collections.Counter(); bytype=collections.Counter()
for h in csv.DictReader(open(D+'hsfha_AL_games.csv',encoding='utf-8')):
    if h['Played']!='1' or h['TeamScore']=='' or h['OppScore']=='': c['unplayed/noscore']+=1; continue
    if h['Exhibition']=='1': c['exhibition']+=1; continue
    k=(h['Season'],)+tuple(sorted([h['TeamCode'],h['OppCode']]))
    if k in have: c['have']+=1; continue
    t,o_=canon.get(h['TeamCode']),canon.get(h['OppCode'])
    if not t or not o_: c['unmapped side']+=1; continue
    c['MISSING']+=1; byseas[h['Season'][:3]+'0s']+=1; bytype[h['GameType']]+=1
    out.append(h|{'OurTeam':t,'OurOpp':o_})
print(c); print(sorted(byseas.items())); print(bytype)
pickle.dump(out,open('/tmp/al_hsfha_missing.pkl','wb'))
import random; random.seed(1)
for x in random.sample(out,8): print(x['Season'],x['Date'],x['OurTeam'],x['TeamScore'],x['OurOpp'],x['OppScore'],x['Location'],x['GameType'])
