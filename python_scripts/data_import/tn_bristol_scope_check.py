import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== All hsfdatabase.com rows involving "Bristol Tennessee (TN)", by season ===')
cur.execute("""
    SELECT Season, COUNT(*) AS GameCount,
           MIN(Date) AS FirstDate, MAX(Date) AS LastDate
    FROM HS_Scores
    WHERE (Home = 'Bristol Tennessee (TN)' OR Visitor = 'Bristol Tennessee (TN)')
      AND Source LIKE '%hsfdatabase%'
    GROUP BY Season
    ORDER BY Season
""")
for r in cur.fetchall():
    print(' ', r)

print()
print('=== Same, but for ALL sources (not just hsfdatabase) -- comparison ===')
cur.execute("""
    SELECT Season, COUNT(*) AS GameCount
    FROM HS_Scores
    WHERE (Home = 'Bristol Tennessee (TN)' OR Visitor = 'Bristol Tennessee (TN)')
    GROUP BY Season
    ORDER BY Season
""")
for r in cur.fetchall():
    print(' ', r)

print()
print('=== Full detail for the worst season (most hsfdatabase Bristol Tennessee rows) ===')
cur.execute("""
    SELECT TOP 1 Season, COUNT(*) AS Cnt
    FROM HS_Scores
    WHERE (Home = 'Bristol Tennessee (TN)' OR Visitor = 'Bristol Tennessee (TN)')
      AND Source LIKE '%hsfdatabase%'
    GROUP BY Season
    ORDER BY COUNT(*) DESC
""")
worst_season = cur.fetchone()[0]
print(f'Worst season: {worst_season}')
cur.execute("""
    SELECT Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE (Home = 'Bristol Tennessee (TN)' OR Visitor = 'Bristol Tennessee (TN)')
      AND Source LIKE '%hsfdatabase%'
      AND Season = ?
    ORDER BY Date
""", worst_season)
for r in cur.fetchall():
    print(' ', r)

print()
print('=== Does the REAL Bristol Tennessee (any source) have a sane ~10-game season in that worst year? ===')
cur.execute("""
    SELECT Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE (Home = 'Bristol Tennessee (TN)' OR Visitor = 'Bristol Tennessee (TN)')
      AND Season = ?
    ORDER BY Date
""", worst_season)
for r in cur.fetchall():
    print(' ', r)
