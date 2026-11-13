import pickle,collections,csv
co,pos,G=pickle.load(open('/tmp/tn_geo.pkl','rb'))
KH,H='Knoxville Halls (TN)','Halls (TN)'
res=collections.Counter(); mv={KH:[],H:[]}; mid=[]
for g in G:
    for me in (KH,H):
        if me in (g['Home'],g['Visitor']):
            o=g['Visitor'] if g['Home']==me else g['Home']
            p=pos.get(o)
            z='?' if not p else 'W' if p[1]<-87.6 else 'E' if p[1]>-85.8 else 'M'
            res[(me,z)]+=1
            if me==KH and z=='W': mv[KH].append((g,o))
            if me==H and z=='E': mv[H].append((g,o))
            if z in 'M?': mid.append((me,g['Season'],o,p))
print(res)
print('KH->Halls sample',[ (g['Season'],o) for g,o in mv[KH][:12]])
print('Halls->KH',[ (g['Season'],o,g['Src']) for g,o in mv[H]])
print('mid/unknown',mid)
open('/tmp/kh_to_halls.csv','w').write('ID\n'+'\n'.join(g['ID'] for g,o in mv[KH])+'\n')
open('/tmp/halls_to_kh.csv','w').write('ID\n'+'\n'.join(g['ID'] for g,o in mv[H])+'\n')
