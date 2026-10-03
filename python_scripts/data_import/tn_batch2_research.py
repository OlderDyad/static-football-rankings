import pyodbc, csv, os

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

teams = [
    'Baxter (TN)', 'Memphis Messick (TN)', 'Bruceton Central (TN)', 'White Bluff (TN)',
    'Huntsville (TN)', 'Alamo (TN)', 'Millington (TN)', 'Boones Creek (TN)',
    'Dandridge Maury (TN)', 'Halls (TN)',
]

for t in teams:
    print('=' * 70)
    print(t)
    cur.execute('SELECT MIN(Season), MAX(Season), COUNT(*) FROM HS_Scores WHERE Home=? OR Visitor=?', t, t)
    row = cur.fetchone()
    print(f'  Season range: {row[0]}-{row[1]}  Games: {row[2]}')
    cur.execute("""
        SELECT TOP 5 Season, Date,
            CASE WHEN Home=? THEN Visitor ELSE Home END AS Opponent,
            Source
        FROM HS_Scores WHERE Home=? OR Visitor=? ORDER BY Date
    """, t, t, t)
    for r in cur.fetchall():
        print('   sample:', r)
    cur.execute("""
        SELECT TOP 3 Season, Date,
            CASE WHEN Home=? THEN Visitor ELSE Home END AS Opponent,
            Source
        FROM HS_Scores WHERE Home=? OR Visitor=? ORDER BY Date DESC
    """, t, t, t)
    for r in cur.fetchall():
        print('   recent:', r)

print()
print('=== Confirm "Knoxville Halls (TN)" is already canonical ===')
repo_root = os.path.join('..', '..')
alias_path = os.path.join(repo_root, 'excel_files', 'State_Aliases_ProperNames', 'TN_Alias_Rules_ACTIVE.csv')
with open(alias_path, newline='', encoding='utf-8-sig') as f:
    reader = list(csv.DictReader(f))
for r in reader:
    if 'halls' in r['Alias_Name'].lower():
        print(' ', r['Alias_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))

print()
print('=== Check for near-duplicate/variant names of each batch team already in alias file ===')
keys = ['baxter', 'messick', 'bruceton', 'white bluff', 'huntsville', 'alamo', 'millington', 'boones creek', 'dandridge', 'maury']
for k in keys:
    matches = [r['Alias_Name'] for r in reader if k in r['Alias_Name'].lower()]
    print(f'{k}: {matches}')
