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
    ('Petersburg Morgan School (TN)', ['Petersburg Morgan School for Boys (TN)']),
    ('Tennessee Military Institute (TN)', ['Sweetwater Tennessee Military Institute (TN)', 'Knoxville Military Institute (TN)', 'Military Institute (TN)']),
    ('Chattanooga High (TN)', ['City High Chattanooga (TN)', 'ChattanoogaCity (TN)', 'Chattanooga Central (TN)']),
    ('Newbern (TN)', ['Newbern Dyer County (TN)']),
    ('Kingsport Tri-Cities Christian (TN)', ['Blountville Tri-Cities Christian (TN)']),
    ('Homesteads (TN)', ['Crossville Cumberland Homesteads (TN)']),
    ('Martin (TN)', ['Martin Westview (TN)']),
    ('Chattanooga (TN)', ['Chattanooga High (TN)', 'ChattanoogaCity (TN)', 'City High Chattanooga (TN)']),
    ('Sewanee (TN)', ['Sewanee Military Academy (TN)', 'Sewanee University of the South (TN)', 'Sewanee Academy (TN)', 'Sewanee Grammar (TN)']),
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
extra = ['Petersburg Morgan School for Boys (TN)', 'Sweetwater Tennessee Military Institute (TN)',
         'Knoxville Military Institute (TN)', 'Military Institute (TN)', 'City High Chattanooga (TN)',
         'ChattanoogaCity (TN)', 'Chattanooga Central (TN)', 'Newbern Dyer County (TN)',
         'Blountville Tri-Cities Christian (TN)', 'Crossville Cumberland Homesteads (TN)',
         'Martin Westview (TN)', 'Sewanee Military Academy (TN)', 'Sewanee University of the South (TN)']
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
