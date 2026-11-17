import csv,os,sys,shutil
ST=sys.argv[1]; D=os.path.expanduser(f'~/mnt/static-football-rankings/python_scripts/hs_school/{ST}/')
sc=[x for x in csv.DictReader(open(os.path.expanduser(f'~/grind/{ST}_scored.csv'))) if x['Keep']]
f=D+f'{ST}_same_score_decisions.csv'
dec=list(csv.DictReader(open(f,encoding='utf-8-sig'))) if os.path.exists(f) else []
if os.path.exists(f): shutil.copyfile(f,D+f'{ST}_same_score_decisions_pre_grind.csv')
fn=['AID','BID','Keep']+[k for d in dec[:1] for k in d if k not in ('AID','BID','Keep')]
if 'Note' not in fn: fn.append('Note')
have={(d['AID'],d['BID']):d for d in dec}; n=0
for x in sc:
  k=(x['AID'],x['BID']); note=f"grind 2026-11-13: {x['Why']}"
  if k in have:
    if have[k].get('Keep') in ('A','B'): continue
    have[k]['Keep']=x['Keep']; have[k]['Note']=note
  else:
    d={'AID':k[0],'BID':k[1],'Keep':x['Keep'],'Note':note}; dec.append(d); have[k]=d
  n+=1
with open(f,'w',newline='',encoding='utf-8-sig') as fh:
  w=csv.DictWriter(fh,fieldnames=fn,extrasaction='ignore'); w.writeheader(); w.writerows(dec)
print(ST,n)
