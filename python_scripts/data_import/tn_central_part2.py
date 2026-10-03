import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=' * 70)
print('PART D: Re-examine the 4 mismatched-date duplicates using SCORE-MATCH')
print('  instead of date-match (same method the tool itself uses --')
print('  ScoreMatchFlag / "same game, wrong opponent name" -- for the flagged')
print('  Knoxville Central row, does an identical score appear against the')
print('  correct Central team ANYWHERE that season, even off-date?)')
print('=' * 70)

cases = [
    ('26023000-BBF8-47EC-94E1-00192EFC6662', 1949, 'Nashville Litton (TN)', 21, 0),
    ('E79633EC-6AF6-4377-AE93-B578EAFF3DA6', 1951, 'Nashville East (TN)', 12, 0),
    ('D16A0459-703B-40F8-AB02-AC30C2E6563D', 1953, 'Nashville Father Ryan (TN)', 13, 7),
    ('C9535E49-17CD-4299-B8AD-5860BB1F5777', 1955, 'Nashville Father Ryan (TN)', 33, 0),
]
for scores_id, season, opponent, s1, s2 in cases:
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores
        WHERE Season = ? AND ((Home = ? AND Home_Score = ? AND Visitor_Score = ?)
                            OR (Home = ? AND Home_Score = ? AND Visitor_Score = ?))
        ORDER BY Date
    """, season, opponent, s1, s2, opponent, s2, s1)
    print(f'  {opponent} {season}, score {s1}-{s2} (or {s2}-{s1}) games this season:')
    for r in cur.fetchall():
        print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')

print()
print('=' * 70)
print('PART E: For the 1951 Nashville East anomaly (no score match found) --')
print('  look for a plausible OCR-garbled score near 12-0 in Nashville East or')
print('  Nashville Central 1951 games, and check whether any OTHER team named')
print('  something Central-like fits instead.')
print('=' * 70)
cur.execute("""
    SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
    FROM HS_Scores
    WHERE Season = 1951 AND (Home = 'Nashville East (TN)' OR Visitor = 'Nashville East (TN)')
    ORDER BY Date
""")
print('  Full Nashville East 1951 schedule (for OCR/score-typo scan):')
for r in cur.fetchall():
    print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')

print()
print('=' * 70)
print('PART F: For the 5 unregistered rows, pull the CORRECTION-TARGET schedule')
print('  (not just Knoxville Central\'s) to finish the relabel-vs-duplicate test.')
print('=' * 70)
targets = [
    (1926, 'Chattanooga Central (TN)', 'Chattanooga Baylor (TN) row: Knoxville Central 12-0 Chattanooga Baylor'),
    (1926, 'Nashville Central (TN)', 'Nashville MBA row: Nashville MBA 35-0 Knoxville Central'),
    (1942, 'Nashville Central (TN)', 'Nashville MBA row: Knoxville Central 12-6 Nashville MBA'),
    (1969, 'Nashville Central (TN)', 'Lipscomb Academy row: Knoxville Central 6-0 Nashville Lipscomb Academy'),
    (1970, 'Nashville Central (TN)', 'Lipscomb Academy row: Knoxville Central 12-6 Nashville Lipscomb Academy'),
    (1987, 'Kingsport Central (TN)', 'Dobyns-Bennett row: Knoxville Central 20-14 Kingsport Dobyns-Bennett'),
]
for season, target, desc in targets:
    print()
    print(f'--- {season}: {desc} -- full {target} schedule ---')
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores WHERE Season = ? AND (Home = ? OR Visitor = ?) ORDER BY Date
    """, season, target, target)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f'    {r.Date}: {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
    else:
        print(f'    No games found for {target} in {season} at all.')

print()
print('=' * 70)
print('PART G: Check if InvestigationID is an IDENTITY column (auto-assigned) --')
print('  needed to know whether we can manually INSERT specific new rows for')
print('  the 5 unregistered seasons, or must omit the ID and let SQL assign one.')
print('=' * 70)
cur.execute("""
    SELECT COLUMNPROPERTY(OBJECT_ID('HS_Mapping_Investigations'), 'InvestigationID', 'IsIdentity') AS IsIdentity
""")
print(f'  IsIdentity(InvestigationID) = {cur.fetchone()[0]}  (1 = auto-assigned, 0/None = must specify)')
