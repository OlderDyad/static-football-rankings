import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Any alias rule resolving a bare "Central" to Knoxville Central (TN)? ===')
cur.execute("""
    SELECT Alias_Name, Standardized_Name, Newspaper_Region, Newspaper_City, Newspaper_State
    FROM HS_Team_Name_Alias
    WHERE Standardized_Name = 'Knoxville Central (TN)'
    ORDER BY Newspaper_Region
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  {r.Alias_Name!r} -> {r.Standardized_Name!r}  (Region={r.Newspaper_Region}, City={r.Newspaper_City}, State={r.Newspaper_State})')
else:
    print('  None found -- Knoxville Central is not an alias-resolution target for anything.')

print()
print('=== All distinct "___ Central (TN)" team names in HS_Scores (to see how many real "Central" schools exist) ===')
cur.execute("""
    SELECT DISTINCT Home AS TeamName FROM HS_Scores WHERE Home LIKE '%Central (TN)%'
    UNION
    SELECT DISTINCT Visitor FROM HS_Scores WHERE Visitor LIKE '%Central (TN)%'
    ORDER BY TeamName
""")
for r in cur.fetchall():
    print(f'  {r.TeamName}')

print()
print('=== Raw Source filenames for the 20 flagged same-day Knoxville Central conflicts (checking if same CSV source repeats) ===')
cur.execute("""
    SELECT s.Date, s.Home, s.Visitor, s.Home_Score, s.Visitor_Score, s.Source
    FROM HS_Scores s
    WHERE (s.Home = 'Knoxville Central (TN)' OR s.Visitor = 'Knoxville Central (TN)')
    AND s.Date IN (
        SELECT s2.Date FROM HS_Scores s2
        WHERE (s2.Home = 'Knoxville Central (TN)' OR s2.Visitor = 'Knoxville Central (TN)')
        GROUP BY s2.Date HAVING COUNT(*) > 1
    )
    ORDER BY s.Date
""")
for r in cur.fetchall():
    print(f'  {r.Date}  {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}   [{r.Source}]')

print()
print('=== Check: does "Nashville Central (TN)" exist anywhere as its own team name? ===')
cur.execute("""
    SELECT COUNT(*) FROM HS_Scores WHERE Home = 'Nashville Central (TN)' OR Visitor = 'Nashville Central (TN)'
""")
print(f'  Nashville Central (TN) row count: {cur.fetchone()[0]}')

print()
print('=== Check games_raw for any raw scrapes mentioning "Central" near Knoxville Central rows (if still present) ===')
cur.execute("""
    SELECT TOP 20 raw_id, primary_team_name, opponent_name_raw, result_text, game_date, batch_id
    FROM games_raw
    WHERE primary_team_name LIKE '%Central%' OR opponent_name_raw LIKE '%Central%'
    ORDER BY raw_id
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  {r}')
else:
    print('  No matching games_raw rows found (may have been purged after import).')
