import pickle,collections
co,pos,G=pickle.load(open('/tmp/tn_geo.pkl','rb'))
for me in ('Knoxville Halls (TN)','Halls (TN)'):
    c=collections.Counter()
    for g in G:
        if me in (g['Home'],g['Visitor']):
            o=g['Visitor'] if g['Home']==me else g['Home']
            if o.endswith('(KY)') or o.endswith('(VA)'): c[(o,g['Src'][:14], g['Season'][:3])]+=1
    print('##',me); 
    for k,v in sorted(c.items()): print(v,k)
