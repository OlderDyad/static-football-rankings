import pyodbc, csv, os

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

teams = [
    'Maryville Lanier (TN)', 'South Harriman Roane County (TN)', 'Memphis King Prep (TN)',
    'Blountville (TN)', 'Gatlinburg (TN)', 'Nashville Cameron (TN)', 'Dickson (TN)',
    'Arlington Memphis Nighthawks (TN)', 'Etowah (TN)', 'Rockvale (TN)',
    'Hendersonville Christian Academy (TN)', 'Blanche (TN)', 'Nashville Wallace Academy (TN)',
    'Mount Juliet Green Hill (TN)', 'Ducktown (TN)',
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
        SELECT TOP 2 Season, Date,
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
keys = ['maryville', 'harriman', 'roane', 'king prep', 'blountville', 'gatlinburg',
        'cameron', 'dickson', 'nighthawks', 'etowah', 'rockvale', 'hendersonville',
        'blanche', 'wallace', 'green hill', 'mount juliet', 'ducktown']
for k in keys:
    matches = [r['Alias_Name'] for r in reader if k in r['Alias_Name'].lower()]
    print(f'{k}: {matches}')
