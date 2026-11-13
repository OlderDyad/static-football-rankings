import pickle,csv,os
A,B,canon,dom=pickle.load(open('/tmp/hsfha_AB.pkl','rb'))
hn={r['Code']:r['Name'] for r in csv.DictReader(open(os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/TN/hsfha_TN_schools.csv'),encoding='utf-8'))}
for c,n in hn.items():
    if n.startswith('Tennessee Military Institute'): canon[c]='Sweetwater Tennessee Military Institute (TN)'
    if n.startswith('Northpoint Christian'): canon[c]='Southaven Northpoint Christian (MS)'
pickle.dump((A,B,canon,dom),open('/tmp/hsfha_AB.pkl','wb'))
