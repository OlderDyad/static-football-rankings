import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Step 1: verify the dedup-guard patch actually landed ===')
cur.execute("""
    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Unmatched_Opponents' AND COLUMN_NAME = 'RawGameID'
""")
has_col = cur.fetchone() is not None
print(f'  Unmatched_Opponents.RawGameID exists: {has_col}')

cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.FinalizeMaxPrepsData'))")
definition = cur.fetchone()[0]
has_guard = "NOT EXISTS (SELECT 1 FROM dbo.Unmatched_Opponents uo WHERE uo.RawGameID" in definition
print(f'  Procedure has the new NOT EXISTS guard: {has_guard}')

if not (has_col and has_guard):
    print()
    print('  PATCH NOT FULLY APPLIED -- stopping here. Re-run apply_finalize_dedup_guard.py --commit first.')
    conn.close()
    raise SystemExit(1)

print()
print('=== Step 2: before counts ===')
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = 2026")
before_scores = cur.fetchone().RowCount
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.Unmatched_Opponents WHERE BatchID = 33")
before_unmatched = cur.fetchone().RowCount
print(f'  2026 MaxPreps HS_Scores rows: {before_scores}')
print(f'  Unmatched_Opponents rows for batch 33: {before_unmatched}')

print()
print('=== Step 3: run FinalizeMaxPrepsData for batch 33 ===')
cur.execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = 33")
conn.commit()
print('  Done.')

print()
print('=== Step 4: after counts ===')
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = 2026")
after_scores = cur.fetchone().RowCount
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.Unmatched_Opponents WHERE BatchID = 33")
after_unmatched = cur.fetchone().RowCount
print(f'  2026 MaxPreps HS_Scores rows: {after_scores}  (+{after_scores - before_scores})')
print(f'  Unmatched_Opponents rows for batch 33: {after_unmatched}  (+{after_unmatched - before_unmatched})')

print()
print('=== Step 5: run it AGAIN immediately to prove the dedup guard works (should add ~0 new rows) ===')
cur.execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = 33")
conn.commit()
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = 2026")
second_scores = cur.fetchone().RowCount
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.Unmatched_Opponents WHERE BatchID = 33")
second_unmatched = cur.fetchone().RowCount
print(f'  2026 MaxPreps HS_Scores rows after 2nd call: {second_scores}  (+{second_scores - after_scores} -- should be 0)')
print(f'  Unmatched_Opponents rows after 2nd call: {second_unmatched}  (+{second_unmatched - after_unmatched} -- should be 0, this is the guard working)')

print()
print('=== Sample of newly finalized games ===')
cur.execute("""
    SELECT TOP 10 Date, Home, Visitor, Home_Score, Visitor_Score, Source
    FROM dbo.HS_Scores
    WHERE Source LIKE '%maxpreps%' AND Season = 2026
    ORDER BY Date_Added DESC
""")
for r in cur.fetchall():
    print(f'  {r.Date}  {r.Home} {r.Home_Score} - {r.Visitor_Score} {r.Visitor}')

conn.close()
