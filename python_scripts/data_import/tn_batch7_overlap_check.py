import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

def show(t):
    cur.execute('SELECT MIN(Season), MAX(Season), COUNT(*) FROM HS_Scores WHERE Home=? OR Visitor=?', t, t)
    row = cur.fetchone()
    print(f'  {t}: {row[0]}-{row[1]}  ({row[2]} games)')

def overlap(a, b):
    cur.execute("""
        SELECT COUNT(DISTINCT s1.Season)
        FROM HS_Scores s1
        JOIN HS_Scores s2 ON s1.Season = s2.Season
        WHERE (s1.Home=? OR s1.Visitor=?) AND (s2.Home=? OR s2.Visitor=?)
    """, a, a, b, b)
    print(f'  Overlapping seasons ({a} & {b}): {cur.fetchone()[0]}')

groups = [
    ('Kingsport Sullivan (TN)', ['Kingsport Sullivan North (TN)', 'Kingsport Sullivan South (TN)', 'Kingsport Sullivan West (TN)']),
    ('Smithville (TN)', ['Smithville DeKalb County (TN)']),
    ('Tyner (TN)', ['Chattanooga Tyner Academy (TN)']),
    ('Pulaski (TN)', ['Pulaski Giles County (TN)']),
    ('Chattanooga Booker T. Washington (TN)', ['Chattanooga B.T. Washington (TN)']),
    ('Speedwell Powell Valley (TN)', ['Powell Valley (TN)']),
    ('Jonesborough (TN)', ['Jonesborough David Crockett (TN)', 'Jonesborough Lamar Washington County (TN)']),
    ('Waynesboro (TN)', ['Waynesboro Wayne County (TN)']),
]

for base, candidates in groups:
    print('=' * 70)
    print(base)
    show(base)
    for c in candidates:
        show(c)
        overlap(base, c)

print()
print('=== Sample opponents for candidate schools (era/geography check) ===')
extra = ['Kingsport Sullivan North (TN)', 'Kingsport Sullivan South (TN)', 'Kingsport Sullivan West (TN)',
         'Smithville DeKalb County (TN)', 'Chattanooga Tyner Academy (TN)', 'Pulaski Giles County (TN)',
         'Chattanooga B.T. Washington (TN)', 'Powell Valley (TN)', 'Jonesborough David Crockett (TN)',
         'Jonesborough Lamar Washington County (TN)', 'Waynesboro Wayne County (TN)']
for t in extra:
    print('-' * 70)
    print(t)
    cur.execute("""
        SELECT TOP 3 Season, Date,
            CASE WHEN Home=? THEN Visitor ELSE Home END AS Opponent,
            Source
        FROM HS_Scores WHERE Home=? OR Visitor=? ORDER BY Date
    """, t, t, t)
    for r in cur.fetchall():
        print('   earliest:', r)
    cur.execute("""
        SELECT TOP 3 Season, Date,
            CASE WHEN Home=? THEN Visitor ELSE Home END AS Opponent,
            Source
        FROM HS_Scores WHERE Home=? OR Visitor=? ORDER BY Date DESC
    """, t, t, t)
    for r in cur.fetchall():
        print('   latest:', r)
