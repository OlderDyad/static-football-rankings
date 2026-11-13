import pickle,sys,os,csv
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/SC/')
res=pickle.load(open('/tmp/sc_hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/sc_hsfha_by.pkl','rb'))
name,hname,out=sys.argv[1],sys.argv[2],sys.argv[3]
ids=[]
for o,h,ch,cv,x in res:
    if not h: continue
    for side,cd in (('Home',ch),('Visitor',cv)):
        if o[side].strip()==name and hn.get(cd)==hname: ids.append((o['ID'],o['Season']))
w=csv.writer(open(D+out,'w',newline='')); w.writerow(['ID'])
for i,s in ids: w.writerow([i])
print(name,'->',hname,len(ids),'seasons',min(s for i,s in ids) if ids else '',max(s for i,s in ids) if ids else '')
