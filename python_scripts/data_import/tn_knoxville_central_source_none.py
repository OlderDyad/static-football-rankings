import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Overall counts: Knoxville Central rows by Source-is-null vs not ===')
cur.execute("""
    SELECT
        CASE WHEN Source IS NULL THEN 'NULL' ELSE 'has source' END AS SourceBucket,
        COUNT(*) AS [RowCount],
        MIN(Season) AS MinSeason,
        MAX(Season) AS MaxSeason
    FROM HS_Scores
    WHERE Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)'
    GROUP BY CASE WHEN Source IS NULL THEN 'NULL' ELSE 'has source' END
""")
for r in cur.fetchall():
    print(f'  {r.SourceBucket}: {r.RowCount} rows, seasons {r.MinSeason}-{r.MaxSeason}')

print()
print('=== Future_Game flag on the Source=NULL rows ===')
cur.execute("""
    SELECT Future_Game, COUNT(*) AS [RowCount]
    FROM HS_Scores
    WHERE (Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)')
      AND Source IS NULL
    GROUP BY Future_Game
""")
for r in cur.fetchall():
    print(f'  Future_Game={r.Future_Game}: {r.RowCount} rows')

print()
print('=== BatchID and Date_Added distribution for Source=NULL Knoxville Central rows ===')
cur.execute("""
    SELECT BatchID, CAST(Date_Added AS DATE) AS AddedDate, COUNT(*) AS [RowCount]
    FROM HS_Scores
    WHERE (Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)')
      AND Source IS NULL
    GROUP BY BatchID, CAST(Date_Added AS DATE)
    ORDER BY AddedDate
""")
for r in cur.fetchall():
    print(f'  BatchID={r.BatchID}  AddedDate={r.AddedDate}  Count={r.RowCount}')

print()
print('=== Same check for Date_Added on the has-source rows, for comparison ===')
cur.execute("""
    SELECT CAST(Date_Added AS DATE) AS AddedDate, COUNT(*) AS [RowCount]
    FROM HS_Scores
    WHERE (Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)')
      AND Source IS NOT NULL
    GROUP BY CAST(Date_Added AS DATE)
    ORDER BY AddedDate
""")
for r in cur.fetchall():
    print(f'  AddedDate={r.AddedDate}  Count={r.RowCount}')

print()
print('=== Sample of 10 Source=NULL rows with full detail ===')
cur.execute("""
    SELECT TOP 10 ID, Date, Season, Home, Visitor, Home_Score, Visitor_Score, BatchID, Date_Added, Future_Game, Access_ID
    FROM HS_Scores
    WHERE (Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)')
      AND Source IS NULL
    ORDER BY Date
""")
for r in cur.fetchall():
    print(f'  {r}')

print()
print('=== Does the SAME pattern (Source=NULL shadow rows) appear for OTHER Knoxville teams, or is it unique to Central? ===')
cur.execute("""
    SELECT
        CASE
            WHEN Home LIKE 'Knoxville %' THEN Home
            WHEN Visitor LIKE 'Knoxville %' THEN Visitor
        END AS TeamName,
        COUNT(*) AS NullSourceCount
    FROM HS_Scores
    WHERE Source IS NULL
      AND (Home LIKE 'Knoxville %' OR Visitor LIKE 'Knoxville %')
    GROUP BY CASE
            WHEN Home LIKE 'Knoxville %' THEN Home
            WHEN Visitor LIKE 'Knoxville %' THEN Visitor
        END
    ORDER BY NullSourceCount DESC
""")
for r in cur.fetchall():
    print(f'  {r.TeamName}: {r.NullSourceCount} null-source rows')
