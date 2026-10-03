"""
Verifies that batch 34's permanently-pending team_ids are the SAME known
duplicate-team-record set identified in batch 33 (task #52), not new/different
failures worth investigating separately.

A team_id is "permanently pending" if it has a pending team_scraping_status
row for this batch but no row in URL_ProperName_Mapping -- get_urls_to_process()
INNER JOINs against that table, so such a team_id can never be selected for
scraping no matter how many times the batch runs.

Read-only. Prints a summary; does not modify any data.
"""
import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

BATCH_ID = 34

print(f'=== Batch {BATCH_ID}: pending team_ids with no URL_ProperName_Mapping entry ===')
cur.execute("""
    SELECT DISTINCT S.team_id
    FROM dbo.team_scraping_status AS S
    LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
    WHERE S.batch_id = ? AND S.status = 'pending' AND M.Team_ID IS NULL
""", BATCH_ID)
batch34_stuck = set(r.team_id for r in cur.fetchall())
print(f'  Batch 34 stuck (unjoinable) distinct team_ids: {len(batch34_stuck)}')

print()
print('=== Same check against batch 33 (already diagnosed/documented) ===')
cur.execute("""
    SELECT DISTINCT S.team_id
    FROM dbo.team_scraping_status AS S
    LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
    WHERE S.batch_id = 33 AND S.status = 'pending' AND M.Team_ID IS NULL
""")
batch33_stuck = set(r.team_id for r in cur.fetchall())
print(f'  Batch 33 stuck (unjoinable) distinct team_ids: {len(batch33_stuck)}')

print()
only_in_34 = batch34_stuck - batch33_stuck
only_in_33 = batch33_stuck - batch34_stuck
both = batch34_stuck & batch33_stuck
print(f'  In both batch 33 and batch 34: {len(both)}')
print(f'  Only in batch 34 (NEW -- not previously seen): {len(only_in_34)}')
print(f'  Only in batch 33 (no longer stuck in batch 34 -- got mapped since): {len(only_in_33)}')

if only_in_34:
    print()
    print(f'  First 20 NEW stuck team_ids worth a look:')
    cur.execute(f"""
        SELECT TOP 20 Team_ID, Team_Name, State
        FROM dbo.HS_Team_Names
        WHERE Team_ID IN ({','.join(str(t) for t in list(only_in_34)[:20])})
    """)
    for r in cur.fetchall():
        print(f'    {r.Team_ID}: {r.Team_Name} ({r.State})')

conn.close()
