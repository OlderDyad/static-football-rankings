import csv,re,sys,os
from collections import Counter,defaultdict
ST=sys.argv[1]; D=os.path.expanduser(f'~/mnt/static-football-rankings/python_scripts/hs_school/{ST}/')
f=max([x for x in os.listdir(D) if x.startswith(f'{ST}_same_score_') and x.endswith('.csv') and 'decisions' not in x],key=lambda x:os.path.getmtime(D+x))
def t(s):
  m=re.search(r'//(?:www\.)?([^/.]+)',s); return m.group(1)[:7] if m else re.sub(r'[_\d ].*','',s)[:7]
r=[x for x in csv.DictReader(open(D+f,encoding='utf-8-sig')) if x['Decision']=='UNDECIDED']
c=defaultdict(list)
for x in r:
  a,b=(x['A_Opp'],t(x['A_Source'])),(x['B_Opp'],t(x['B_Source']))
  if a>b: a,b=b,a
  c[(a[0],b[0])].append((int(x['Season']),a[1],b[1],x['Team']))
sfx=f' ({ST})'
for k,v in sorted(c.items(),key=lambda z:-len(z[1])):
  if len(v)<int(sys.argv[2]): break
  S=Counter((q[1],q[2]) for q in v).most_common(1)[0][0]
  tm=Counter(q[3].replace(sfx,'') for q in v).most_common(2)
  print(len(v),min(q[0] for q in v),max(q[0] for q in v),k[0].replace(sfx,''),'|',k[1].replace(sfx,''),S,tm)
