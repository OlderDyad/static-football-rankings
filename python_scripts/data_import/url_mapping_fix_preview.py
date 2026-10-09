"""
STEP 1 of 2 - PREVIEW ONLY (nothing written to the database).

Rebuilds MaxPreps URL mappings for teams that lost them (coverage_gaps_2025_vs_2026.csv, category 2).
Root cause: team records were renamed/merged (e.g. "Kenosha Saint Joseph (WI)" -> "Kenosha St. Joseph (WI)",
"Bascom Hopewell Loudon (OH)" -> "Bascom Hopewell-Loudon (OH)"); the old record was deleted but
URL_ProperName_Mapping kept the old Team_ID, and the 2026 scraper only runs mappings whose Team_ID exists.

Writes:
  url_mapping_fix_plan.json      - automatic fixes (groups B and C below)
  url_mapping_fix_review.csv     - group D candidates; put Y in the Approve column for the ones you accept

  B  re-point an orphan mapping whose ProperName matches the team after normalizing
     (St./Saint, hyphens, apostrophes, case). Team_ID and ProperName are updated.
  C  add a mapping from HS_Team_MaxPreps when that URL belongs to no other team, is not already mapped,
     and the URL's state matches the team's state (guards against the known HS_Team_MaxPreps corruption).
  D  (review) match remaining US teams to a remaining orphan mapping or to an unmapped 2026 opponent URL
     by name tokens inside the URL (same state, exactly one candidate).

  python url_mapping_fix_preview.py > url_mapping_fix_preview.txt
"""
import csv, os, re, json, collections, pyodbc
HERE = os.path.dirname(os.path.abspath(__file__))
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()
CANADA = {'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'ON', 'PE', 'QC', 'SK', 'YT', 'NT', 'CN'}

def norm(s):
    s = (s or '').lower().replace("'", '').replace('’', '')
    s = re.sub(r'\bsaint\b', 'st', s); s = re.sub(r'\bst\.', 'st', s)
    s = re.sub(r'[^a-z0-9() ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()
def state_of(name):
    m = re.search(r'\(([A-Z]{2})\)\s*$', name or ''); return m.group(1) if m else None
def canon_url(u):
    u = (u or '').strip().rstrip('/')
    u = re.sub(r'(/football)?(/\d\d-\d\d)?(/schedule)?$', '', u, flags=re.I)
    return u + '/football/schedule/'
def url_key(u): return canon_url(u).lower()
def url_parts(u):
    m = re.match(r'https?://www\.maxpreps\.com/([a-z]{2})/([^/]+)/([^/]+)', (u or '').strip(), re.I)
    return (m.group(1).upper(), set(m.group(2).lower().split('-')) | set(m.group(3).lower().split('-'))) if m else (None, set())
def name_tokens(name):
    base = norm(re.sub(r'\s*\([A-Z]{2}\)\s*$', '', name or ''))
    return {t for t in base.replace('(', ' ').replace(')', ' ').split() if t}

rows = list(csv.reader(open(os.path.join(HERE, 'coverage_gaps_2025_vs_2026.csv'), encoding='utf-8-sig', errors='replace')))
cat2 = {int(r[4]): (r[1], int(r[3] or 0)) for r in rows if len(r) >= 5 and r[0].startswith('2') and r[4] != 'NULL'}
cur.execute("SELECT ID, Team_Name FROM HS_Team_Names"); names = {r.ID: r.Team_Name for r in cur.fetchall()}
cur.execute("SELECT Team_ID, URL, ProperName FROM URL_ProperName_Mapping"); maps = cur.fetchall()
mapped_ids = {m.Team_ID for m in maps if m.Team_ID in names}
mapped_urls = {url_key(m.URL) for m in maps if m.Team_ID in names}
orphans = [m for m in maps if m.Team_ID not in names]
targets = {tid: names.get(tid, n) for tid, (n, g) in cat2.items() if tid in names and tid not in mapped_ids}
games = {tid: g for tid, (n, g) in cat2.items()}
print(f'Category-2 teams still existing and unmapped: {len(targets)}   orphan mappings: {len(orphans)}')

plan = {'B': [], 'C': []}; used_orphans = set(); used_urls = set()
# ---- B
by_norm = collections.defaultdict(list)
for m in orphans: by_norm[norm(m.ProperName)].append(m)
for tid, tn in targets.items():
    cands = by_norm.get(norm(tn), [])
    urls = {url_key(m.URL) for m in cands}
    if cands and len(urls) == 1 and next(iter(urls)) not in mapped_urls and next(iter(urls)) not in used_urls:
        m = cands[0]
        plan['B'].append({'team_id': tid, 'team_name': tn, 'old_team_id': m.Team_ID, 'url': m.URL, 'old_proper': m.ProperName})
        used_orphans.update((c.Team_ID, c.URL) for c in cands); used_urls |= urls
doneB = {p['team_id'] for p in plan['B']}
# ---- C
cur.execute("SELECT Team_ID, MaxPrepsURL FROM HS_Team_MaxPreps WHERE MaxPrepsURL IS NOT NULL")
tm = cur.fetchall(); users = collections.defaultdict(set); per = collections.defaultdict(set)
for r in tm: users[url_key(r.MaxPrepsURL)].add(r.Team_ID); per[r.Team_ID].add(url_key(r.MaxPrepsURL))
for tid, tn in targets.items():
    if tid in doneB: continue
    st = state_of(tn)
    good = [u for u in per.get(tid, ()) if len(users[u]) == 1 and u not in mapped_urls and u not in used_urls and url_parts(u)[0] == st]
    if len(good) == 1:
        plan['C'].append({'team_id': tid, 'team_name': tn, 'url': canon_url(good[0])}); used_urls.add(good[0])
doneC = {p['team_id'] for p in plan['C']}
# ---- D (review)
pool = []   # (url, label, source)
for m in orphans:
    if (m.Team_ID, m.URL) not in used_orphans: pool.append((m.URL, m.ProperName, 'orphan mapping', m.Team_ID))
cur.execute("SELECT DISTINCT opponent_maxpreps_url, opponent_name_raw FROM games_raw WHERE season_year = 2026 AND opponent_maxpreps_url LIKE '%maxpreps.com/%'")
seen = set()
for u, n in cur.fetchall():
    k = url_key(u)
    if k in mapped_urls or k in seen: continue
    seen.add(k); pool.append((u, n, '2026 opponent URL', None))
pool = [p for p in pool if url_key(p[0]) not in used_urls]
pool_parts = [(p, *url_parts(p[0])) for p in pool]
review = []; claim = collections.Counter()
for tid, tn in targets.items():
    if tid in doneB or tid in doneC: continue
    st = state_of(tn)
    if st in CANADA: continue
    toks = name_tokens(tn)
    if not toks: continue
    hits = {url_key(p[0]): p for p, s, ut in pool_parts if s == st and toks <= ut}
    if len(hits) == 1:
        p = next(iter(hits.values())); review.append([tid, tn, games.get(tid, 0), canon_url(p[0]), p[1], p[2], p[3] or '', '']); claim[url_key(p[0])] += 1
review = [r for r in review if claim[url_key(r[3])] == 1]     # drop URLs claimed by two teams
with open(os.path.join(HERE, 'url_mapping_fix_review.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['Team_ID', 'Team_Name', 'Games2025', 'URL', 'Name_on_source', 'Source', 'Old_Team_ID', 'Approve'])
    w.writerows(sorted(review, key=lambda r: -r[2]))
json.dump(plan, open(os.path.join(HERE, 'url_mapping_fix_plan.json'), 'w'), indent=1)

def show(t, items, f):
    print('\n' + '=' * 100 + f'\n{t}: {len(items)}\n' + '=' * 100)
    for p in items[:40]: print('  ' + f(p))
show('B. Re-point orphan mapping (automatic)', sorted(plan['B'], key=lambda p: -games.get(p['team_id'], 0)),
     lambda p: f"{p['team_id']:>6} {p['team_name']:42s} <- \"{p['old_proper']}\" (old ID {p['old_team_id']})")
show('C. Add mapping from HS_Team_MaxPreps (automatic)', sorted(plan['C'], key=lambda p: -games.get(p['team_id'], 0)),
     lambda p: f"{p['team_id']:>6} {p['team_name']:42s} {p['url']}")
show('D. Candidates for your review (url_mapping_fix_review.csv)', sorted(review, key=lambda r: -r[2]),
     lambda r: f"{r[0]:>6} {r[1]:42s} {r[3]}  [{r[5]}: {r[4]}]")
left = [tid for tid in targets if tid not in doneB and tid not in doneC and tid not in {r[0] for r in review}]
us_left = [t for t in left if state_of(targets[t]) not in CANADA]
print(f'\nStill unmapped after B/C/D: {len(left)} ({len(us_left)} US, {len(left) - len(us_left)} Canadian - separate source)')
print(f"Automatic: B {len(plan['B'])} + C {len(plan['C'])} = {len(plan['B']) + len(plan['C'])} teams.  Review: {len(review)}.")
print('Next: open url_mapping_fix_review.csv, put Y in Approve for good rows, then run  python url_mapping_fix_commit.py')
