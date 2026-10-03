import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Sample of the "exactly one fallback URL" bucket (487 total, should be easy backfills) ===')
cur.execute("""
    SELECT S.team_id, N.Team_Name, N.City, N.State,
           (SELECT MIN(T2.MaxPrepsURL) FROM dbo.HS_Team_MaxPreps T2 WHERE T2.Team_ID = S.team_id) AS MaxPrepsURL
    FROM dbo.team_scraping_status AS S
    LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
    JOIN dbo.HS_Team_Names AS N ON N.ID = S.team_id
    WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL
      AND (SELECT COUNT(DISTINCT T.MaxPrepsURL) FROM dbo.HS_Team_MaxPreps T WHERE T.Team_ID = S.team_id) = 1
    ORDER BY S.team_id
""")
rows = cur.fetchall()
print(f'  (showing first 20 of {len(rows)})')
for r in rows[:20]:
    print(f'  team_id={r.team_id}  {r.Team_Name} ({r.City}, {r.State})  ->  {r.MaxPrepsURL}')

print()
print('=== Sample of the "multiple/messy fallback URLs" bucket (6065 total, needs manual review) ===')
cur.execute("""
    SELECT TOP 5 S.team_id, N.Team_Name, N.City, N.State,
           (SELECT COUNT(DISTINCT T.MaxPrepsURL) FROM dbo.HS_Team_MaxPreps T WHERE T.Team_ID = S.team_id) AS URLCount
    FROM dbo.team_scraping_status AS S
    LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
    JOIN dbo.HS_Team_Names AS N ON N.ID = S.team_id
    WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL
      AND (SELECT COUNT(DISTINCT T.MaxPrepsURL) FROM dbo.HS_Team_MaxPreps T WHERE T.Team_ID = S.team_id) > 1
    ORDER BY URLCount DESC
""")
for r in cur.fetchall():
    print(f'  team_id={r.team_id}  {r.Team_Name} ({r.City}, {r.State})  -- {r.URLCount} distinct URLs on file')

conn.close()
