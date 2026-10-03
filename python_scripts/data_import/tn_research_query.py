import pyodbc, csv

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

teams = [
    'Nashville West (TN)', 'Murfreesboro Central (TN)', 'Johnson City (TN)',
    'Jacksboro (TN)', 'Paris Grove (TN)', 'Sewanee Military Academy (TN)',
    'Knoxville Carter (TN)', 'Charlotte (TN)', 'Memphis Tech (TN)', 'Knoxville Stair Tech (TN)'
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

print()
print('=== Possible near-matches already in alias file ===')
with open(r'excel_files\State_Aliases_ProperNames\TN_Alias_Rules_ACTIVE.csv', newline='', encoding='utf-8') as f:
    reader = list(csv.DictReader(f))
for t in teams:
    key = t.split(' (')[0].split()[0].lower()  # crude first-word match (city)
    matches = [r['Team_Name'] for r in reader if key in r['Team_Name'].lower() and r['Team_Name'] != t]
    print(f'{t}: {matches[:10]}')
