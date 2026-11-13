import pickle,csv,os,collections
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/NC/')
res=pickle.load(open('/tmp/nc_hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/nc_hsfha_by.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/nc_hsfha_AB.pkl','rb'))
span={}
for r in csv.DictReader(open(D+'hsfha_NC_games.csv',encoding='utf-8')):
    if r['Played']!='1': continue
    s=int(r['Season'])
    for c in (r['TeamCode'],r['OppCode']):
        if c: a,b=span.get(c,(9999,0)); span[c]=(min(a,s),max(b,s))
names=['Wadesboro Anson (NC)','Kinston (NC)','Marshall Madison (NC)','Ahoskie Hertford County (NC)','Sylva Smoky Mountain (NC)','Burlington (NC)','Burlington Walter M. Williams (NC)',
 'Warrenton (NC)','Warrenton Warren County (NC)','Edenton (NC)','Edenton John A. Holmes (NC)','Nashville (NC)','Nashville Nash Central (NC)','Elizabeth City Pasquotank (NC)',
 'Elizabeth City Pasquotank County (NC)','Elizabeth City (NC)','Laurinburg (NC)','Laurinburg Scotland (NC)','Wilson (NC)','Greenville (NC)','Winston-Salem (NC)','Candler Enka (NC)','Oxford (NC)','Oxford Orphanage (NC)','Rutherfordton (NC)','Newton-Conover (NC)','Newton (NC)']
for n in names:
    c=by.get(n)
    if not c: print(n,'no matches'); continue
    tot=sum(c.values())
    seas=collections.defaultdict(list)
    for o,h,ch,cv,x in res:
        if not h: continue
        for side,cd in (('Home',ch),('Visitor',cv)):
            if o[side]==n: seas[cd].append(int(o['Season']))
    print(n,tot,'|',[(hn.get(k,k),v,(min(seas[k]),max(seas[k])),span.get(k)) for k,v in c.most_common(3) if v>=5])
