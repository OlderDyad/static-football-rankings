import pyodbc
import re
from difflib import SequenceMatcher

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT S.team_id, N.Team_Name, N.City, N.State
    FROM dbo.team_scraping_status AS S
    LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
    JOIN dbo.HS_Team_Names AS N ON N.ID = S.team_id
    WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL
""")
teams = {r.team_id: (r.Team_Name, r.City, r.State) for r in cur.fetchall()}
team_ids = list(teams.keys())

cur.execute("""
    SELECT Team_ID, MaxPrepsURL
    FROM dbo.HS_Team_MaxPreps
    WHERE Team_ID IN (SELECT DISTINCT S.team_id
                       FROM dbo.team_scraping_status AS S
                       LEFT JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
                       WHERE S.batch_id = 33 AND S.status IN ('pending','failed') AND M.Team_ID IS NULL)
""")
def normalize_url(u):
    # Collapse a doubled trailing path segment bug seen in HS_Team_MaxPreps,
    # e.g. ".../football/football/" -> ".../football/"
    while u.rstrip('/').endswith('/football'):
        # strip one "football" layer at a time until only one remains
        parts = u.rstrip('/').split('/')
        if len(parts) >= 2 and parts[-1] == 'football' and parts[-2] == 'football':
            u = '/'.join(parts[:-1]) + '/'
        else:
            break
    return u

candidates = {}
for r in cur.fetchall():
    candidates.setdefault(r.Team_ID, set()).add(normalize_url(r.MaxPrepsURL))

conn.close()

# City-only abbreviation expansions (per user: only the CITY segment gets
# de-abbreviated for the proper name -- school/mascot qualifiers keep
# whatever convention the DB already uses, e.g. "St. Patrick" stays as-is).
CITY_ABBREV = {
    'mt': 'mount', 'ft': 'fort', 'mtn': 'mountain',
    'st': 'saint',  # only applied to the city token itself, not qualifiers
}

def expand_city(city_slug):
    words = city_slug.split('-')
    return ' '.join(CITY_ABBREV.get(w, w) for w in words)

def parse_url(url):
    # https://www.maxpreps.com/mi/mt-pleasant/mt-pleasant-oilers/football/...
    m = re.match(r'https?://(?:www\.)?maxpreps\.com/([a-z]{2})/([^/]+)/([^/]+)/', url)
    if not m:
        return None
    state, city_slug, school_mascot_slug = m.groups()
    return state.upper(), city_slug, school_mascot_slug

def normalize(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()

results = {'no_candidates': 0, 'no_city_state_match': 0, 'single_gated_ok': 0,
           'multi_one_city_match_clear_qualifier': 0, 'multi_one_city_match_ambiguous_qualifier': 0,
           'multi_several_city_matches': 0}
detail = {k: [] for k in results}

for team_id, (name, city, state) in teams.items():
    urls = candidates.get(team_id, set())
    if not urls:
        results['no_candidates'] += 1
        continue

    name_norm = normalize(name)
    state_bracket = f'({state.strip("()")})' if state else None

    gated = []  # urls whose city+state matches this team's Team_Name
    for u in urls:
        parsed = parse_url(u)
        if not parsed:
            continue
        url_state, city_slug, school_mascot_slug = parsed
        city_expanded = expand_city(city_slug)
        # hard gate: does Team_Name start with the expanded city AND end with the state?
        state_ok = state and url_state.upper() == state.strip('()').upper()
        city_ok = name_norm.startswith(normalize(city_expanded))
        if state_ok and city_ok:
            gated.append((u, school_mascot_slug))

    if not gated:
        results['no_city_state_match'] += 1
        detail['no_city_state_match'].append((team_id, name, city, state, sorted(urls)))
        continue

    if len(gated) == 1:
        results['single_gated_ok'] += 1
        detail['single_gated_ok'].append((team_id, name, city, state, gated[0][0]))
        continue

    # Multiple candidates pass the city+state gate -- use the qualifier
    # (Team_Name minus city minus state) vs. the school/mascot slug to break the tie.
    qualifier = name_norm
    for u, school_mascot_slug in gated:
        pass
    scored = []
    for u, school_mascot_slug in gated:
        score = SequenceMatcher(None, qualifier, normalize(school_mascot_slug)).ratio()
        scored.append((u, score))
    scored.sort(key=lambda x: -x[1])
    best_url, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0

    if best_score - second_score >= 0.15:
        results['multi_one_city_match_clear_qualifier'] += 1
        detail['multi_one_city_match_clear_qualifier'].append((team_id, name, city, state, best_url, round(best_score, 2)))
    else:
        results['multi_one_city_match_ambiguous_qualifier'] += 1
        detail['multi_one_city_match_ambiguous_qualifier'].append((team_id, name, city, state, [x[0] for x in scored]))

print('=== City+State-gated reconciliation (973 distinct gap teams) ===')
print(f'  No candidate URL at all:                                    {results["no_candidates"]}')
print(f'  Candidates exist but NONE match city+state (needs research):{results["no_city_state_match"]}')
print(f'  Exactly one candidate passes city+state gate (auto-safe):   {results["single_gated_ok"]}')
print(f'  Multiple pass gate, qualifier gives clear winner (auto-ok): {results["multi_one_city_match_clear_qualifier"]}')
print(f'  Multiple pass gate, qualifier still ambiguous (review):     {results["multi_one_city_match_ambiguous_qualifier"]}')

print()
print('=== Sample: single gated match (auto-safe bucket) ===')
for row in detail['single_gated_ok'][:10]:
    print(f'  team_id={row[0]}  {row[1]} ({row[2]}, {row[3]})  ->  {row[4]}')

print()
print('=== Sample: candidates exist but none pass city+state gate (real research needed) ===')
for row in detail['no_city_state_match'][:10]:
    print(f'  team_id={row[0]}  {row[1]} ({row[2]}, {row[3]})  candidates={row[4]}')

print()
print('=== Sample: multiple pass gate, still ambiguous after qualifier check ===')
for row in detail['multi_one_city_match_ambiguous_qualifier'][:10]:
    print(f'  team_id={row[0]}  {row[1]} ({row[2]}, {row[3]})  candidates={row[4]}')
