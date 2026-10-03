import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

pairs = [
    ('Baxter (TN)', 'Baxter Upperman (TN)'),
    ('Bruceton Central (TN)', 'Hollow Rock-Bruceton Central (TN)'),
    ('Huntsville (TN)', 'Huntsville Scott (TN)'),
    ('Alamo (TN)', 'Alamo Crockett County (TN)'),
    ('Millington (TN)', 'Millington Central (TN)'),
    ('Millington (TN)', 'Memphis Millington (TN)'),
    ('Boones Creek (TN)', 'Johnson City Boones Creek (TN)'),
]

for a, b in pairs:
    print('=' * 70)
    print(f'{a}  vs  {b}')
    for t in (a, b):
        cur.execute('SELECT MIN(Season), MAX(Season), COUNT(*) FROM HS_Scores WHERE Home=? OR Visitor=?', t, t)
        row = cur.fetchone()
        print(f'  {t}: {row[0]}-{row[1]}  ({row[2]} games)')
    # overlap check
    cur.execute("""
        SELECT COUNT(DISTINCT s1.Season)
        FROM HS_Scores s1
        JOIN HS_Scores s2 ON s1.Season = s2.Season
        WHERE (s1.Home=? OR s1.Visitor=?) AND (s2.Home=? OR s2.Visitor=?)
    """, a, a, b, b)
    overlap = cur.fetchone()[0]
    print(f'  Overlapping seasons (both names active same year): {overlap}')

print()
print('=== "Maury (TN)" -- Jefferson County (Dandridge) or Maury County (Middle TN)? ===')
t = 'Maury (TN)'
cur.execute('SELECT MIN(Season), MAX(Season), COUNT(*) FROM HS_Scores WHERE Home=? OR Visitor=?', t, t)
row = cur.fetchone()
print(f'  Season range: {row[0]}-{row[1]}  Games: {row[2]}')
cur.execute("""
    SELECT TOP 8 Season, Date,
        CASE WHEN Home=? THEN Visitor ELSE Home END AS Opponent,
        Source
    FROM HS_Scores WHERE Home=? OR Visitor=? ORDER BY Date
""", t, t, t)
for r in cur.fetchall():
    print('   sample:', r)
