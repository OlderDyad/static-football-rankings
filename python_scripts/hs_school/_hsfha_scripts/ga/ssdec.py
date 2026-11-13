import csv,pickle,glob,os,collections
D=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/GA/')
res=pickle.load(open('/tmp/ga_hsfha_res.pkl','rb'))
sc={o['ID']:(x,h['GameID'] if h else None) for o,h,ch,cv,x in res}
f=sorted(glob.glob(D+'GA_same_score_2*.csv'))[-1]
out=[];c=collections.Counter()
for r in csv.DictReader(open(f,encoding='utf-8-sig')):
    a,b=r['AID'],r['BID']; sa,ga=sc.get(a,(0,None)); sb,gb=sc.get(b,(0,None))
    if sa==2 and sb<2: k='A'
    elif sb==2 and sa<2: k='B'
    elif sa==2 and sb==2:
        k='A' if ga!=gb and False else ('X' if ga!=gb else ('A' if r['Decision']!='DROP A' else 'B'))
    elif r['Decision']=='DROP A': k='B'
    elif r['Decision']=='DROP B': k='A'
    else: k='X'
    # tool decided against HSFHA? note
    if r['Decision']=='DROP A' and k=='A' or r['Decision']=='DROP B' and k=='B': c['override']+=1
    c[(r['Decision'],k)]+=1; out.append((a,b,k))
w=csv.writer(open(D+'GA_same_score_decisions.csv','w',newline='')); w.writerow(['AID','BID','Keep']); w.writerows(out)
for k,v in sorted(c.items(),key=str): print(k,v)
