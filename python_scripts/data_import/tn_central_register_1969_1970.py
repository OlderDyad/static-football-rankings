import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

# These two seasons were never registered by `detect` (pre-2003, non-newspapers.com
# sources -- documented blind spot in the workflow guide). Both are now confirmed as
# score-matched duplicates: Nashville Central's own schedule already has the identical
# game (6-0 vs Lipscomb Academy same date in 1969; 12-6 vs Lipscomb Academy one week
# off in 1970), so the Knoxville Central version is the same game re-dated/mislabeled.
new_investigations = [
    (1969, 0, True, 'High - same game, wrong opponent name',
     'Manually registered: detect never ran on this row (pre-2003, non-newspapers.com source). '
     'Nashville Central already has an identical 6-0 game vs Nashville Lipscomb Academy on the same '
     'date (1969-10-03); this Knoxville Central row is a duplicate.'),
    (1970, 7, True, 'High - same game, wrong opponent name',
     'Manually registered: detect never ran on this row (pre-2003, non-newspapers.com source). '
     'Nashville Central already has an identical 12-6 game vs Nashville Lipscomb Academy one week '
     'later (1970-09-11 vs the flagged 1970-09-04); this Knoxville Central row is a duplicate.'),
]

scores_ids = {
    1969: '1D73CCF3-E72D-4BDA-A679-9ACBB7399483',
    1970: '0FEED2A0-B4B9-4A27-9CCA-4612C124ECA9',
}

print('Inserting 2 new investigations for Knoxville Central (TN) -- 1969 and 1970 --')
print('and printing the ready-to-run delete commands once each new InvestigationID is known.')
print()

for season, min_days, score_match, priority, notes in new_investigations:
    cur.execute("""
        INSERT INTO HS_Mapping_Investigations
            (AnchorTeam, State, Season, DateIdentified, Status, MinDaysApart,
             ScoreMatchFlag, Priority, ConflictType, Notes)
        OUTPUT INSERTED.InvestigationID
        VALUES
            ('Knoxville Central (TN)', '(TN)', ?, GETDATE(), 'New', ?, ?, ?, 'GhostTeam', ?)
    """, season, min_days, score_match, priority, notes)
    new_id = cur.fetchone()[0]
    conn.commit()
    print(f'  Season {season}: new InvestigationID = {new_id}')
    print(f'    Run this to delete the confirmed duplicate row:')
    print(f'    python mapping_conflict_audit.py delete --id {scores_ids[season]} --investigation {new_id} --reason "Duplicate confirmed via score-match against Nashville Central\'s own {season} schedule (see investigation Notes)"')
    print()
