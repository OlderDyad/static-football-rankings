import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

a = 'Johnson City (TN)'
b = 'Johnson City Science Hill (TN)'

print('=== Season-by-season game counts, side by side ===')
cur.execute("""
    SELECT Season,
        SUM(CASE WHEN Home=? OR Visitor=? THEN 1 ELSE 0 END) AS A_games,
        SUM(CASE WHEN Home=? OR Visitor=? THEN 1 ELSE 0 END) AS B_games
    FROM HS_Scores
    WHERE Home IN (?, ?) OR Visitor IN (?, ?)
    GROUP BY Season
    ORDER BY Season
""", a, a, b, b, a, b, a, b)
for r in cur.fetchall():
    print(' ', r)

print()
print('=== Exact same-date collisions (both playing same date -- possible duplicate records) ===')
cur.execute("""
    SELECT s1.Season, s1.Date,
        s1.Home AS A_Home, s1.Visitor AS A_Visitor, s1.Home_Score AS A_HS, s1.Visitor_Score AS A_VS, s1.Source AS A_Source,
        s2.Home AS B_Home, s2.Visitor AS B_Visitor, s2.Home_Score AS B_HS, s2.Visitor_Score AS B_VS, s2.Source AS B_Source
    FROM HS_Scores s1
    JOIN HS_Scores s2
        ON s1.Date = s2.Date
       AND (s1.Home = ? OR s1.Visitor = ?)
       AND (s2.Home = ? OR s2.Visitor = ?)
    ORDER BY s1.Date
""", a, a, b, b)
rows = cur.fetchall()
print(f'  {len(rows)} same-date pairs found')
for r in rows[:15]:
    print('  ', r)
