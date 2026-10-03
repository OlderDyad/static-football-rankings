import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== All "Johnson City Science Hill (TN)" vs "Bristol Tennessee (TN)" games, any date ===')
cur.execute("""
    SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
    FROM HS_Scores
    WHERE (Home = 'Johnson City Science Hill (TN)' AND Visitor = 'Bristol Tennessee (TN)')
       OR (Visitor = 'Johnson City Science Hill (TN)' AND Home = 'Bristol Tennessee (TN)')
    ORDER BY Date
""")
rows = cur.fetchall()
print(f'{len(rows)} total row(s)')
for r in rows:
    print(' ', r)

print()
print('=== Does hsfdatabase.com show ANY other TN team playing "Bristol Tennessee" on a date that duplicates a maxpreps game? ===')
cur.execute("""
    SELECT s1.Season, s1.Date, s1.Home AS RealHome, s1.Visitor AS RealVisitor, s1.Source AS RealSource,
           s2.Home AS BristolHome, s2.Visitor AS BristolVisitor, s2.Source AS BristolSource
    FROM HS_Scores s1
    JOIN HS_Scores s2
        ON s1.Date = s2.Date
       AND s1.Season = s2.Season
       AND (s2.Home = 'Bristol Tennessee (TN)' OR s2.Visitor = 'Bristol Tennessee (TN)')
       AND s1.Source LIKE '%maxpreps%'
       AND s2.Source LIKE '%hsfdatabase%'
       AND (s1.Home IN (s2.Home, s2.Visitor) OR s1.Visitor IN (s2.Home, s2.Visitor))
       AND s1.ID <> s2.ID
    ORDER BY s1.Date
""")
rows2 = cur.fetchall()
print(f'{len(rows2)} matching pattern row(s) across all of TN (not just Science Hill)')
for r in rows2[:30]:
    print(' ', r)
