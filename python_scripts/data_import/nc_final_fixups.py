"""
Three small fixes from the NC-paper review, plus a READ-ONLY check of the quarantine table.

  1959-10-10  Mount Pleasant (NC) 21-13 Hartsville (SC)   -> Concord Hartsell (NC)
  1959-10-17  Marion (NC) 20-0 Hartsville (SC)            -> Concord Hartsell (NC)
  1937-10-23  Greenville (SC) 551-0 Anderson (SC)         -> 55-0  (OCR read the colon in "55:" as a 1)

Shows exactly what it will change, then asks you to type COMMIT. Anything else = nothing changes.

  python nc_final_fixups.py
"""
import pyodbc, sys
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;', autocommit=False)
cur = conn.cursor()

# ---------------- READ-ONLY: how does the quarantine table behave after a release? ----------------
print('=' * 90 + '\nQUARANTINE TABLE CHECK (read-only)\n' + '=' * 90)
cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'HS_Scores_Under_Review' ORDER BY ORDINAL_POSITION")
print('  Columns:', [r[0] for r in cur.fetchall()])
cur.execute("SELECT COUNT(*) FROM HS_Scores_Under_Review"); total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM HS_Scores_Under_Review u WHERE EXISTS (SELECT 1 FROM HS_Scores s WHERE s.ID = u.ID)"); both = cur.fetchone()[0]
print(f'  Rows in HS_Scores_Under_Review: {total}')
print(f'  ...of those ALSO back in HS_Scores (released but still listed): {both}')
if both:
    print('  -> Released games stay in the review table. Your old Step 2 (DELETE ... WHERE ID IN (SELECT ID FROM HS_Scores_Under_Review))')
    print('     would delete these released games from HS_Scores again. The new version must only delete rows moved in the same run.')
else:
    print('  -> No overlap right now (released games are removed from the review table, or nothing has been released yet).')

# ---------------- PREVIEW of the three fixes ----------------
print('\n' + '=' * 90 + '\nFIXES TO APPLY\n' + '=' * 90)
cur.execute("SELECT is_computed FROM sys.columns WHERE object_id = OBJECT_ID('HS_Scores') AND name = 'Margin'")
r = cur.fetchone(); margin_is_plain = bool(r) and not r[0]

fixes = []
cur.execute("""SELECT ID, Date, Home, Home_Score, Visitor, Visitor_Score FROM HS_Scores
               WHERE Visitor = 'Hartsville (SC)' AND ((Date = '1959-10-10' AND Home = 'Mount Pleasant (NC)')
                                                   OR (Date = '1959-10-17' AND Home = 'Marion (NC)'))""")
for g in cur.fetchall():
    fixes.append(('team', g.ID)); print(f'  {g.Date} {g.Home} {g.Home_Score}-{g.Visitor_Score} {g.Visitor}   ->  Visitor = Concord Hartsell (NC)')
cur.execute("""SELECT ID, Date, Home, Home_Score, Visitor, Visitor_Score FROM HS_Scores
               WHERE Date = '1937-10-23' AND Home = 'Greenville (SC)' AND Visitor = 'Anderson (SC)' AND Home_Score = 551""")
for g in cur.fetchall():
    fixes.append(('score', g.ID)); print(f'  {g.Date} {g.Home} {g.Home_Score}-{g.Visitor_Score} {g.Visitor}   ->  Home_Score = 55' + ('  (+ Margin recalculated)' if margin_is_plain else ''))
print(f'\n  {len(fixes)} row(s) found (expected 3).')
if len(fixes) != 3:
    print('  Not exactly 3 - stopping so nothing unexpected changes. Paste this output back.'); sys.exit()

if input('\nType COMMIT to apply: ').strip() != 'COMMIT':
    print('Nothing changed.'); sys.exit()
for kind, gid in fixes:
    if kind == 'team':
        cur.execute("UPDATE HS_Scores SET Visitor = 'Concord Hartsell (NC)' WHERE ID = ? AND Visitor = 'Hartsville (SC)'", gid)
    else:
        sql = "UPDATE HS_Scores SET Home_Score = 55" + (", Margin = 55 - Visitor_Score" if margin_is_plain else "") + " WHERE ID = ? AND Home_Score = 551"
        cur.execute(sql, gid)
    if cur.rowcount != 1:
        conn.rollback(); print(f'ROLLED BACK - row {gid} did not update cleanly. Nothing changed.'); sys.exit()
cur.execute("SELECT COUNT(*) FROM HS_Scores WHERE Home_Score = 551 AND Date = '1937-10-23'"); left = cur.fetchone()[0]
cur.execute("""SELECT COUNT(*) FROM HS_Scores WHERE Visitor = 'Hartsville (SC)' AND ((Date='1959-10-10' AND Home='Mount Pleasant (NC)') OR (Date='1959-10-17' AND Home='Marion (NC)'))"""); left += cur.fetchone()[0]
if left:
    conn.rollback(); print('ROLLED BACK - verification failed. Nothing changed.')
else:
    conn.commit(); print('COMMITTED: 2 games refiled to Concord Hartsell (NC), 1937 Greenville-Anderson corrected to 55-0. Verification: 0 rows left.')
