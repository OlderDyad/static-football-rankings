import csv,re,os
from collections import Counter,defaultdict
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/ND/')
ss=list(csv.DictReader(open(D+'ND_same_score_COMMITTED_20261112_1025.csv',encoding='utf-8-sig')))
typ=lambda s:'mp' if 'maxpreps' in s else 'nd' if 'northdakotahsfootball' in s else 'o'
# 1 decisions
dec=list(csv.DictReader(open(D+'ND_same_score_decisions.csv',encoding='utf-8-sig')))
keep={}; pairs=Counter(); drop=set()
for x in ss:
  if x['Decision']!='UNDECIDED': continue
  a,b=typ(x['A_Source']),typ(x['B_Source'])
  if {a,b}=={'mp','nd'}:
    k='A' if a=='mp' else 'B'; keep[(x['AID'],x['BID'])]=k
    drop.add(x['BID'] if k=='A' else x['AID'])
    mp,nd=(x['A_Opp'],x['B_Opp']) if a=='mp' else (x['B_Opp'],x['A_Opp'])
    if mp!=nd: pairs[(nd,mp)]+=1
n=0
for r in dec:
  k=keep.get((r['AID'],r['BID']))
  if k and r['Keep'] not in('A','B'): r['Keep']=k; n+=1
print('decisions set',n,'pairs',len(pairs))
w=csv.DictWriter(open(D+'ND_same_score_decisions.csv','w',newline='',encoding='utf-8-sig'),fieldnames=['AID','BID','Keep']); w.writeheader(); w.writerows(dec)
# 2 moves
cands=defaultdict(set)
for (nd,mp),c in pairs.items():
  if c>=2: cands[nd].add(mp)
g=list(csv.DictReader(open(D+'ND_q_nd_dump_1_20261112_1004.csv',encoding='utf-8-sig')))
mpseas=defaultdict(int)
for r in g:
  if typ(r['Src'])=='mp':
    for t in (r['Home'],r['Visitor']): mpseas[(t,r['Season'])]+=1
mv=defaultdict(list); skip=Counter()
for r in g:
  if typ(r['Src'])!='nd' or r['ID'] in drop: continue
  for t in (r['Home'],r['Visitor']):
    if t not in cands: continue
    s=r['Season']
    if mpseas[(t,s)]: skip['member has MP games']+=1; continue
    hit=[c for c in cands[t] if mpseas[(c,s)]]
    if len(hit)!=1: skip[f'{len(hit)} coops']+=1; continue
    mv[(t,hit[0])].append((int(s),r['ID']))
print(skip)
os.makedirs(D+'coop_ids',exist_ok=True)
jobs=[]
for i,((f,t),l) in enumerate(sorted(mv.items())):
  fn=f'coop_ids/mv_{i:03d}.csv'
  with open(D+fn,'w',newline='') as fh: fh.write('ID\n'+'\n'.join(x[1] for x in l)+'\n')
  ys=[x[0] for x in l]
  print(len(l),min(ys),max(ys),f,'->',t)
  jobs.append(f'move-team ND --from "{f}" --to "{t}" --seasons {min(ys)}-{max(ys)} --ids {fn} --reason "ND co-op: northdakotahsfootball member name -> MaxPreps co-op name for co-op seasons (2026-11-12)" --commit')
open(os.path.expanduser('~/nd/moves.txt'),'w').write('\n'.join(jobs)+'\n')
