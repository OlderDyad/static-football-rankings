import pickle,csv,os,collections,datetime as dt
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/AR/')
res=pickle.load(open('/tmp/ar_hsfha_res.pkl','rb'))
out=[]; c=collections.Counter(); seen=set()
for o,h,ch,cv,sc in res:
    if not h or sc!=2 or not h['Date']: continue
    src=o['Src'].lower()
    kind='hsfdatabase' if 'hsfdatabase' in src else ('blank' if src.strip() in ('','ref!','0') else None)
    if not kind: continue
    nd=dt.date.fromisoformat(h['Date']); s=int(o['Season'])
    if not (dt.date(s,8,1)<=nd<=dt.date(s+1,1,31)): c['outofseason']+=1; continue
    if o['Dt']==h['Date']: c[kind+' same']+=1; continue
    if o['ID'] in seen: continue
    seen.add(o['ID'])
    c[kind+' change']+=1
    out.append((o['ID'],h['Date'],f"hsfha.org game {h['GameID']}",kind))
print(c)
for k in ('hsfdatabase','blank'):
    rows=[r for r in out if r[3]==k]
    with open(D+f'hsfha_dates_{k}.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['ID','NewDate','Note']); w.writerows([r[:3] for r in rows])
    print(k,len(rows))
