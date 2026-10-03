import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== All distinct "Bristol..." team names in HS_Scores, with game counts ===')
cur.execute("""
    SELECT TeamName, COUNT(*) AS Cnt, MIN(Season) AS FirstSeason, MAX(Season) AS LastSeason
    FROM (
        SELECT Home AS TeamName, Season FROM HS_Scores WHERE Home LIKE 'Bristol%'
        UNION ALL
        SELECT Visitor, Season FROM HS_Scores WHERE Visitor LIKE 'Bristol%'
    ) t
    GROUP BY TeamName
    ORDER BY Cnt DESC
""")
for r in cur.fetchall():
    print(' ', r)

print()
print('=== Bristol Tennessee (TN) vs Bristol Virginia (VA) head-to-head history ===')
cur.execute("""
    SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE (Home = 'Bristol Tennessee (TN)' AND Visitor = 'Bristol Virginia (VA)')
       OR (Home = 'Bristol Virginia (VA)' AND Visitor = 'Bristol Tennessee (TN)')
    ORDER BY Season
""")
for r in cur.fetchall():
    print(' ', r)

print()
print('=== Any games for "Bristol Battle (VA)" (the odd one) ===')
cur.execute("""
    SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE Home = 'Bristol Battle (VA)' OR Visitor = 'Bristol Battle (VA)'
    ORDER BY Season, Date
""")
for r in cur.fetchall():
    print(' ', r)

print()
print('=== "Bristol (VA)" (the unqualified one -- flagged for merge into Bristol Virginia (VA)) ===')
cur.execute("""
    SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE Home = 'Bristol (VA)' OR Visitor = 'Bristol (VA)'
    ORDER BY Season, Date
""")
rows = cur.fetchall()
print(f'{len(rows)} row(s)')
for r in rows[:15]:
    print(' ', r)

print()
print('=== Current TN alias file entries for Bristol ===')
import csv, os
repo_root = os.path.join('..', '..')
alias_path = os.path.join(repo_root, 'excel_files', 'State_Aliases_ProperNames', 'TN_Alias_Rules_ACTIVE.csv')
with open(alias_path, newline='', encoding='utf-8-sig') as f:
    reader = list(csv.DictReader(f))
for r in reader:
    if 'bristol' in r['Alias_Name'].lower():
        print(' ', r['Alias_Name'], '| GameCount=', r.get('GameCount'), '| Standardized_Name=', r.get('Standardized_Name'))
