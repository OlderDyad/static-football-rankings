import pyodbc
import re
from difflib import SequenceMatcher

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Corrected sizing using DISTINCT team_id (prior counts were inflated by duplicate rows) ===')
cur.execute("""
    SELECT COUNT(DISTINCT S.team_id) AS DistinctGapTeams
    FROM dbo.team_scraping_status AS S
    LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
    WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL
""")
total_distinct = cur.fetchone()[0]
print(f'  Distinct gap team_ids (no URL_ProperName_Mapping row): {total_distinct}')

# Pull each gap team's name/city/state plus every candidate URL on file.
cur.execute("""
    SELECT DISTINCT S.team_id, N.Team_Name, N.City, N.State
    FROM dbo.team_scraping_status AS S
    LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
    JOIN dbo.HS_Team_Names AS N ON N.ID = S.team_id
    WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL
""")
teams = {r.team_id: (r.Team_Name, r.City, r.State) for r in cur.fetchall()}

cur.execute("""
    SELECT Team_ID, MaxPrepsURL
    FROM dbo.HS_Team_MaxPreps
    WHERE Team_ID IN (SELECT DISTINCT S.team_id
                       FROM dbo.team_scraping_status AS S
                       LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
                       WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL)
""")
candidates = {}
for r in cur.fetchall():
    candidates.setdefault(r.Team_ID, set()).add(r.MaxPrepsURL)

conn.close()

def normalize(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()

def slug_text(url):
    # last two path segments usually carry the school/mascot name, e.g.
    # /il/colfax/ridgeview-lexington-mustangs/football/ -> "colfax ridgeview lexington mustangs"
    parts = [p for p in url.split('/') if p and p not in ('https:', 'www.maxpreps.com', 'football')]
    return normalize(' '.join(parts[-2:]))

results = {'no_candidates': 0, 'single_high_conf': 0, 'single_low_conf': 0,
           'multi_clear_winner': 0, 'multi_ambiguous': 0}
detail_rows = []

for team_id, (name, city, state) in teams.items():
    urls = candidates.get(team_id, set())
    target = normalize(f'{city} {name}')
    if not urls:
        results['no_candidates'] += 1
        continue
    scored = sorted(
        ((u, SequenceMatcher(None, target, slug_text(u)).ratio()) for u in urls),
        key=lambda x: -x[1]
    )
    best_url, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0
    if len(urls) == 1:
        if best_score >= 0.5:
            results['single_high_conf'] += 1
        else:
            results['single_low_conf'] += 1
        detail_rows.append((team_id, name, city, state, best_url, round(best_score, 2), 'single'))
    else:
        if best_score >= 0.5 and (best_score - second_score) >= 0.15:
            results['multi_clear_winner'] += 1
            detail_rows.append((team_id, name, city, state, best_url, round(best_score, 2), 'multi-clear'))
        else:
            results['multi_ambiguous'] += 1
            detail_rows.append((team_id, name, city, state, best_url, round(best_score, 2), 'multi-AMBIGUOUS'))

print()
print('=== Name-match based reconciliation (city+name vs. URL slug, difflib similarity) ===')
print(f'  Total distinct gap teams:                         {total_distinct}')
print(f'  No candidate URL at all (real research needed):   {results["no_candidates"]}')
print(f'  Single candidate, name matches well (auto-safe):  {results["single_high_conf"]}')
print(f'  Single candidate, name match is weak (review):    {results["single_low_conf"]}')
print(f'  Multiple candidates, one clear winner (auto-ok):  {results["multi_clear_winner"]}')
print(f'  Multiple candidates, genuinely ambiguous (review):{results["multi_ambiguous"]}')

print()
print('=== Sample: multi-candidate cases with a clear winner (should be safe to auto-pick) ===')
shown = 0
for row in detail_rows:
    if row[6] == 'multi-clear' and shown < 10:
        print(f'  team_id={row[0]}  {row[1]} ({row[2]}, {row[3]})  score={row[5]}  ->  {row[4]}')
        shown += 1

print()
print('=== Sample: genuinely ambiguous cases (need manual review) ===')
shown = 0
for row in detail_rows:
    if row[6] == 'multi-AMBIGUOUS' and shown < 10:
        print(f'  team_id={row[0]}  {row[1]} ({row[2]}, {row[3]})  best_score={row[5]}  ->  {row[4]}')
        shown += 1
