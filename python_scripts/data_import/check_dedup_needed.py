import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Batch 33 status right now ===')
cur.execute("SELECT status FROM dbo.scraping_batches WHERE batch_id = 33")
print(f'  {cur.fetchone().status}')

print()
print('=== Exact (Date, Home, Visitor) duplicates among the new 2026 MaxPreps rows? ===')
cur.execute("""
    SELECT Date, Home, Visitor, COUNT(*) AS [RowCount]
    FROM dbo.HS_Scores
    WHERE Source LIKE '%maxpreps%' AND Season = 2026
    GROUP BY Date, Home, Visitor
    HAVING COUNT(*) > 1
""")
rows = cur.fetchall()
print(f'  Exact duplicate (Date,Home,Visitor) groups: {len(rows)}')
for r in rows[:10]:
    print(f'    {r.Date}  {r.Home} vs {r.Visitor}  x{r.RowCount}')

print()
print('=== Direction-reversed duplicates (same two teams same date, Home/Visitor swapped)? ===')
cur.execute("""
    SELECT a.Date, a.Home, a.Visitor, a.ID AS ID_A, b.ID AS ID_B
    FROM dbo.HS_Scores a
    JOIN dbo.HS_Scores b
      ON a.Date = b.Date AND a.Home = b.Visitor AND a.Visitor = b.Home AND a.ID <> b.ID
    WHERE a.Source LIKE '%maxpreps%' AND a.Season = 2026
      AND b.Source LIKE '%maxpreps%' AND b.Season = 2026
""")
rows = cur.fetchall()
print(f'  Direction-reversed duplicate pairs: {len(rows)}')
for r in rows[:10]:
    print(f'    {r.Date}  {r.Home} vs {r.Visitor}')

print()
print('=== Total 2026 MaxPreps HS_Scores rows vs. distinct (Date,Home,Visitor) combos ===')
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = 2026")
total = cur.fetchone().RowCount
cur.execute("""
    SELECT COUNT(*) AS [RowCount] FROM (
        SELECT DISTINCT Date, Home, Visitor FROM dbo.HS_Scores
        WHERE Source LIKE '%maxpreps%' AND Season = 2026
    ) x
""")
distinct = cur.fetchone().RowCount
print(f'  Total rows: {total}   Distinct (Date,Home,Visitor): {distinct}')

conn.close()
