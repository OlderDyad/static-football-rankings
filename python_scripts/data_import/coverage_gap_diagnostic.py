"""
READ-ONLY diagnostic for the 2025-vs-2026 coverage gap file (coverage_gaps_2025_vs_2026.csv).
Nothing is written to the database.

  python coverage_gap_diagnostic.py > coverage_gap_diagnostic.txt

Category 2 "No MaxPreps URL mapping" (1,952 teams) - how many can be fixed automatically:
  A. an orphan URL_ProperName_Mapping row (Team_ID no longer in HS_Team_Names) whose ProperName
     equals this team's Team_Name  -> just re-point Team_ID (same fix as 2026-06-08, Fix 2)
  B. same, but matching on a normalized name (case / punctuation / "St."-"Saint" / double spaces)
  C. a URL for this Team_ID in HS_Team_MaxPreps that no other Team_ID uses (corruption-safe)
  D. the rest - need URL research (shown by state, 5+ 2025 games first)
Category 6 "Scraped games, none reached HS_Scores" (26) - what games_raw holds for them in 2026.
"""
import csv, os, re, sys, collections, pyodbc
HERE = os.path.dirname(os.path.abspath(__file__))
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()
def hdr(t): print('\n' + '=' * 100 + '\n' + t + '\n' + '=' * 100)
def cols(table):
    cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION", table)
    return [r[0] for r in cur.fetchall()]
def norm(s):
    s = (s or '').lower().replace('saint ', 'st. ').replace('st ', 'st. ')
    s = re.sub(r"[^a-z0-9() ]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

rows = list(csv.reader(open(os.path.join(HERE, 'coverage_gaps_2025_vs_2026.csv'), encoding='utf-8-sig', errors='replace')))
cat = collections.defaultdict(list)          # category -> [(name, games2025, team_id)]
for r in rows:
    if len(r) >= 5: cat[r[0][:1]].append((r[1], int(r[3] or 0), None if r[4] == 'NULL' else int(r[4])))
cat2 = {tid: (n, g) for n, g, tid in cat['2'] if tid}
print(f"File: cat1 {len(cat['1'])}, cat2 {len(cat['2'])}, cat5 {len(cat['5'])}, cat6 {len(cat['6'])}")

hdr('Table columns (for building the fix script)')
for t in ('URL_ProperName_Mapping', 'HS_Team_MaxPreps', 'games_raw', 'Unmatched_Opponents', 'UnmappedURL_Log', 'team_scraping_status'):
    print(f'  {t}: {cols(t)}')

# ---------------- category 2 ----------------
cur.execute("SELECT ID, Team_Name FROM HS_Team_Names")
names = {r.ID: r.Team_Name for r in cur.fetchall()}
cur.execute("SELECT Team_ID, URL, ProperName FROM URL_ProperName_Mapping")
maps = cur.fetchall()
orphans = [m for m in maps if m.Team_ID not in names]
by_exact = collections.defaultdict(list); by_norm = collections.defaultdict(list)
for m in orphans:
    by_exact[(m.ProperName or '').strip()].append(m); by_norm[norm(m.ProperName)].append(m)
print(f'\nURL_ProperName_Mapping: {len(maps)} rows, {len(orphans)} orphans (Team_ID not in HS_Team_Names)')

fixA, fixB, rest = [], [], []
for tid, (n, g) in cat2.items():
    tn = names.get(tid, n)
    if by_exact.get(tn): fixA.append((tid, tn, g, by_exact[tn]))
    elif by_norm.get(norm(tn)): fixB.append((tid, tn, g, by_norm[norm(tn)]))
    else: rest.append((tid, tn, g))
hdr(f'A. Exact ProperName match to an orphan mapping: {len(fixA)} teams ({sum(1 for x in fixA if x[2] >= 5)} with 5+ games)')
for tid, tn, g, ms in sorted(fixA, key=lambda x: -x[2])[:25]:
    print(f'  {tid:>6} {tn:45s} {g:>3}g  <- {ms[0].URL}  (old Team_ID {ms[0].Team_ID}{", +%d more" % (len(ms)-1) if len(ms) > 1 else ""})')
hdr(f'B. Normalized-name match to an orphan mapping: {len(fixB)} teams - REVIEW these')
for tid, tn, g, ms in sorted(fixB, key=lambda x: -x[2])[:60]:
    print(f'  {tid:>6} {tn:45s} {g:>3}g  <- "{ms[0].ProperName}"  {ms[0].URL}')

# C. HS_Team_MaxPreps fallback (corruption-safe: URL used by exactly one Team_ID)
c_tmp = cols('HS_Team_MaxPreps'); urlcol = next((c for c in c_tmp if 'url' in c.lower()), None)
fixC = []
if urlcol:
    cur.execute(f"SELECT Team_ID, [{urlcol}] AS U FROM HS_Team_MaxPreps WHERE [{urlcol}] IS NOT NULL")
    tm = cur.fetchall()
    users = collections.defaultdict(set)
    for r in tm: users[r.U.strip().rstrip('/').lower()].add(r.Team_ID)
    mapped_urls = {(m.URL or '').strip().rstrip('/').lower() for m in maps if m.Team_ID in names}
    per_team = collections.defaultdict(set)
    for r in tm: per_team[r.Team_ID].add(r.U.strip().rstrip('/'))
    still = []
    for tid, tn, g in rest:
        good = [u for u in per_team.get(tid, ()) if len(users[u.lower()]) == 1 and u.lower() not in mapped_urls]
        (fixC if len(good) == 1 else still).append((tid, tn, g, good))
    rest = [(a, b, c) for a, b, c, _ in still]
hdr(f'C. Unique URL in HS_Team_MaxPreps (column {urlcol}): {len(fixC)} teams')
for tid, tn, g, good in sorted(fixC, key=lambda x: -x[2])[:40]:
    print(f'  {tid:>6} {tn:45s} {g:>3}g  {good[0]}')

hdr(f'D. Still unmapped after A-C: {len(rest)} teams ({sum(1 for x in rest if x[2] >= 5)} with 5+ games) - need URL research')
st = collections.Counter(re.search(r'\((\w\w)\)\s*$', n).group(1) if re.search(r'\((\w\w)\)\s*$', n) else '?' for _, n, g in rest if g >= 5)
print('  by state (5+ games):', ', '.join(f'{k} {v}' for k, v in st.most_common()))
for tid, tn, g in sorted(rest, key=lambda x: -x[2])[:40]: print(f'  {tid:>6} {tn:45s} {g:>3}g')

# ---------------- category 6 ----------------
hdr('Category 6 - what games_raw has for these teams (2026)')
gr = cols('games_raw'); tcol = next((c for c in gr if c.lower() in ('team_id', 'source_team_id', 'teamid')), None)
print('  games_raw team column:', tcol)
if tcol:
    ids = [tid for _, _, tid in cat['6'] if tid]
    q = f"SELECT TOP 60 * FROM games_raw WHERE [{tcol}] IN ({','.join('?' * len(ids))}) ORDER BY [{tcol}]"
    cur.execute(q, *ids)
    cn = [d[0] for d in cur.description]
    print('  ' + ' | '.join(cn))
    for r in cur.fetchall(): print('  ' + ' | '.join(str(v)[:40] for v in r))
print('\nDone - nothing was changed.')
