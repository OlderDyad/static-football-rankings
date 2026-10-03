import pyodbc, re

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== All distinct team names containing "Reserve", across all states ===')
cur.execute("""
    SELECT TeamName, COUNT(*) AS Cnt, MIN(Season) AS FirstSeason, MAX(Season) AS LastSeason
    FROM (
        SELECT Home AS TeamName, Season FROM HS_Scores WHERE Home LIKE '%Reserve%'
        UNION ALL
        SELECT Visitor, Season FROM HS_Scores WHERE Visitor LIKE '%Reserve%'
    ) t
    GROUP BY TeamName
    ORDER BY TeamName
""")
rows = cur.fetchall()

town_pattern = re.compile(r'^Reserve\s')  # "Reserve, LA" town-name teams start with "Reserve"
suffix_pattern = re.compile(r'\bReserve\s*\(')  # " ... Reserve (ST)" -- suffix usage

town_rows = []
suffix_rows = []
other_rows = []
for r in rows:
    name = r[0]
    if town_pattern.match(name):
        town_rows.append(r)
    elif suffix_pattern.search(name):
        suffix_rows.append(r)
    else:
        other_rows.append(r)

print(f'\n--- Town-name teams ("Reserve, LA" -- leave alone): {len(town_rows)} ---')
for r in town_rows:
    print(' ', r)

print(f'\n--- Suffix usage ("<School> Reserve (ST)" -- candidates for B-team rename): {len(suffix_rows)} ---')
for r in suffix_rows:
    print(' ', r)

print(f'\n--- Other/unclear matches: {len(other_rows)} ---')
for r in other_rows:
    print(' ', r)
