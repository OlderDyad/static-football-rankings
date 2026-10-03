"""
STEP 1 of 2 - PREVIEW ONLY. Nothing is written to the database.

Builds the exact change list for the NC-paper cleanup and saves it to nc_cleanup_plan.json,
which nc_cleanup_commit.py applies (by row ID / alias key only - nothing pattern-based).

  python nc_cleanup_preview.py > nc_cleanup_preview.txt
"""
import json, pyodbc
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()
CN, CO, GR = 'The Charlotte News', 'The Charlotte Observer', 'The Greensboro Record'
NC_PAPERS = (CN, CO, GR)
plan = {'alias_updates': [], 'score_updates': []}

def hdr(t): print('\n' + '=' * 100 + '\n' + t + '\n' + '=' * 100)

# ------------------------------------------------------------------------------------------
hdr('A. ALIAS RULES TO REPOINT  (alias, region, current -> new)')
ALIAS_FIX = [
    # (alias, regions, only-if-currently, new target)
    ('Lexington',        [CN],         'Lexington (SC)',                       'Lexington (NC)'),
    ('Farmville',        [CN, GR],     'Farmville (VA)',                       'Farmville (NC)'),
    ('LaGrange',         [CN],         'LaGrange (GA)',                        'LaGrange North Lenoir (NC)'),
    ('La Grange',        [CN],         'LaGrange (GA)',                        'LaGrange North Lenoir (NC)'),
    ('Bath',             [CN, CO],     'Hot Springs Bath County (VA)',         'Bath (NC)'),
    ('Hot Springs',      [CN, CO, GR], 'Hot Springs Bath County (VA)',         'Hot Springs (NC)'),
    ('Cleveland',        [CN, CO],     'Cleveland (TN)',                       'Cleveland (NC)'),
    ('Bennett',          [CN, CO],     'Kingsport Dobyns-Bennett (TN)',        'Bennett (NC)'),
    ('Lexington Dunbar', [CN],         'Lexington Paul Laurence Dunbar (KY)',  'Lexington Dunbar (NC)'),
    ('Nathanael Green',  [CN],         'Siloam Nathanael Greene Academy (GA)', 'Nathanael Greene (NC)'),
    ('Nathaniel Greene', [CN],         'Siloam Nathanael Greene Academy (GA)', 'Nathanael Greene (NC)'),
]
for alias, regions, cur_target, new in ALIAS_FIX:
    for reg in regions:
        cur.execute("SELECT Standardized_Name FROM HS_Team_Name_Alias WHERE Alias_Name = ? AND Newspaper_Region = ?", alias, reg)
        r = cur.fetchone()
        if r and r[0] == cur_target:
            plan['alias_updates'].append({'alias': alias, 'region': reg, 'old': cur_target, 'new': new})
            print(f'  CHANGE  {alias!r:22} [{reg}]  {cur_target}  ->  {new}')
        else:
            print(f'  skip    {alias!r:22} [{reg}]  currently {r[0] if r else "(no rule)"}')

# Weaverville-Barnardsville: every rule pointing at the (VA) name, any spelling
cur.execute("SELECT Alias_Name, Newspaper_Region FROM HS_Team_Name_Alias WHERE Standardized_Name = 'Weaverville-Barnardsville (VA)'")
for a, reg in cur.fetchall():
    plan['alias_updates'].append({'alias': a, 'region': reg, 'old': 'Weaverville-Barnardsville (VA)', 'new': 'Weaverville-Barnardsville (NC)'})
    print(f'  CHANGE  {a!r:22} [{reg}]  Weaverville-Barnardsville (VA)  ->  Weaverville-Barnardsville (NC)')
# Lees-McRae: one varsity name, JV left alone
cur.execute("""SELECT Alias_Name, Newspaper_Region, Standardized_Name FROM HS_Team_Name_Alias
               WHERE Standardized_Name IN ('Lees-McRae Junior College (NC)')""")
for a, reg, old in cur.fetchall():
    plan['alias_updates'].append({'alias': a, 'region': reg, 'old': old, 'new': 'Lees-McRae College (NC)'})
    print(f'  CHANGE  {a!r:22} [{reg}]  {old}  ->  Lees-McRae College (NC)')

# ------------------------------------------------------------------------------------------
hdr('B. GAMES TO REFILE  (by row ID)')
def stage(label, wrong, right, where_sql, params):
    cur.execute(f"""SELECT ID, Date, Home, Home_Score, Visitor, Visitor_Score, Source FROM HS_Scores
                    WHERE (Home = ? OR Visitor = ?) AND ({where_sql}) ORDER BY Date""", wrong, wrong, *params)
    rows = cur.fetchall()
    print(f'\n-- {label}:  {wrong}  ->  {right}   ({len(rows)} game(s))')
    for r in rows:
        side = 'Home' if r.Home == wrong else 'Visitor'
        plan['score_updates'].append({'id': str(r.ID), 'side': side, 'old': wrong, 'new': right})
        print(f'     {r.Date} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')

stage('Farmville vs eastern-NC teams', 'Farmville (VA)', 'Farmville (NC)',
      "Home IN ('New Bern (NC)','Vanceboro West Craven (NC)') OR Visitor IN ('New Bern (NC)','Vanceboro West Craven (NC)')", [])
stage('LaGrange vs Selma', 'LaGrange (GA)', 'LaGrange North Lenoir (NC)', "Home = 'Selma (NC)' OR Visitor = 'Selma (NC)'", [])
stage('Hot Springs (Madison Co.) vs mountain NC teams', 'Hot Springs Bath County (VA)', 'Hot Springs (NC)',
      "Home LIKE '%(NC)' OR Visitor LIKE '%(NC)'", [])
# Denton (1959-10-03) and Allen Jay (1959-11-28) left out: Andrews (NC) already has other games those days
ANDREWS_OPP = ("'Franklin (NC)','Bryson City Swain County (NC)','Hayesville (NC)','Mebane Eastern Alamance (NC)',"
               "'Southern Pines (NC)'")
stage('Andrews (Cherokee Co.) - mountain neighbours + 1958-59 NC playoffs', 'Andrews (SC)', 'Andrews (NC)',
      f"Home IN ({ANDREWS_OPP}) OR Visitor IN ({ANDREWS_OPP})", [])
COL_OPP = "'Plymouth (NC)','Edenton (NC)','Williamston (NC)','Ahoskie (NC)','Manteo (NC)','Windsor (NC)','Engelhard (NC)','Weeksville (NC)','Rich Square (NC)','Ahoskie Hertford County (NC)'"
stage('Columbia (Tyrrell Co.) vs Albemarle-sound teams', 'Columbia (SC)', 'Columbia (NC)',
      f"Home IN ({COL_OPP}) OR Visitor IN ({COL_OPP})", [])
stage('Greenville (SC) games filed as Greenville (NC) - SC opponents (Anderson, Gaffney, Parker, Spartanburg...)',
      'Greenville (NC)', 'Greenville (SC)', "Home LIKE '%(SC)' OR Visitor LIKE '%(SC)'", [])
stage('Weaverville-Barnardsville state typo', 'Weaverville-Barnardsville (VA)', 'Weaverville-Barnardsville (NC)', '1=1', [])
stage('Lees-McRae one varsity name', 'Lees-McRae Junior College (NC)', 'Lees-McRae College (NC)', '1=1', [])

# ------------------------------------------------------------------------------------------
hdr('C. CONTEXT FOR YOUR REVIEW (not changed)')
print('\n-- Andrews (NC) 1958-1959 schedule (do the playoff games fit?)')
cur.execute("""SELECT Date, Home, Home_Score, Visitor, Visitor_Score FROM HS_Scores
               WHERE Season IN (1958,1959) AND (Home='Andrews (NC)' OR Visitor='Andrews (NC)') ORDER BY Date""")
for r in cur.fetchall(): print(f'     {r.Date} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}')
print('\n-- Left alone, need a call: Andrews 1932 vs Beaufort, 1954 vs Reidsville; Hartsville (SC) vs Marion/Mount Pleasant; Cameron (SC) 1954')
cur.execute("""SELECT Date, Home, Home_Score, Visitor, Visitor_Score, Source FROM HS_Scores WHERE
   (('Andrews (SC)' IN (Home,Visitor)) AND (Home IN ('Beaufort (NC)','Reidsville (NC)') OR Visitor IN ('Beaufort (NC)','Reidsville (NC)')))
or (('Hartsville (SC)' IN (Home,Visitor)) AND Season IN (1948,1959) AND (Home LIKE '%(NC)' OR Visitor LIKE '%(NC)'))
or (('Cameron (SC)' IN (Home,Visitor)) AND (Home LIKE '%(NC)' OR Visitor LIKE '%(NC)')) ORDER BY Date""")
for r in cur.fetchall(): print(f'     {r.Date} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
print('\n-- SUSPECT: Columbia (SC) vs "Greenville (NC)" from NC papers - may really be Greenville (SC). Alias rules for Greenville:')
cur.execute("SELECT Alias_Name, Newspaper_Region, Standardized_Name FROM HS_Team_Name_Alias WHERE Alias_Name LIKE 'Greenville%' AND Newspaper_Region IN (?,?,?) ORDER BY Alias_Name", *NC_PAPERS)
for r in cur.fetchall(): print(f'     {r.Alias_Name!r} [{r.Newspaper_Region}] -> {r.Standardized_Name}')
cur.execute("""SELECT Date, Home, Home_Score, Visitor, Visitor_Score, Source FROM HS_Scores
               WHERE 'Greenville (NC)' IN (Home,Visitor) AND (Home LIKE '%(SC)' OR Visitor LIKE '%(SC)') ORDER BY Date""")
rows = cur.fetchall(); print(f'   Greenville (NC) vs SC opponents: {len(rows)} game(s)')
for r in rows[:40]: print(f'     {r.Date} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
print('\n-- Do the target names exist in HS_Team_Names?')
for n in sorted({u['new'] for u in plan['alias_updates']} | {u['new'] for u in plan['score_updates']}):
    cur.execute("SELECT COUNT(*) FROM HS_Team_Names WHERE Team_Name = ?", n); t = cur.fetchone()[0]
    print(f'     {"yes" if t else "NO "}  {n}')

json.dump(plan, open('nc_cleanup_plan.json', 'w'), indent=1)
print(f"\nPlan saved to nc_cleanup_plan.json: {len(plan['alias_updates'])} alias rule(s), {len(plan['score_updates'])} game row(s).")
print('Review this output, then run:  python nc_cleanup_commit.py')
