import csv,os,glob,shutil,collections,pickle
S=os.path.expanduser('~/mnt/static-football-rankings/python_scripts/hs_school/FL/')
O=os.path.expanduser('~/mnt/Shared_Loren_Maxwell/Florida/'); os.makedirs(O,exist_ok=True)
shutil.copyfile(sorted(glob.glob(S+'FL_q_fl_export_1_*.csv'))[-1],O+'FL-Scores-Full.csv')
shutil.copyfile(sorted(glob.glob(S+'FL_q_fl_export_2_*.csv'))[-1],O+'FL-Team-Names.csv')
hn={r['Code']:r['Name'] for r in csv.DictReader(open(S+'hsfha_FL_schools.csv',encoding='utf-8'))}
# 1 score differences (our dated sources)
r=list(csv.DictReader(open(S+'FL_score_disagreements.csv',encoding='utf-8')))
n=collections.Counter(x['ID'] for x in r)
def kind(s):
    s=s.lower()
    if 'hsfdatabase' in s or s.strip() in ('','ref!','0'): return None
    if 'maxpreps' in s: return 'MaxPreps'
    if '.csv' in s or 'news' in s or 'observer' in s or 'record' in s or 'gazette' in s or 'democrat' in s or 'times' in s or 'advocate' in s or 'journal' in s or 'picayune' in s or 'talk' in s or 'clarion' in s or 'ledger' in s or 'sun herald' in s or 'courier' in s or 'times' in s or 'herald' in s: return 'Newspaper'
    return 'Other web'
rows=[]
for x in r:
    k=kind(x['Source'])
    if not k: continue
    swap=x['HS']==x['HSFHA_VisScore'] and x['VS']==x['HSFHA_HomeScore']
    rows.append([x['Season'],x['Date'],x['Home'],x['HS'],x['Visitor'],x['VS'],k,x['Source'],x['HSFHA_GameID'],x['HSFHA_Date'],x['HSFHA_HomeScore'],x['HSFHA_VisScore'],
                 'Winner/loser reversed' if swap else 'Different score','Teams met more than once - check which game' if n[x['ID']]>1 else '',x['ID']])
with open(O+'FL-HSFHA-Score-Differences.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['Season','OurDate','Home','OurHomeScore','Visitor','OurVisitorScore','OurSourceType','OurSource','HSFHA_GameID','HSFHA_Date','HSFHA_HomeScore','HSFHA_VisitorScore','Difference','Note','OurID']); w.writerows(sorted(rows))
print('scorediff',len(rows),collections.Counter(x[6] for x in rows))
# 2 games we have, HSFHA lacks
u=list(csv.DictReader(open(S+'FL_unmatched_classified.csv',encoding='utf-8')))
lab={'BOTH_COVERED_NO_GAME':'Both schools are on HSFHA that season, game not listed',
     'SEASON_NOT_COVERED':'HSFHA has no season for one of the schools',
     'ONE_TEAM_KNOWN_COVERED':'FL school is on HSFHA that season; opponent not matched to an HSFHA school',
     'ONE_TEAM_KNOWN_NOT_COVERED':'FL school not on HSFHA that season; opponent not matched',
     'SAME_TEAMS_NOT_PLAYED':'HSFHA lists this pairing as not played / no score'}
rows=[[lab[x['Class']],x['Season'],x['Date'],x['Home'],x['HS'],x['Visitor'],x['VS'],x['Source'],x['ID']] for x in u if x['Class'] in lab]
with open(O+'FL-Games-Not-On-HSFHA.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['Category','Season','Date','Home','Home_Score','Visitor','Visitor_Score','Source','OurID']); w.writerows(rows)
print('notonhsfha',len(rows),collections.Counter(x[0][:30] for x in rows))
# 3 HSFHA internal duplicates
pass
# 4 school identity map
mp=list(csv.DictReader(open(S+'hsfha_code_map.csv',encoding='utf-8')))
with open(O+'FL-School-Name-Map.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['HSFHA_Code','HSFHA_School','McKnight_Name','MatchedGames'])
    for x in mp:
        if x['Code'].startswith('FL.'): w.writerow([x['Code'],x['HSFHA_Name'],x['OurName'],x['Votes']])
