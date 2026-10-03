import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

# (phantom_opponent, season, correct_local_central, the flagged HS_Scores row's ScoresID)
checks = [
    ('Nashville West (TN)', 1943, 'Nashville Central (TN)'),
    ('Nashville West (TN)', 1946, 'Nashville Central (TN)'),
    ('Memphis Southside (TN)', 1946, 'Memphis Central (TN)'),
    ('Spring City (TN)', 1946, 'Knoxville Central (TN)'),  # no obvious same-city Central; listed for contrast
]

for opponent, season, local_central in checks:
    print('=' * 70)
    print(f'{opponent} in {season} -- checking against {local_central}')
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores
        WHERE Season = ?
          AND ((Home = ? AND Visitor = ?) OR (Home = ? AND Visitor = ?))
    """, season, opponent, local_central, local_central, opponent)
    rows = cur.fetchall()
    if rows:
        print(f'  Already has a logged game vs {local_central} this season:')
        for r in rows:
            print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
    else:
        print(f'  No existing game vs {local_central} found this season -- relabel candidate, not a duplicate')

    print(f'  All of {opponent}\'s games in {season} (for context):')
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores
        WHERE Season = ? AND (Home = ? OR Visitor = ?)
        ORDER BY Date
    """, season, opponent, opponent)
    for r in cur.fetchall():
        print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')

print()
print('=== Does "Spring City (TN)" have its own "Central"-named rival anywhere in TN? (context check) ===')
cur.execute("""
    SELECT DISTINCT Home AS TeamName FROM HS_Scores WHERE Home LIKE '%Spring City%'
    UNION SELECT DISTINCT Visitor FROM HS_Scores WHERE Visitor LIKE '%Spring City%'
""")
for r in cur.fetchall():
    print(f'  {r.TeamName}')
