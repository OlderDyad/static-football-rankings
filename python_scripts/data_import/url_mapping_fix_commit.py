"""
STEP 2 of 2 - COMMIT. Applies url_mapping_fix_plan.json (groups B and C) plus every row marked Y in
url_mapping_fix_review.csv.

v2: URL is the table's primary key, and many "new" URLs already sit in the table on an ORPHAN row
(Team_ID of a deleted team). For every URL the script now:
  - re-points the existing orphan row to the team        (counted as "re-pointed")
  - skips it if a LIVE team already owns that URL         (listed as "skipped", not fatal)
  - inserts it only if the URL is not in the table at all (counted as "added")
A team that already has a mapping is skipped. Any statement that does not touch exactly one row
rolls back everything.

  python url_mapping_fix_commit.py
"""
import csv, os, json, sys, pyodbc
HERE = os.path.dirname(os.path.abspath(__file__))
plan = json.load(open(os.path.join(HERE, 'url_mapping_fix_plan.json')))
approved = [r for r in csv.DictReader(open(os.path.join(HERE, 'url_mapping_fix_review.csv'), encoding='utf-8'))
            if r['Approve'].strip().upper() == 'Y']
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;', autocommit=False)
cur = conn.cursor()
cur.execute("SELECT ID FROM HS_Team_Names"); live = {r[0] for r in cur.fetchall()}
cur.execute("SELECT COUNT(DISTINCT M.Team_ID) FROM URL_ProperName_Mapping M JOIN HS_Team_Names T ON T.ID = M.Team_ID")
before = cur.fetchone()[0]

def base(u): return (u or '').strip().rstrip('/').lower().split('/football')[0]
work = [('B', p['team_id'], p['team_name'], p['url'], p['old_team_id']) for p in plan['B']]
work += [('C', p['team_id'], p['team_name'], p['url'], None) for p in plan['C']]
work += [('D', int(r['Team_ID']), r['Team_Name'], r['URL'], None) for r in approved]
print(f"Before: {before} teams mapped.   To apply: B {len(plan['B'])}, C {len(plan['C'])}, D {len(approved)}")
if input('Type COMMIT to apply: ').strip() != 'COMMIT': print('Nothing changed.'); sys.exit()

stats = {'re-pointed': 0, 'added': 0}; skipped = []; fatal = []; done_teams = set(); done_urls = set()
for grp, tid, name, url, old in work:
    b = base(url)
    if tid in done_teams or b in done_urls: skipped.append(f'{grp} {name}: duplicate in this run'); continue
    cur.execute("SELECT COUNT(*) FROM URL_ProperName_Mapping WHERE Team_ID = ?", tid)
    if cur.fetchone()[0]: skipped.append(f'{grp} {name}: team already mapped'); continue
    cur.execute("SELECT Team_ID, URL FROM URL_ProperName_Mapping WHERE LOWER(URL) LIKE ?", b + '%')
    rows = [r for r in cur.fetchall() if base(r.URL) == b]
    owners = [r for r in rows if r.Team_ID in live]
    if owners:
        skipped.append(f'{grp} {name}: URL already belongs to live Team_ID {owners[0].Team_ID}'); continue
    if rows:
        r = rows[0]
        cur.execute("UPDATE URL_ProperName_Mapping SET Team_ID = ?, ProperName = ? WHERE URL = ? AND Team_ID = ?", tid, name, r.URL, r.Team_ID)
        if cur.rowcount != 1: fatal.append(f'{grp} {name}: update hit {cur.rowcount} rows'); break
        stats['re-pointed'] += 1
    else:
        cur.execute("INSERT INTO URL_ProperName_Mapping (URL, ProperName, Team_ID) VALUES (?, ?, ?)", url, name, tid)
        stats['added'] += 1
    done_teams.add(tid); done_urls.add(b)

if fatal:
    conn.rollback(); print('ROLLED BACK - nothing changed:'); [print('  ', f) for f in fatal]; sys.exit()
conn.commit()
cur.execute("SELECT COUNT(DISTINCT M.Team_ID) FROM URL_ProperName_Mapping M JOIN HS_Team_Names T ON T.ID = M.Team_ID")
after = cur.fetchone()[0]
print(f"COMMITTED: {stats['re-pointed']} orphan rows re-pointed, {stats['added']} new rows added, {len(skipped)} skipped.")
print(f"Teams the scraper will run: {before} -> {after}")
with open(os.path.join(HERE, 'url_mapping_fix_skipped.txt'), 'w', encoding='utf-8') as f: f.write('\n'.join(skipped))
print('Skipped items listed in url_mapping_fix_skipped.txt')
