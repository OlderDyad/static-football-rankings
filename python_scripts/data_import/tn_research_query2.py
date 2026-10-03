import pyodbc, csv, os

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

teams = [
    'Nashville West (TN)', 'Johnson City (TN)', 'Knoxville Carter (TN)',
]

# Repo root is two levels up from python_scripts\data_import
repo_root = os.path.join('..', '..')
alias_path = os.path.join(repo_root, 'excel_files', 'State_Aliases_ProperNames', 'TN_Alias_Rules_ACTIVE.csv')

print('=== Possible near-matches already in alias file ===')
with open(alias_path, newline='', encoding='utf-8') as f:
    reader = list(csv.DictReader(f))

# Specifically check for the Carter / Strawberry Plains overlap
print()
print('--- Rows containing "Carter" ---')
for r in reader:
    if 'carter' in r['Team_Name'].lower():
        print(' ', r['Team_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))

print()
print('--- Rows containing "West" (Nashville area) ---')
for r in reader:
    if 'nashville' in r['Team_Name'].lower() and 'west' in r['Team_Name'].lower():
        print(' ', r['Team_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))

print()
print('--- Rows containing "Science Hill" or "Johnson City" ---')
for r in reader:
    n = r['Team_Name'].lower()
    if 'science hill' in n or 'johnson city' in n:
        print(' ', r['Team_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))

# Confirm Strawberry Plains Carter's own game stats directly
print()
print('=== Strawberry Plains Carter (TN) direct check ===')
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
