import pickle,os
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/AR/')
res=pickle.load(open('/tmp/ar_hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/ar_hsfha_by.pkl','rb'))
code={v:k for k,v in hn.items()}
P=[('Amity Centerpoint (AR)','Amity (Ark.)','Amity (AR)'),('Little Rock Southwest Christian Academy (AR)','Little Rock Southwest (Ark.)','Little Rock Southwest (AR)'),
   ('West Helena Central (AR)','West Helena Woodruff (Ark.)','West Helena Woodruff (AR)'),('Hartman Johnson County Westside (AR)','Hartman (Ark.)','Hartman (AR)')]
L=[]
for i,(n,h,t) in enumerate(P):
    c=code[h]; s=set()
    for o,hh,ch,cv,x in res:
        if hh and ((o['Home']==n and ch==c) or (o['Visitor']==n and cv==c)): s.add(o['ID'])
    fn=f'hsfha_lin_{i:02d}.csv'; open(D+fn,'w').write('ID\n'+'\n'.join(sorted(s))+'\n')
    L.append(f'move-team AR --from "{n}" --to "{t}" --seasons 1880-2026 --ids {fn} --reason "HSFHA-AR school code: game belongs to {t}" --commit'); print(len(s),n,'->',t)
L.append('move-team AR --from "Palestine-Wheatley (AR)" --to "Palestine (AR)" --seasons 1880-1986 --reason "Lineage split (consolidation 1987, HSFHA-AR): Palestine era" --commit')
open('/tmp/ar_lin.txt','w').write('\n'.join(L)+'\n')
