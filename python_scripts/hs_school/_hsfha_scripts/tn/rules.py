import pickle,csv,os
A,B,canon,dom=pickle.load(open('/tmp/hsfha_AB.pkl','rb'))
P=os.path.expanduser('~/mnt/static-football-rankings/excel_files/State_Aliases_ProperNames/TN_Alias_Rules.csv')
skip={'Mount Pleasant Hay Long (TN)','Tennessee Military Institute (TN)','Sweetwater Tennessee Military Institute (TN)'}
rev={'Kingsport Ketron (TN)':'Ketron (TN)','Kingsport Lynn View (TN)':'Lynn View (TN)','Chattanooga Kirkman (TN)':'Kirkman (TN)',
     'Maryville Lanier (TN)':'Lanier (TN)','Columbia Carver-Smith (TN)':'Carver-Smith (TN)','Memphis Oakhaven Baptist Academy (TN)':'OBA (TN)',
     'Dandridge Maury (TN)':'Maury (TN)'}
m={}
for g,tot,n,t,h in A:
    if n in skip: continue
    if n in rev: m[rev[n]]=n; continue
    m[n]=t
for a,b in [('Hixson (TN)','Chattanooga Hixson (TN)'),('Hixon (TN)','Chattanooga Hixson (TN)'),('Chattanooga Hixson (TN)',None),
            ('Tennessee Military Institute (TN)','Sweetwater Tennessee Military Institute (TN)'),
            ('Memphis Southern Baptist Educational Center (TN)','Southaven Northpoint Christian (MS)'),('Southaven Southern Baptist (MS)','Southaven Northpoint Christian (MS)'),
            ('Memphis Southern Baptist (TN)','Southaven Northpoint Christian (MS)'),('Nashville Tennessee Youth Center (TN)','Tennessee Youth Center (TN)')]:
    if b is None: m.pop(a,None)
    else: m[a]=b
r=list(csv.reader(open(P,encoding='utf-8-sig').read().splitlines())); hdr,rows=r[0],r[1:]
seen=set()
for x in rows:
    if x[0] in m: x[2]=m[x[0]]; seen.add(x[0])
    elif x[2] in m: x[2]=m[x[2]]           # retarget rules that pointed at a now-merged name
for k,v in m.items():
    if k not in seen: rows.append([k,'',v])
tgt={x[0]:x[2] for x in rows if x[2] and x[0]!=x[2]}
bad=[(a,b,tgt[b]) for a,b in tgt.items() if b in tgt]
print('rules',len(m),'chains',bad)
if not bad:
    with open(P,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\r\n'); w.writerow(hdr); w.writerows(rows)
for k,v in sorted(m.items()): print(k,'->',v)
