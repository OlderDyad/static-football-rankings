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
    ('Knoxville Austin (TN)', ['Knoxville Austin-East (TN)', 'Knoxville Austin East (TN)', 'Austin East (TN)', 'Knoxville G.P. Austin (TN)', 'G.P. Austin (TN)']),
    ('Parsons (TN)', ['Parsons-Riverside (TN)']),
    ('Fayette County (TN)', ['Somerville Fayette County (TN)', 'Somerville Fayette Ware (TN)', 'Somerville Fayette Academy (TN)']),
    ('Jefferson City (TN)', ['Jefferson City Jefferson (TN)', 'Jefferson City Nelson Merry (TN)', 'Jefferson City Negro (TN)']),
    ('Nashville Duncan College Prep (TN)', ['Duncan (TN)', 'Duncan School (TN)', 'Nashville Duncan (TN)', 'Nashville Duncan College Prep Alumni (TN)']),
    ('McMinnville City Warren County (TN)', ['McMinnville Warren County (TN)', 'McMinnville Central Warren County (TN)', 'McMinnville Central (TN)', 'McMinnville(TN)', 'McMinnville City (TN)']),
    ('Decaturville (TN)', ['Decaturville Riverside (TN)']),
    ('Petersburg Lincoln County (TN)', ['Petersburg (TN)', 'Petersburg Morgan School (TN)', 'Petersburg Morgan School for Boys (TN)']),
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
extra = ['Knoxville Austin-East (TN)', 'Knoxville G.P. Austin (TN)', 'Parsons-Riverside (TN)',
         'Somerville Fayette County (TN)', 'Jefferson City Jefferson (TN)', 'Jefferson City Negro (TN)',
         'Duncan (TN)', 'Duncan School (TN)', 'Nashville Duncan (TN)',
         'McMinnville Central Warren County (TN)', 'McMinnville City (TN)',
         'Decaturville Riverside (TN)', 'Petersburg (TN)', 'Petersburg Morgan School (TN)']
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
