import pyodbc, csv, os

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

repo_root = os.path.join('..', '..')
alias_path = os.path.join(repo_root, 'excel_files', 'State_Aliases_ProperNames', 'TN_Alias_Rules_ACTIVE.csv')

# utf-8-sig strips the BOM so the column name reads as 'Alias_Name', not '﻿Alias_Name'
with open(alias_path, newline='', encoding='utf-8-sig') as f:
    reader = list(csv.DictReader(f))

print('=== Rows containing "Carter" ===')
for r in reader:
    if 'carter' in r['Alias_Name'].lower():
        print(' ', r['Alias_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))

print()
print('=== Rows containing "Nashville" + "West" ===')
for r in reader:
    n = r['Alias_Name'].lower()
    if 'nashville' in n and 'west' in n:
        print(' ', r['Alias_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))

print()
print('=== Rows containing "Science Hill" or "Johnson City" ===')
for r in reader:
    n = r['Alias_Name'].lower()
    if 'science hill' in n or 'johnson city' in n:
        print(' ', r['Alias_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))

print()
print('=== Strawberry Plains Carter (TN) direct DB check ===')
t = 'Strawberry Plains Carter (TN)'
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
print('=== Any other "Carter (TN)" variants in HS_Team_Names / HS_Scores not yet in alias file ===')
cur.execute("""
    SELECT DISTINCT Home AS TeamName FROM HS_Scores WHERE Home LIKE '%Carter%(TN)%'
    UNION
    SELECT DISTINCT Visitor FROM HS_Scores WHERE Visitor LIKE '%Carter%(TN)%'
""")
for r in cur.fetchall():
    print('  ', r[0])
