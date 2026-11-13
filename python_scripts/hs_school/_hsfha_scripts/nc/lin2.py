import pickle,os,collections
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/NC/')
res=pickle.load(open('/tmp/nc_hsfha_res.pkl','rb'))
by,codeto,hn=pickle.load(open('/tmp/nc_hsfha_by.pkl','rb'))
code={v:k for k,v in hn.items()}; code['SC.GV-028']='SC.GV-028'
P=[('Wadesboro Anson (NC)','Bowman (Wadesboro, N.C.)','Wadesboro Bowman (NC)'),
('Nashville Nash Central (NC)','Nashville (N.C.)','Nashville (NC)'),
('Burlington (NC)','Williams (N.C.)','Burlington Walter M. Williams (NC)'),('Burlington Walter M. Williams (NC)','Burlington (N.C.)','Burlington (NC)'),
('Warrenton Warren County (NC)','Graham (Warrenton, N.C.)','Warrenton John Graham (NC)'),
('Edenton (NC)','Holmes (N.C.)','Edenton John A. Holmes (NC)'),('Laurinburg (NC)','Scotland (N.C.)','Laurinburg Scotland (NC)'),
('Wilson (NC)','Coon (N.C.)','Wilson Coon (NC)'),('Wilson (NC)','Fike (N.C.)','Wilson Fike (NC)'),
('Greenville (NC)','J.H. Rose (N.C.)','Greenville J.H. Rose (NC)'),('Greenville (NC)','SC.GV-028','Greenville (SC)'),
('Winston-Salem (NC)','R.J. Reynolds (N.C.)','Winston-Salem R.J. Reynolds (NC)')]
L=[]
for i,(n,h,t) in enumerate(P):
    c=code[h]; s=set()
    for o,hh,ch,cv,x in res:
        if not hh: continue
        if (o['Home']==n and ch==c) or (o['Visitor']==n and cv==c): s.add(o['ID'])
    fn=f'hsfha_lin_{i:02d}.csv'; open(D+fn,'w').write('ID\n'+'\n'.join(sorted(s))+'\n')
    L.append(f'move-team NC --from "{n}" --to "{t}" --seasons 1880-2026 --ids {fn} --reason "HSFHA-NC school code: game belongs to {t}" --commit')
    print(len(s),n,'->',t)
S=[('Kinston (NC)','Kinston Grainger (NC)','1880-1969'),('Marshall Madison (NC)','Marshall (NC)','1880-1972'),('Ahoskie Hertford County (NC)','Ahoskie (NC)','1880-1987'),
   ('Sylva Smoky Mountain (NC)','Sylva-Webster (NC)','1880-1987'),('Candler Enka (NC)','Candler (NC)','1880-1954')]
L+=[f'move-team NC --from "{a}" --to "{b}" --seasons {s} --reason "Lineage split (consolidation, HSFHA-NC): {b} era" --commit' for a,b,s in S]
open('/tmp/nc_lin_lines.txt','w').write('\n'.join(L)+'\n')
