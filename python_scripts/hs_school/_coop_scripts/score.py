import csv,os,sys,datetime as dt
from collections import defaultdict,Counter
ST=sys.argv[1]; D=os.path.expanduser(f'~/mnt/static-football-rankings/python_scripts/hs_school/{ST}/')
ssf=max([f for f in os.listdir(D) if f.startswith(f'{ST}_same_score_') and f.endswith('.csv') and 'decisions' not in f],key=lambda x:os.path.getmtime(D+x))
dump=max([f for f in os.listdir(D) if f.startswith(f'{ST}_q_') and 'dump' in f and f.endswith('.csv')],key=lambda x:os.path.getmtime(D+x))
rows=[x for x in csv.DictReader(open(D+ssf,encoding='utf-8-sig')) if x['Decision']=='UNDECIDED']
g=list(csv.DictReader(open(D+dump,encoding='utf-8-sig')))
ids={r['ID'] for r in g}
opp=defaultdict(set); pairs=defaultdict(Counter)  # (team,season)->opps ; team->Counter((opp,season))
for r in g:
  s=int(r['Season']); h,v=r['Home'],r['Visitor']
  opp[(h,s)].add(v); opp[(v,s)].add(h); pairs[h][(v,s)]+=1; pairs[v][(h,s)]+=1
def hist(t,o,s):
  return sum(c for (oo,ss),c in pairs[t].items() if oo==o and ss!=s and abs(ss-s)<=6)
def net(t,o,s):
  return len((opp[(t,s)]-{o})&(opp[(o,s)]-{t}))
EST=('digital.libraries.psu','lonestarfootball','texashighschoolfootballhistory','beasport','michigan-football','ihsa.org','scfootballhistory','iwasatthegame',
 'footballhistory','azfootballarchives','hsfdatabase','classmates','e-yearbook','Ford','cebyrd','almanac','northdakotahsfootball','partletonsports','wyoming-football')
def est(src): return any(e in (src or '') for e in EST)
def size(o): return sum(pairs[o].values())
out=[];stat=Counter()
for x in rows:
  if x['AID'] not in ids or x['BID'] not in ids: stat['gone']+=1; continue
  t=x['Team']; s=int(x['Season']); A,B=x['A_Opp'],x['B_Opp']
  hA,hB=hist(t,A,s),hist(t,B,s); nA,nB=net(t,A,s),net(t,B,s); sA,sB=size(A),size(B)
  keep=None; why=''
  if A==t: keep,why='B','self-game copy'
  elif B==t: keep,why='A','self-game copy'
  elif hA>=2 and hB==0 and nA>=nB: keep,why='A',f'history {hA}-{hB}'
  elif hB>=2 and hA==0 and nB>=nA: keep,why='B',f'history {hB}-{hA}'
  elif nA>=3 and nB==0 and hB==0: keep,why='A',f'league {nA}-{nB}'
  elif nB>=3 and nA==0 and hA==0: keep,why='B',f'league {nB}-{nA}'
  elif sA>=100 and sB<=5 and hB==0 and nB==0: keep,why='A',f'size {sA}-{sB}'
  elif sB>=100 and sA<=5 and hA==0 and nA==0: keep,why='B',f'size {sB}-{sA}'
  elif hA>=1 and hB==0 and nA>=nB+2: keep,why='A',f'history+league {hA}/{nA}-{hB}/{nB}'
  elif hB>=1 and hA==0 and nB>=nA+2: keep,why='B',f'history+league {hB}/{nB}-{hA}/{nA}'
  elif (hA>=2 or nA>=2) and (hB>=2 or nB>=2) and (est(x['A_Source']) or est(x['B_Source'])):
    keep,why='X',f'both regular opponents {hA}/{nA} {hB}/{nB}, estimated-date source: likely two real games in different weeks'
  if keep in ('A','B') and why!='self-game copy':
    sk,sd=(sA,sB) if keep=='A' else (sB,sA)
    if sk<50 and sk<0.1*sd: keep,why=None,''
  stat[why.split()[0] if keep else 'undecided']+=1
  out.append(dict(AID=x['AID'],BID=x['BID'],Keep=keep or '',Why=why,Team=t,Season=s,Score=x['Score'],A_Opp=A,B_Opp=B,hA=hA,hB=hB,nA=nA,nB=nB,sA=sA,sB=sB,A_Src=x['A_Source'][:40],B_Src=x['B_Source'][:40]))
print(ST,len(rows),dict(stat))
w=csv.DictWriter(open(os.path.expanduser(f'~/grind/{ST}_scored.csv'),'w',newline=''),fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
