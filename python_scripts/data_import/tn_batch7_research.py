import pyodbc, csv, os

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

teams = [
    'Kingsport Sullivan (TN)', 'Gray Trinity Academy (TN)', 'Chattanooga Brainerd Christian (TN)',
    'Smithville (TN)', 'Tyner (TN)', 'Memphis Prep (TN)', 'Pulaski (TN)', 'Murfreesboro Holloway (TN)',
    'Johnson City Tennessee Silverbacks (TN)', 'Alcoa Hall (TN)', 'Chattanooga Booker T. Washington (TN)',
    'Speedwell Powell Valley (TN)', 'Jonesborough (TN)', 'Lakeland Preparatory (TN)', 'Waynesboro (TN)',
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
keys = ['kingsport sullivan', 'gray trinity', 'trinity academy', 'brainerd christian', 'smithville',
        'tyner', 'memphis prep', 'pulaski', 'holloway', 'silverbacks', 'alcoa hall', 'alcoa',
        'booker t. washington', 'b.t. washington', 'speedwell', 'powell valley', 'jonesborough',
        'lakeland preparatory', 'lakeland', 'waynesboro']
for k in keys:
    matches = [r['Alias_Name'] for r in reader if k in r['Alias_Name'].lower()]
    print(f'{k}: {matches}')
