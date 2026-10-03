import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Batch 33 status ===')
cur.execute("SELECT batch_id, batch_name, status, created_date, total_teams FROM dbo.scraping_batches WHERE batch_id = 33")
r = cur.fetchone()
print(f'  status={r.status}  total_teams={r.total_teams}  created={r.created_date}')

print()
print('=== team_scraping_status breakdown for batch 33 ===')
cur.execute("SELECT status, COUNT(*) AS [RowCount] FROM dbo.team_scraping_status WHERE batch_id = 33 GROUP BY status")
for row in cur.fetchall():
    print(f'  {row.status}: {row.RowCount}')

print()
print('=== Is there a newer batch (Sunday sweep since)? ===')
cur.execute("SELECT TOP 5 batch_id, batch_name, status, created_date, total_teams FROM dbo.scraping_batches WHERE batch_name LIKE 'MaxPreps Scrape - %' ORDER BY batch_id DESC")
for row in cur.fetchall():
    print(f'  batch_id={row.batch_id}  status={row.status}  created={row.created_date}  total_teams={row.total_teams}')

print()
print('=== Did FinalizeMaxPrepsData run for batch 33? (check HS_Scores for recent MaxPreps rows) ===')
cur.execute("""
    SELECT COUNT(*) AS [RowCount], MAX(Date) AS MostRecentGameDate
    FROM dbo.HS_Scores
    WHERE Source LIKE '%maxpreps%' AND Season = 2026
""")
r = cur.fetchone()
print(f'  2026 MaxPreps-sourced HS_Scores rows: {r.RowCount}, most recent game date: {r.MostRecentGameDate}')

conn.close()
