import pyodbc, csv, os

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

teams = [
    'Sevierville (TN)', 'Nashville Lawson (TN)', 'Memphis FCA (TN)', 'Coalfield Yellow (TN)',
    'Clarksville Kirkwood (TN)', 'Cedar Hill (TN)', 'York (TN)', 'Greeneville Greene (TN)',
    'Winchester (TN)', 'East Nashville Magnet (TN)', 'Livingston (TN)', 'Springfield Bransford (TN)',
    'Jackson University School (TN)', 'Horace Maynard (TN)', 'Clarksville Burt (TN)',
]

for t in teams:
    print('=' * 70)
    print(t)
    cur.execute('SELECT MIN(Season), MAX(Season), COUNT(*) FROM HS_Scores WHERE Home=? OR Visitor=?', t, t)
    row = cur.fetchone()
    print(f'  Season range: {row[0]}-{row[1]}  Games: {row[2]}')
    cur.execute("""
        SELECT TOP 4 Season, Date,
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
print('=== Check for near-duplicate/variant names already in alias file ===')
repo_root = os.path.join('..', '..')
alias_path = os.path.join(repo_root, 'excel_files', 'State_Aliases_ProperNames', 'TN_Alias_Rules_ACTIVE.csv')
with open(alias_path, newline='', encoding='utf-8-sig') as f:
    reader = list(csv.DictReader(f))
keys = ['sevierville', 'nashville lawson', 'lawson', 'memphis fca', 'coalfield', 'clarksville kirkwood',
        'kirkwood', 'cedar hill', 'york', 'greeneville greene', 'winchester', 'east nashville magnet',
        'livingston', 'springfield bransford', 'bransford', 'university school', 'horace maynard',
        'maynard', 'clarksville burt', 'burt']
for k in keys:
    matches = [r['Alias_Name'] for r in reader if k in r['Alias_Name'].lower()]
    print(f'{k}: {matches}')
