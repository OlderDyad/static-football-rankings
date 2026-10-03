"""
STEP 2 of 2 - COMMIT. Applies nc_cleanup_plan.json (made by nc_cleanup_preview.py).

Every change targets one exact row (alias by Alias_Name + Newspaper_Region + current target;
game by ID + current team name). If ANY row doesn't match exactly once, everything is rolled back.
Take a .bak first if you want a restore point.

  python nc_cleanup_commit.py
"""
import json, pyodbc, sys
plan = json.load(open('nc_cleanup_plan.json'))
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;', autocommit=False)
cur = conn.cursor()
print(f"Plan: {len(plan['alias_updates'])} alias rule(s), {len(plan['score_updates'])} game row(s).")
if input("Type COMMIT to apply: ").strip() != 'COMMIT':
    print('Nothing changed.'); sys.exit()

problems = []
for a in plan['alias_updates']:
    cur.execute("""UPDATE HS_Team_Name_Alias SET Standardized_Name = ?
                   WHERE Alias_Name = ? AND Newspaper_Region = ? AND Standardized_Name = ?""", a['new'], a['alias'], a['region'], a['old'])
    if cur.rowcount != 1: problems.append(f"alias {a['alias']!r} [{a['region']}] matched {cur.rowcount} rows")
for s in plan['score_updates']:
    col = 'Home' if s['side'] == 'Home' else 'Visitor'
    cur.execute(f"UPDATE HS_Scores SET {col} = ? WHERE ID = ? AND {col} = ?", s['new'], s['id'], s['old'])
    if cur.rowcount != 1: problems.append(f"game {s['id']} matched {cur.rowcount} rows")

# zero-row verification: nothing in the plan should still point at the old value
left = 0
for a in plan['alias_updates']:
    cur.execute("SELECT COUNT(*) FROM HS_Team_Name_Alias WHERE Alias_Name = ? AND Newspaper_Region = ? AND Standardized_Name = ?", a['alias'], a['region'], a['old'])
    left += cur.fetchone()[0]
for s in plan['score_updates']:
    cur.execute("SELECT COUNT(*) FROM HS_Scores WHERE ID = ? AND (Home = ? OR Visitor = ?)", s['id'], s['old'], s['old'])
    left += cur.fetchone()[0]

if problems or left:
    conn.rollback()
    print('ROLLED BACK - nothing changed.'); [print('  ', p) for p in problems]; print(f'   rows still on old value: {left}')
else:
    conn.commit()
    print(f"COMMITTED: {len(plan['alias_updates'])} alias rule(s) repointed, {len(plan['score_updates'])} game row(s) refiled. Verification: 0 rows left on old values.")
