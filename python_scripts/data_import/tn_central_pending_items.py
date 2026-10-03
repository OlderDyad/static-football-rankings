import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=' * 70)
print('PART A: The 4 mismatched-date "duplicate" candidates -- is the existing')
print('  game vs the correct Central a real second meeting, or something else?')
print('=' * 70)

mismatched = [
    ('26023000-BBF8-47EC-94E1-00192EFC6662', 1949, 'Nashville Litton (TN)', 'Nashville Central (TN)', '1949-10-08', '1949-09-30'),
    ('E79633EC-6AF6-4377-AE93-B578EAFF3DA6', 1951, 'Nashville East (TN)', 'Nashville Central (TN)', '1951-11-10', '1951-10-20'),
    ('D16A0459-703B-40F8-AB02-AC30C2E6563D', 1953, 'Nashville Father Ryan (TN)', 'Nashville Central (TN)', '1953-09-12', '1953-08-28'),
    ('C9535E49-17CD-4299-B8AD-5860BB1F5777', 1955, 'Nashville Father Ryan (TN)', 'Nashville Central (TN)', '1955-09-10', '1955-09-02'),
]

for scores_id, season, opponent, central, flagged_date, existing_date in mismatched:
    print()
    print(f'--- {opponent} in {season} (flagged Knoxville Central row on {flagged_date}; existing {central} game on {existing_date}) ---')
    print(f'  Full {opponent} schedule this season:')
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores WHERE Season = ? AND (Home = ? OR Visitor = ?) ORDER BY Date
    """, season, opponent, opponent)
    for r in cur.fetchall():
        print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
    print(f'  Full {central} schedule this season:')
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores WHERE Season = ? AND (Home = ? OR Visitor = ?) ORDER BY Date
    """, season, central, central)
    for r in cur.fetchall():
        print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
    print(f'  Full Knoxville Central schedule this season (for context):')
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores WHERE Season = ? AND (Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)') ORDER BY Date
    """, season)
    for r in cur.fetchall():
        print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')

print()
print('=' * 70)
print('PART B: Columbia Central (TN) vs Knoxville Central (TN), 1943-10-16 --')
print('  is this a real matchup or a self-match error in our earlier script?')
print('=' * 70)
cur.execute("""
    SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
    FROM HS_Scores WHERE Season = 1943 AND (Home LIKE '%Columbia%' OR Visitor LIKE '%Columbia%') ORDER BY Date
""")
print('  All "Columbia"-named teams\' games in 1943:')
for r in cur.fetchall():
    print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
print('  Full Knoxville Central schedule, 1943 (for context):')
cur.execute("""
    SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
    FROM HS_Scores WHERE Season = 1943 AND (Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)') ORDER BY Date
""")
for r in cur.fetchall():
    print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')

print()
print('=' * 70)
print('PART C: The 5 unregistered rows -- full season context for each, plus')
print('  the exact column layout of an EXISTING investigation row (5513) so we')
print('  know the schema to replicate if we need to manually register new ones.')
print('=' * 70)
unregistered = [
    ('15C3E2D1-05AC-46DC-9956-D03D01A27677', 1926, 'Chattanooga Baylor (TN)'),
    ('25E5DB64-E28F-4B80-8F94-8B43F29FB97B', 1926, 'Nashville Montgomery Bell Academy (TN)'),
    ('C17182B5-D020-4EC6-8D13-D5488A476F25', 1942, 'Nashville Montgomery Bell Academy (TN)'),
    ('1D73CCF3-E72D-4BDA-A679-9ACBB7399483', 1969, 'Nashville Lipscomb Academy (TN)'),
    ('0FEED2A0-B4B9-4A27-9CCA-4612C124ECA9', 1970, 'Nashville Lipscomb Academy (TN)'),
    ('0E635739-A858-43B2-AB1B-FBDB30BEE62A', 1987, 'Kingsport Dobyns-Bennett (TN)'),
]
for scores_id, season, opponent in unregistered:
    print()
    print(f'--- {opponent} in {season}, full Knoxville Central schedule that season ---')
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores WHERE Season = ? AND (Home = 'Knoxville Central (TN)' OR Visitor = 'Knoxville Central (TN)') ORDER BY Date
    """, season)
    for r in cur.fetchall():
        print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')

print()
print('  Full column layout + values of an existing investigation (InvestigationID=5513) for schema reference:')
cur.execute("SELECT * FROM HS_Mapping_Investigations WHERE InvestigationID = 5513")
row = cur.fetchone()
cols = [d[0] for d in cur.description]
for c, v in zip(cols, row):
    print(f'    {c} = {v!r}')
