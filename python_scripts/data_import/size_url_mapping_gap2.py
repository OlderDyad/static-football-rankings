import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== How many pending/failed team_scraping_status rows point at team_id=66369? ===')
cur.execute("""
    SELECT COUNT(*) AS [RowCount]
    FROM dbo.team_scraping_status
    WHERE batch_id = 33 AND status IN ('pending','failed') AND team_id = 66369
""")
print(f'  {cur.fetchone().RowCount} row(s) in team_scraping_status for team_id=66369')

print()
print('=== Duplicate team_id rows in team_scraping_status for batch 33 (pending/failed) -- sentinel-ID smell test ===')
cur.execute("""
    SELECT team_id, COUNT(*) AS [RowCount]
    FROM dbo.team_scraping_status
    WHERE batch_id = 33 AND status IN ('pending','failed')
    GROUP BY team_id
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
""")
rows = cur.fetchall()
print(f'  {len(rows)} team_id(s) with duplicate rows')
for r in rows[:10]:
    print(f'    team_id={r.team_id}: {r.RowCount} rows')

print()
print('=== URLs shared across MANY different team_ids in HS_Team_MaxPreps -- "non-varsity/catch-all URL" smell test ===')
cur.execute("""
    SELECT TOP 15 MaxPrepsURL, COUNT(DISTINCT Team_ID) AS DistinctTeamIds
    FROM dbo.HS_Team_MaxPreps
    GROUP BY MaxPrepsURL
    HAVING COUNT(DISTINCT Team_ID) > 1
    ORDER BY COUNT(DISTINCT Team_ID) DESC
""")
rows = cur.fetchall()
for r in rows:
    print(f'  {r.DistinctTeamIds} team_ids share -> {r.MaxPrepsURL}')

print()
print('=== Does HS_Team_MaxPreps have Season data we can use to pick the most-recent URL? ===')
cur.execute("""
    SELECT Team_ID, MaxPrepsURL, Season
    FROM dbo.HS_Team_MaxPreps
    WHERE Team_ID IN (194, 198, 109)
    ORDER BY Team_ID, Season DESC
""")
for r in cur.fetchall():
    print(f'  team_id={r.Team_ID}  season={r.Season}  {r.MaxPrepsURL}')

print()
print('=== Test the 95% hypothesis: excl. sentinel/dup team_ids AND catch-all URLs shared by >1 team_id, taking only most-recent season ===')
cur.execute("""
    WITH BadUrls AS (
        SELECT MaxPrepsURL
        FROM dbo.HS_Team_MaxPreps
        GROUP BY MaxPrepsURL
        HAVING COUNT(DISTINCT Team_ID) > 1
    ),
    GapTeams AS (
        SELECT DISTINCT S.team_id
        FROM dbo.team_scraping_status AS S
        LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
        WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL
          AND (SELECT COUNT(*) FROM dbo.team_scraping_status S2 WHERE S2.batch_id = 33 AND S2.status IN ('pending','failed') AND S2.team_id = S.team_id) = 1
    ),
    CleanMaxPreps AS (
        SELECT T.Team_ID, T.MaxPrepsURL, T.Season
        FROM dbo.HS_Team_MaxPreps T
        WHERE NOT EXISTS (SELECT 1 FROM BadUrls B WHERE B.MaxPrepsURL = T.MaxPrepsURL)
    ),
    MaxSeason AS (
        SELECT G.team_id, MAX(C.Season) AS TopSeason
        FROM GapTeams G
        JOIN CleanMaxPreps C ON C.Team_ID = G.team_id
        GROUP BY G.team_id
    ),
    UrlsAtTopSeason AS (
        SELECT MS.team_id, MS.TopSeason, COUNT(DISTINCT C.MaxPrepsURL) AS UrlCountAtTopSeason
        FROM MaxSeason MS
        JOIN CleanMaxPreps C ON C.Team_ID = MS.team_id AND C.Season = MS.TopSeason
        GROUP BY MS.team_id, MS.TopSeason
    )
    SELECT
        COUNT(*) AS TotalWithAnyCleanUrl,
        SUM(CASE WHEN UrlCountAtTopSeason = 1 THEN 1 ELSE 0 END) AS SingleCleanUrlAtMostRecentSeason,
        SUM(CASE WHEN UrlCountAtTopSeason > 1 THEN 1 ELSE 0 END) AS StillAmbiguousAtMostRecentSeason
    FROM UrlsAtTopSeason
""")
row = cur.fetchone()
print(f'  Gap teams with at least one non-catch-all URL on file: {row.TotalWithAnyCleanUrl}')
print(f'  -> single clean URL at their most recent season:      {row.SingleCleanUrlAtMostRecentSeason}')
print(f'  -> still ambiguous even at most recent season:        {row.StillAmbiguousAtMostRecentSeason}')

print()
print('=== Sample: Team_Name alongside the picked (most-recent-season, non-catch-all) URL -- eyeball name consistency ===')
cur.execute("""
    WITH BadUrls AS (
        SELECT MaxPrepsURL
        FROM dbo.HS_Team_MaxPreps
        GROUP BY MaxPrepsURL
        HAVING COUNT(DISTINCT Team_ID) > 1
    ),
    GapTeams AS (
        SELECT DISTINCT S.team_id
        FROM dbo.team_scraping_status AS S
        LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
        WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL
          AND (SELECT COUNT(*) FROM dbo.team_scraping_status S2 WHERE S2.batch_id = 33 AND S2.status IN ('pending','failed') AND S2.team_id = S.team_id) = 1
    ),
    CleanMaxPreps AS (
        SELECT T.Team_ID, T.MaxPrepsURL, T.Season
        FROM dbo.HS_Team_MaxPreps T
        WHERE NOT EXISTS (SELECT 1 FROM BadUrls B WHERE B.MaxPrepsURL = T.MaxPrepsURL)
    ),
    MaxSeason AS (
        SELECT G.team_id, MAX(C.Season) AS TopSeason
        FROM GapTeams G
        JOIN CleanMaxPreps C ON C.Team_ID = G.team_id
        GROUP BY G.team_id
    )
    SELECT TOP 20 N.Team_Name, N.City, N.State, C.MaxPrepsURL, MS.TopSeason
    FROM MaxSeason MS
    JOIN CleanMaxPreps C ON C.Team_ID = MS.team_id AND C.Season = MS.TopSeason
    JOIN dbo.HS_Team_Names N ON N.ID = MS.team_id
    WHERE (SELECT COUNT(DISTINCT C2.MaxPrepsURL) FROM CleanMaxPreps C2 WHERE C2.Team_ID = MS.team_id AND C2.Season = MS.TopSeason) = 1
    ORDER BY N.Team_Name
""")
for r in cur.fetchall():
    print(f'  [{r.TopSeason}] {r.Team_Name} ({r.City}, {r.State})  ->  {r.MaxPrepsURL}')

conn.close()
