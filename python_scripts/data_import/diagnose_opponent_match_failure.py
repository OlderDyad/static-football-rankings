import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== scraping_batches.season_slug for batch 33 (should be NULL for current-season) ===')
cur.execute("SELECT batch_id, batch_name, season_slug FROM dbo.scraping_batches WHERE batch_id = 33")
r = cur.fetchone()
print(f'  season_slug = {r.season_slug!r}')

print()
print('=== Sample raw opponent URLs actually scraped into games_raw for batch 33 ===')
cur.execute("SELECT TOP 10 opponent_name_raw, opponent_maxpreps_url FROM dbo.games_raw WHERE batch_id = 33")
raw_urls = []
for r in cur.fetchall():
    print(f'  {r.opponent_name_raw!r:50s} -> {r.opponent_maxpreps_url!r}')
    raw_urls.append(r.opponent_maxpreps_url)

print()
print('=== Sample URL_ProperName_Mapping.URL values (the format we are matching against) ===')
cur.execute("SELECT TOP 5 URL, ProperName FROM dbo.URL_ProperName_Mapping")
for r in cur.fetchall():
    print(f'  {r.URL!r}  ({r.ProperName})')

print()
print('=== Direct test: does any raw opponent URL from games_raw match URL_ProperName_Mapping.URL exactly? ===')
for u in raw_urls[:5]:
    cur.execute("SELECT ProperName FROM dbo.URL_ProperName_Mapping WHERE URL = ?", u)
    match = cur.fetchone()
    print(f'  {u!r}  ->  exact match: {match.ProperName if match else "NO MATCH"}')

print()
print('=== Also check primary_team_name matching (the OTHER side of the join) ===')
cur.execute("SELECT TOP 5 primary_team_name FROM dbo.games_raw WHERE batch_id = 33")
for r in cur.fetchall():
    cur.execute("SELECT ProperName FROM dbo.URL_ProperName_Mapping WHERE ProperName = ?", r.primary_team_name)
    match = cur.fetchone()
    print(f'  primary_team_name={r.primary_team_name!r}  ->  exact ProperName match: {"YES" if match else "NO MATCH"}')

conn.close()
