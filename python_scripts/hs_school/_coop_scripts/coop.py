import csv,os,sys
from collections import Counter,defaultdict
ST=sys.argv[1]; R=os.path.expanduser('~/mnt/static-football-rankings/'); D=R+f'python_scripts/hs_school/{ST}/'
P=lambda n:f'{n} ({ST})' if not n.endswith(')') else n
cfg=dict(l.split('\t') for l in open(os.path.expanduser(f'~/{ST.lower()}/cfg.txt')).read().strip().split('\n') if l and not l.startswith('#')) if False else None
# --- config
exec(open(os.path.expanduser(f'~/{ST.lower()}/cfg.py')).read())
ss=sorted([f for f in os.listdir(D) if f.startswith(f'{ST}_same_score_COMMITTED_')])[-1]
rows=[x for x in csv.DictReader(open(D+ss,encoding='utf-8-sig')) if x['Decision']=='UNDECIDED']
# 1 wrong-name decisions: keep the side that is NOT the wrong name
decf=D+f'{ST}_same_score_decisions.csv'
dec=list(csv.DictReader(open(decf,encoding='utf-8-sig'))) if os.path.exists(decf) else []; have={(d['AID'],d['BID']):d for d in dec}; n=0
for x in rows:
  for wrong,right in WRONG:
    k=None
    if x['A_Opp']==P(wrong) and x['B_Opp']==P(right): k='B'
    if x['B_Opp']==P(wrong) and x['A_Opp']==P(right): k='A'
    if k:
      key=(x['AID'],x['BID'])
      if key in have: have[key]['Keep']=k
      else: d={'AID':key[0],'BID':key[1],'Keep':k}; dec.append(d); have[key]=d
      n+=1
csv.DictWriter(open(decf,'w',newline='',encoding='utf-8-sig'),fieldnames=['AID','BID','Keep']).writeheader() if False else None
with open(decf,'w',newline='',encoding='utf-8-sig') as fh:
  fn=['AID','BID','Keep']+[k for d in dec[:1] for k in d if k not in ('AID','BID','Keep')]
  w=csv.DictWriter(fh,fieldnames=fn,extrasaction='ignore'); w.writeheader(); w.writerows(dec)
print('wrong-name decisions',n)
# 2 alias rules
rf=R+f'excel_files/State_Aliases_ProperNames/{ST}_Alias_Rules.csv'
raw=open(rf,'rb').read()
try: txt=raw.decode('utf-8-sig')
except UnicodeDecodeError: txt=raw.decode('latin1')
rr=list(csv.reader(txt.splitlines())); hdr,body=rr[0],rr[1:]
idx={r[0]:i for i,r in enumerate(body)}
for a,t in ALIAS:
  a,t=P(a),P(t)
  for r in body:
    if r[2]==a: r[2]=t
  if a in idx: body[idx[a]][2]=t
  else: body.append([a,'0',t]); idx[a]=len(body)-1
  if t not in idx: body.append([t,'0',t]); idx[t]=len(body)-1
with open(rf,'w',newline='',encoding='utf-8-sig') as fh: csv.writer(fh).writerows([hdr]+body)
print('rules',len(ALIAS))
# 3 co-op majority moves per season
dump=sorted([f for f in os.listdir(D) if f.startswith(f'{ST}_q_') and 'dump' in f])[-1]
g=list(csv.DictReader(open(D+dump,encoding='utf-8-sig')))
cnt=defaultdict(Counter); ids=defaultdict(list)
for r in g:
  for t in (r['Home'],r['Visitor']):
    cnt[t][r['Season']]+=1; ids[(t,r['Season'])].append((int(r['Season']),r['ID']))
import datetime as _dt
og=defaultdict(list)
for r in g:
  try: d=_dt.date.fromisoformat(r['Dt'][:10]).toordinal()
  except Exception: d=None
  og[(r['Home'],r['Season'])].append((r['Visitor'],d,r['ID'])); og[(r['Visitor'],r['Season'])].append((r['Home'],d,r['ID']))
def pick(o,k,s):
  """ids of o's games in season s to rename to k: all if >=80% of them match a k game (same opponent, +-3 days), else only the matching ones"""
  O,K=og[(o,s)],og[(k,s)]
  m=[i for op,d,i in O if d and any(op==o2 and d2 and abs(d-d2)<=3 for o2,d2,_ in K)]
  if not O or not m: return []
  return [(int(s),i) for _,_,i in O] if len(m)/len(O)>=0.8 else [(int(s),i) for i in m]
skipped=[]
mv=defaultdict(list)
for a,b in COOP:
  a,b=P(a),P(b)
  for s in set(cnt[a])&set(cnt[b]):
    x,y=cnt[a][s],cnt[b][s]
    if x==y: continue
    f,t=(a,b) if x<y else (b,a)
    p=pick(f,t,s)
    if not p: skipped.append((f,t,s)); continue
    mv[(f,t)]+=p

# 4 PREF: (keep, other, maxseason): in seasons <= maxseason where keep has games, other's games -> keep
for k,o,mx in globals().get('PREF',[]):
  k,o=P(k),P(o)
  for s in set(cnt[k])&set(cnt[o]):
    if int(s)<=mx:
      p=pick(o,k,s)
      if not p: skipped.append((o,k,s)); continue
      mv[(o,k)]+=p
# 5 MOVE: (from, to, s1, s2) plain season-range moves
plain=[f'move-team {ST} --from "{P(f)}" --to "{P(t)}" --seasons {a}-{b} --reason "{ST} same school, older name -> later name for {a}-{b} (2026-11-12)" --commit' for f,t,a,b in globals().get('MOVE',[])]
print('season moves skipped (no shared games):',Counter((a,b) for a,b,s in skipped).most_common(40))
os.makedirs(D+'coop_ids',exist_ok=True); jobs=list(plain)
for i,((f,t),l) in enumerate(sorted(mv.items())):
  fn=f'coop_ids/{ST}_mv_{i:03d}.csv'; open(D+fn,'w').write('ID\n'+'\n'.join(sorted({q[1] for q in l}))+'\n')
  ys=[q[0] for q in l]; print(len(l),min(ys),max(ys),f,'->',t)
  jobs.append(f'move-team {ST} --from "{f}" --to "{t}" --seasons {min(ys)}-{max(ys)} --ids {fn} --reason "{ST} co-op/consolidation names in the same season: one name per season (majority, or pre-consolidation name) (2026-11-12)" --commit')
open(os.path.expanduser(f'~/{ST.lower()}/moves.txt'),'w').write('\n'.join(jobs)+'\n')
