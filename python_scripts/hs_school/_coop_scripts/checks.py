import csv,os,sys,re,datetime as dt,glob
from collections import Counter
HS=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/')
EST=('digital.libraries.psu','lonestarfootball','texashighschoolfootballhistory','beasport','michigan-football','ihsa.org','scfootballhistory','iwasatthegame',
 'footballhistory','azfootballarchives','hsfdatabase','Ford','cebyrd','almanac','northdakotahsfootball','partletonsports','wyoming-football')
STOP={'university','college','of','the','state','at','and','univ','u','a&m','tech','institute','junior','jc','frosh','jv','st','st.','saint'}
HSLIKE=re.compile(r'early college|university high|college park|college prep|university school|academy|college station|college place|university city|lab school|laboratory',re.I)
def toks(n):
  n=re.sub(r'\([A-Z]{2}\)','',n.lower()); return {w for w in re.findall(r"[a-z&']+",n) if w not in STOP and len(w)>2}
def latest(st,q,i):
  fs=glob.glob(f'{HS}{st}/{st}_q_{q}_{i}_*.csv'); return max(fs,key=os.path.getmtime) if fs else None
def run(st):
  out={'st':st}
  # season vs date
  f=latest(st,'season_date',2); fix=[]; other=[]
  if f:
    for r in csv.DictReader(open(f,encoding='utf-8-sig')):
      d=dt.date.fromisoformat(r['Date'][:10]); s=int(r['Season'])
      if any(e in (r['Source'] or '') for e in EST) and d.year==s+1 and d.month<=4: fix.append(r)
      else: other.append(r)
    by={}
    for r in fix: by.setdefault(r['Season'],[]).append(r)
    rows=[]
    for s,l in by.items():
      l.sort(key=lambda r:r['Date']); y=int(s); d=dt.date(y,12,20)
      while d.weekday()!=4: d-=dt.timedelta(days=1)
      for k,r in enumerate(l): rows.append((r['ID'],(d-dt.timedelta(days=7*(len(l)-1-k))).isoformat(),f"estimated date {r['Date']} past season -> December Friday"))
    if rows:
      w=csv.writer(open(f'{HS}{st}/{st}_season_date_fix.csv','w',newline='')); w.writerow(['ID','NewDate','Note']); w.writerows(rows)
  out['sd_fix']=len(fix); out['sd_other']=len(other)
  # college copies
  f=latest(st,'college_check',4); arch=[]
  if f:
    for r in csv.DictReader(open(f,encoding='utf-8-sig')):
      if r.get('Kind')!='college vs college' or int(r['Season'])<1940 or not r.get('CollegeID'): continue
      if HSLIKE.search(r['Home']) or HSLIKE.search(r['Visitor']): continue
      h,v,ch,cv=toks(r['Home']),toks(r['Visitor']),toks(r.get('C_Home','')),toks(r.get('C_Visitor',''))
      if (h&ch and v&cv) or (h&cv and v&ch): arch.append(r['ID'])
    if arch:
      w=csv.writer(open(f'{HS}{st}/{st}_college_copies_archive.csv','w',newline='')); w.writerow(['ID']); [w.writerow([i]) for i in arch]
  out['college']=len(arch)
  # forfeits
  f=latest(st,'forfeits',2); out['ff_2_0']=sum(1 for _ in csv.DictReader(open(f,encoding='utf-8-sig'))) if f else 0
  return out
for st in sys.argv[1:]: print(run(st))
