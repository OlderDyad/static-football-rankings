import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== All "Blountville (TN)" games (full list) ===')
cur.execute("""
    SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE Home = 'Blountville (TN)' OR Visitor = 'Blountville (TN)'
    ORDER BY Season, Date
""")
rows = cur.fetchall()
print(f'{len(rows)} games')
for r in rows:
    print(' ', r)

print()
print('=== "Blountville Sullivan Central (TN)" games in the same years Blountville (TN) was active (1932-1967) ===')
cur.execute("""
    SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE (Home = 'Blountville Sullivan Central (TN)' OR Visitor = 'Blountville Sullivan Central (TN)')
      AND Season BETWEEN 1932 AND 1967
    ORDER BY Season, Date
""")
rows2 = cur.fetchall()
print(f'{len(rows2)} games')
for r in rows2:
    print(' ', r)

print()
print('=== Check for identical-date/score games between the two names (literal duplicates) ===')
cur.execute("""
    SELECT a.Season, a.Date, a.Home AS Home_A, a.Home_Score, a.Visitor AS Visitor_A, a.Visitor_Score,
           b.Home AS Home_B, b.Visitor AS Visitor_B, b.Source
    FROM HS_Scores a
    JOIN HS_Scores b
      ON a.Season = b.Season AND a.Date = b.Date
     AND a.Home_Score = b.Home_Score AND a.Visitor_Score = b.Visitor_Score
    WHERE (a.Home = 'Blountville (TN)' OR a.Visitor = 'Blountville (TN)')
      AND (b.Home = 'Blountville Sullivan Central (TN)' OR b.Visitor = 'Blountville Sullivan Central (TN)')
      AND a.Home != b.Home
""")
for r in cur.fetchall():
    print(' ', r)
