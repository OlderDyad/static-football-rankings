import csv,os,sys
from collections import Counter,defaultdict
ST=sys.argv[1]; D=os.path.expanduser(f'~/mnt/static-football-rankings/python_scripts/hs_school/{ST}/')
exec(open(os.path.expanduser(f'~/{ST.lower()}/cfg.py')).read())
P=lambda n:n if n.endswith(')') else f'{n} ({ST})'
dump=sorted([f for f in os.listdir(D) if f.startswith(f'{ST}_q_') and 'dump' in f])[-1]
g=list(csv.DictReader(open(D+dump,encoding='utf-8-sig')))
opp=defaultdict(list)  # name -> [(season,opp,id)]
for r in g:
  opp[r['Home']].append((int(r['Season']),r['Visitor'],r)); opp[r['Visitor']].append((int(r['Season']),r['Home'],r))
out=[]
for w,rt in WRONG:
  w,rt=P(w),P(rt)
  for s,o,r in opp[w]:
    near=lambda n:sum(1 for s2,o2,_ in opp[n] if o2==o and abs(s2-s)<=5)
    a,b=near(rt),near(w)-1
    if a>=2 and b==0: out.append([w,rt,s,r['Dt'],o,a,b,r['Src'][:60],r['ID']])
print(ST,len(out),Counter((x[0],x[1]) for x in out).most_common())
with open(D+f'{ST}_wrong_name_suspects.csv','w',newline='',encoding='utf-8-sig') as fh:
  w_=csv.writer(fh); w_.writerow(['WrongName','RightName','Season','Date','Opponent','RightNamePlaysOpp','WrongNamePlaysOpp','Src','ID']); w_.writerows(out)
