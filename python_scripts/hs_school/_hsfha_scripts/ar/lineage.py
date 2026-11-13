import pickle,csv,os,collections
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/AR/')
res=pickle.load(open('/tmp/ar_hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/ar_hsfha_by.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/ar_hsfha_AB.pkl','rb'))
span={}
for r in csv.DictReader(open(D+'hsfha_AR_games.csv',encoding='utf-8')):
    if r['Played']!='1': continue
    s=int(r['Season'])
    for c in (r['TeamCode'],r['OppCode']):
        if c: a,b=span.get(c,(9999,0)); span[c]=(min(a,s),max(b,s))
names=['Palestine-Wheatley (AR)','Amity Centerpoint (AR)','Little Rock Southwest Christian Academy (AR)','West Helena Central (AR)','Hartman Johnson County Westside (AR)','Fort Smith Union Christian Academy (AR)','Camden (AR)','Camden Fairview (AR)','Helena (AR)','Glenwood (AR)','Yellville (AR)','Wilson (AR)','Ola (AR)','Rector (AR)','Mabelvale (AR)']
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
