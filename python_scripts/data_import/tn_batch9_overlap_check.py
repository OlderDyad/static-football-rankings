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
    ('Lafayette (TN)', ['Lafayette Macon County (TN)']),
    ('Decaturville Riverside (TN)', ['Parsons-Riverside (TN)', 'Decatur County-Riverside (TN)']),
    ('Rutledge (TN)', ['Rutledge Grainger (TN)']),
    ('Watertown Purple (TN)', ['Watertown (TN)']),
    ('Sparta (TN)', ['Sparta White County (TN)']),
    ('Murfreesboro Middle Tennessee (TN)', ['Murfreesboro Middle Tennessee Christian (TN)']),
    ('Athens J.L. Cook McMinn County (TN)', ['Athens McMinn County (TN)']),
    ('Crossville (TN)', ['Crossville Cumberland County (TN)']),
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
extra = ['Lafayette Macon County (TN)', 'Parsons-Riverside (TN)', 'Decatur County-Riverside (TN)',
         'Rutledge Grainger (TN)', 'Watertown (TN)', 'Sparta White County (TN)',
         'Murfreesboro Middle Tennessee Christian (TN)', 'Athens McMinn County (TN)',
         'Crossville Cumberland County (TN)']
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
