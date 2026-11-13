import pickle,collections,csv,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/TN/')
by,codeto,hn=pickle.load(open('/tmp/hsfha_by.pkl','rb'))
span={}
for r in csv.DictReader(open(D+'hsfha_TN_games.csv',encoding='utf-8')):
    if r['Played']!='1': continue
    s=int(r['Season'])
    for c in (r['TeamCode'],r['OppCode']):
        if c.startswith('TN.'):
            a,b=span.get(c,(9999,0)); span[c]=(min(a,s),max(b,s))
cty=lambda c:c.split('-')[0]
out=[]
for n,c in sorted(by.items(),key=lambda x:-sum(x[1].values())):
    if not n.endswith('(TN)'): continue
    tot=sum(c.values()); tc=[(k,v) for k,v in c.most_common() if k.startswith('TN.') and v>=8 and v>=0.05*tot]
    if len(tc)<2: continue
    main=tc[0][0]
    for k,v in tc[1:]:
        if cty(k)!=cty(main): kind='OTHER-COUNTY (misattributed)'
        else:
            # successor = later-starting code
            (A,B)=(k,main) if span[k][0]<=span[main][0] else (main,k)
            st=span[B][0]
            feeders=[x for x in span if cty(x)==cty(B) and x!=B and st-2<=span[x][1]<=st and span[x][0]<st]
            ov = span[A][1] >= span[B][0]+1   # both active same years -> separate schools
            kind='OVERLAP (two schools)' if ov else ('CONSOLIDATION (%d schools ended)'%len(feeders) if len(feeders)>=2 else 'RENAME (one predecessor)')
        out.append((n,hn.get(main),span[main],hn.get(k),span[k],v,kind))
w=csv.writer(open(D+'hsfha_split_classify.csv','w',newline='',encoding='utf-8'))
w.writerow(['OurName','MainHSFHA','MainSpan','OtherHSFHA','OtherSpan','Games','Kind'])
for o in out: w.writerow(o); print(o)
