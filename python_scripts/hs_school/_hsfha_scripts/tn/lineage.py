import pickle,csv,os,collections
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/TN/')
res=pickle.load(open('/tmp/hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/hsfha_by.pkl','rb'))
A,B,canon,dom=pickle.load(open('/tmp/hsfha_AB.pkl','rb'))
code={v:k for k,v in hn.items()}
span={}
for r in csv.DictReader(open(D+'hsfha_TN_games.csv',encoding='utf-8')):
    if r['Played']!='1': continue
    s=int(r['Season'])
    for c in (r['TeamCode'],r['OppCode']):
        if c: a,b=span.get(c,(9999,0)); span[c]=(min(a,s),max(b,s))
L=[('Church Hill Volunteer (TN)','Church Hill (Tenn.)','Volunteer (Tenn.)'),('Winchester Franklin County (TN)','Winchester (Tenn.)','Franklin County (Tenn.)'),
('Dickson County (TN)','Dickson (Tenn.)','Dickson County (Tenn.)'),('Evensville Rhea County (TN)','Rhea Central (Tenn.)','Rhea County (Tenn.)'),
('McMinnville Warren County (TN)','McMinnville Central (Tenn.)','Warren County (Tenn.)'),('Lynnville Richland (TN)','Lynnville (Tenn.)','Richland (Tenn.)'),
('Martin Westview (TN)','Martin (Tenn.)','Westview (Tenn.)'),('Copperhill Copper Basin (TN)','Copperhill (Tenn.)','Copper Basin (Tenn.)'),
('Ashland City Cheatham County Central (TN)','Ashland City (Tenn.)','Cheatham County Central (Tenn.)'),('Tiptonville Lake County (TN)','Tiptonville (Tenn.)','Lake County (Tenn.)'),
('Englewood McMinn Central (TN)','Englewood (Tenn.)','McMinn Central (Tenn.)'),('Nashville Pearl-Cohn (TN)','Pearl (Tenn.)','Pearl-Cohn (Tenn.)'),
('Selmer McNairy Central (TN)','Selmer (Tenn.)','McNairy Central (Tenn.)'),('Newbern Dyer County (TN)','Newbern (Tenn.)','Dyer County (Tenn.)'),
('Wartrace Cascade (TN)','Wartrace (Tenn.)','Cascade (Tenn.)'),('Saint Andrews-Sewanee (TN)',"St. Andrew's School (Tenn.)","St. Andrew's-Sewanee (Tenn.)"),
('Gatlinburg (TN)','Gatlinburg (Tenn.)','Gatlinburg-Pittman (Tenn.)'),('Jackson University School of Jackson (TN)','Old Hickory Academy (Tenn.)','University School of Jackson (Tenn.)'),
('Fayetteville (TN)','Fayetteville Central (Tenn.)','Fayetteville (Tenn.)'),('Somerville Fayette County (TN)','Fayette County (Tenn.)','Fayette Academy (Tenn.)')]
for n,p,s in L:
    pc,sc=code.get(p),code.get(s)
    c=by.get(n,collections.Counter())
    # matched games of n by season & code
    pre=collections.Counter(); post=collections.Counter()
    for o,h,ch,cv,x in res:
        if not h: continue
        for side,cd in (('Home',ch),('Visitor',cv)):
            if o[side]!=n: continue
            (pre if cd==pc else post if cd==sc else collections.Counter())[int(o['Season'])]+=1
    print(n,'| pred',p,span.get(pc),'canon:',canon.get(pc),'| succ',s,span.get(sc),'canon:',canon.get(sc))
    print('    pred seasons',min(pre) if pre else None,max(pre) if pre else None,sum(pre.values()),' succ seasons',min(post) if post else None,max(post) if post else None,sum(post.values()))
