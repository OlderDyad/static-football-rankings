"""
Read-only check for the Utah-newspaper batch (Ogden Standard-Examiner, Salt Lake Tribune,
Provo Sunday Herald, 1925-1969) BEFORE running apply_corrections.py.
Nothing is written to the database.

  python ut_batch_alias_validation.py > ut_batch_alias_validation.txt
"""
import pyodbc
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()
REGIONS = ('The Ogden Standard Examiner', 'The Salt Lake Tribune', 'The Sunday Herald')

def games(name):
    cur.execute("""SELECT COUNT(*), MIN(Season), MAX(Season) FROM HS_Scores WHERE Home = ? OR Visitor = ?""", name, name)
    return cur.fetchone()
def is_canonical(name):
    cur.execute("SELECT COUNT(*) FROM HS_Team_Name_Alias WHERE Standardized_Name = ?", name); a = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM HS_Team_Names WHERE Team_Name = ?", name); t = cur.fetchone()[0]
    return a, t
def like(pattern, state):
    cur.execute("""SELECT TOP 12 n, COUNT(*) c, MIN(s), MAX(s) FROM (
                     SELECT Home n, Season s FROM HS_Scores WHERE Home LIKE ? UNION ALL
                     SELECT Visitor, Season FROM HS_Scores WHERE Visitor LIKE ?) x
                   WHERE n LIKE ? GROUP BY n ORDER BY c DESC""", pattern, pattern, f'%({state})')
    return cur.fetchall()

print('=' * 90); print('1. PROPOSED NAMES - do they already exist?  (alias-table hits / HS_Team_Names hits / HS_Scores games)'); print('=' * 90)
proposed = [
 ('Acequia (ID)','%Acequia%','ID'),('Ammon (ID)','%Ammon%','ID'),('Salt Lake City Cathedral (UT)','%Cathedral%','UT'),
 ('Downey (ID)','%Downey%','ID'),('Eden (ID)','%Eden%','ID'),('Ferron (UT)','%Ferron%','UT'),('Ferron (UT)','%South Emery%','UT'),
 ('Huntington (UT)','%Huntington%','UT'),('Huntington (UT)','%North Emery%','UT'),('Iona (ID)','%Iona%','ID'),
 ('King Hill (ID)','%King Hill%','ID'),('Lava Hot Springs (ID)','%Lava%','ID'),('Montour (ID)','%Montour%','ID'),
 ('Moreland (ID)','%Moreland%','ID'),('Paul (ID)','%Paul%','ID'),('Roswell (ID)','%Roswell%','ID'),('Thomas (ID)','%Thomas%','ID'),
 ('Topaz (UT)','%Topaz%','UT'),('Troy (ID)','%Troy%','ID'),('Ucon (ID)','%Ucon%','ID'),('Grand View (ID)','%Grand%View%','ID'),
 ('Valley (WA)','%Valley%','WA'),('Spokane Valley Central Valley (WA)','%Central Valley%','WA'),('Bicknell Wayne (UT)','%Wayne%','UT'),
 ('Ephraim (UT)','%Ephraim%','UT'),('Castle Dale Central (UT)','%Castle Dale%','UT'),('Orderville Valley (UT)','%Valley%','UT'),
 ('Star (ID)','%Star%','ID'),('Richfield (ID)','%Richfield%','ID'),('Hazelton Valley (ID)','%Hazelton%','ID'),
 ('Altamont (UT)','%Alt%','UT'),('Mesquite Virgin Valley (NV)','%Virgin%','NV'),('Rupert Minico (ID)','%Minidoka%','ID'),
 ('Boise Fairmont (ID)','%Fairmont%','ID'),('Richmond (UT)','%Richmond%','UT'),('Richmond (UT)','%North Cache%','UT'),
 ('Boise St. Teresa''s Academy (ID)','%Teresa%','ID'),
]
seen = set()
for name, pat, st in proposed:
    if name not in seen:
        seen.add(name); a, t = is_canonical(name); g = games(name)
        flag = 'OK ' if (a or t or g[0]) else 'NEW'
        print(f'{flag} {name:45s} alias={a:<3} team_names={t:<2} games={g[0]} ({g[1]}-{g[2]})')
    for n, c, lo, hi in like(pat, st):
        if n != name: print(f'        similar: {n:45s} games={c} ({lo}-{hi})')

print(); print('=' * 90); print('2. DO THE CORRECTED CLIPPING TEXTS RESOLVE?  (existing alias per newspaper region)'); print('=' * 90)
for alias in ['Hollister','Kuna','Hansen','Melba','Albion','Oakley','Granger','Uintah','Cathedral','Alterra','Davis','American Fork',
              'Star','Richfield','Wellpinit','Valley','Central','Fairmont','Richmond','Brigham','Diggers','Tigers']:
    cur.execute(f"""SELECT Newspaper_Region, Standardized_Name FROM HS_Team_Name_Alias
                    WHERE Alias_Name = ? AND (Newspaper_Region IN (?,?,?) OR Newspaper_Region = '*Global*')""", alias, *REGIONS)
    hits = cur.fetchall()
    print(f'  {alias:14s}: ' + ('; '.join(f'[{h[0]}] -> {h[1]}' for h in hits) if hits else '(no alias in these regions)'))

print(); print('=' * 90); print('3. CONTEXT FOR THE 5 UNRESOLVED NAMES (games already in HS_Scores that weekend)'); print('=' * 90)
checks = [
 ('Diggers beat Box Elder 13-0', '1950-11-14', '1950-11-20', ['Brigham City Box Elder (UT)', 'South Jordan Bingham (UT)']),
 ('Eagles 51 Moab 13 (set to Millard)', '1950-11-14', '1950-11-20', ['Moab Grand County (UT)', 'Fillmore Millard County (UT)']),
 ('Tigers 39 Morgan 0', '1946-11-12', '1946-11-18', ['Morgan (UT)', 'Orem Lincoln (UT)']),
 ('Millard 46 Richmond 0', '1944-10-10', '1944-10-15', ['Fillmore Millard County (UT)', 'Richfield (UT)']),
 ('South Summit 14 Brigham 0', '1953-10-27', '1953-11-02', ['Kamas South Summit (UT)', 'Brigham City Box Elder (UT)', 'South Jordan Bingham (UT)']),
 ('Nampa 32 Fairmont 13', '1947-10-20', '1947-10-26', ['Nampa (ID)']),
 ('Dixie 25 Virgin 7', '1951-09-18', '1951-09-23', ['Saint George Dixie (UT)', 'Mesquite Virgin Valley (NV)']),
]
for label, d1, d2, teams in checks:
    print(f'-- {label}')
    for t in teams:
        cur.execute("""SELECT Date, Home, Home_Score, Visitor, Visitor_Score, Source FROM HS_Scores
                       WHERE Date BETWEEN ? AND ? AND (Home = ? OR Visitor = ?) ORDER BY Date""", d1, d2, t, t)
        rows = cur.fetchall()
        for r in rows: print(f'     {r.Date} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
        if not rows: print(f'     (no games for {t})')

print(); print('=' * 90); print('4. SAME MISREADS ALREADY SITTING IN HS_Scores FROM EARLIER BATCHES'); print('=' * 90)
ID_TOWNS = ['Hansen','Shoshone','Hailey','Fairfield','Jerome','Bellevue','Glenns Ferry','Wendell','Hagerman','Dietrich','Hazelton','King Hill','Paul','Murtaugh','Gooding','Carey','Castleford','Kimberly','Buhl','Filer','Bliss','Declo']
for team in ['Richfield (UT)', 'Afton Star Valley (WY)']:
    cur.execute(f"""SELECT Date, Home, Home_Score, Visitor, Visitor_Score, Source FROM HS_Scores
                    WHERE Season < 1970 AND ((Home = ? AND Visitor LIKE '%(ID)') OR (Visitor = ? AND Home LIKE '%(ID)'))
                    ORDER BY Date""", team, team)
    rows = cur.fetchall()
    print(f'-- {team} vs Idaho opponents before 1970: {len(rows)} game(s)  (Richfield ID / Star ID mislabeled?)')
    for r in rows: print(f'     {r.Date} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
cur.execute("SELECT COUNT(*), MIN(Season), MAX(Season) FROM HS_Scores WHERE Home = 'Wellpinit (ID)' OR Visitor = 'Wellpinit (ID)'")
print(f'-- Wellpinit (ID) games (Wellpinit is in Washington): {tuple(cur.fetchone())}')
for n in ['Spokane Valley Central Valley (WA)', 'Veradale Central Valley (WA)']:
    print(f'-- {n}: games/min/max = {tuple(games(n))}')
