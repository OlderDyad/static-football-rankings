import pickle,collections
co,pos,G=pickle.load(open('/tmp/tn_geo.pkl','rb'))
KH,H,HK='Knoxville Halls (TN)','Halls (TN)','Harlan Grays Knob Hall (KY)'
harlan={'Alva Black Star (KY)','Benham (KY)','Blackey Stuart Robinson (KY)','Evarts (KY)','Harlan (KY)','Hyden Leslie County (KY)','Loyall (KY)','Lynch (KY)','Wallins Creek (KY)','Whitesburg (KY)','Cumberland (KY)','Hazard (KY)','Pineville (KY)','Pineville Bell County (KY)','Middlesboro (KY)','Barbourville (KY)','Barbourville Knox Central (KY)','Knox Central (KY)','Corbin Lynn Camp (KY)','Corbin (KY)','Pennington Gap Pennington (VA)'}
wky={'Fulton City (KY)','Hickman Fulton County (KY)','Mayfield Graves County (KY)','Murray (KY)','Murray Calloway County (KY)','Paducah McCracken County (KY)'}
mv=collections.defaultdict(list); left=collections.Counter()
for g in G:
    for me in (KH,H):
        if me not in (g['Home'],g['Visitor']): continue
        o=g['Visitor'] if g['Home']==me else g['Home']
        p=pos.get(o); s=int(g['Season'])
        if o in harlan and s<=1963: mv[(me,HK)].append((g,o)); continue
        if me==KH and (o in wky or (p and p[1]<-87.6 and not o.endswith('(KY)'))): mv[(me,H)].append((g,o)); continue
        if me==H and o not in harlan and p and p[1]>-85.8: mv[(me,KH)].append((g,o)); continue
        left[(me,'W' if p and p[1]<-87.6 else 'E' if p and p[1]>-85.8 else 'M')]+=1
for k,v in mv.items():
    print(k,len(v)); print('   ',collections.Counter(o for g,o in v).most_common(40))
print(left)
for (a,b),v in mv.items():
    fn={'Halls (TN)':'halls','Knoxville Halls (TN)':'khalls','Harlan Grays Knob Hall (KY)':'hallky'}
    open(f'/tmp/{fn[a]}_to_{fn[b]}.csv','w').write('ID\n'+'\n'.join(g['ID'] for g,o in v)+'\n')
