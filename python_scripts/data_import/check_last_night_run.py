import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Most recent batches ===')
cur.execute("""
    SELECT TOP 3 batch_id, batch_name, status, created_date, total_teams
    FROM dbo.scraping_batches
    WHERE batch_name LIKE 'MaxPreps Scrape - %'
    ORDER BY batch_id DESC
""")
rows = cur.fetchall()
for r in rows:
    print(f'  batch_id={r.batch_id}  status={r.status}  created={r.created_date}  total_teams={r.total_teams}')
latest_batch = rows[0].batch_id

print()
print(f'=== team_scraping_status for batch {latest_batch} ===')
cur.execute("SELECT status, COUNT(*) AS [RowCount] FROM dbo.team_scraping_status WHERE batch_id = ? GROUP BY status", latest_batch)
for r in cur.fetchall():
    print(f'  {r.status}: {r.RowCount}')

print()
print(f'=== games_raw rows for batch {latest_batch} (scraped, whether finalized or not) ===')
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.games_raw WHERE batch_id = ?", latest_batch)
print(f'  {cur.fetchone().RowCount}')

print()
print('=== 2026 MaxPreps HS_Scores rows added in the last 24 hours (did finalize actually run?) ===')
cur.execute("""
    SELECT COUNT(*) AS [RowCount], MAX(Date_Added) AS MostRecent
    FROM dbo.HS_Scores
    WHERE Source LIKE '%maxpreps%' AND Season = 2026 AND Date_Added >= DATEADD(hour, -24, GETDATE())
""")
r = cur.fetchone()
print(f'  New rows in last 24h: {r.RowCount}   Most recent Date_Added: {r.MostRecent}')

conn.close()
