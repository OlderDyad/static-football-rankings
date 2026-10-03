import pyodbc
import re
import csv
from difflib import SequenceMatcher

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== URL_ProperName_Mapping schema ===')
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'URL_ProperName_Mapping'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f'  {r.COLUMN_NAME}  {r.DATA_TYPE}({r.CHARACTER_MAXIMUM_LENGTH})  NULLABLE={r.IS_NULLABLE}')

print()
print('=== URL_ProperName_Mapping_Aliases schema (for reference) ===')
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'URL_ProperName_Mapping_Aliases'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f'  {r.COLUMN_NAME}  {r.DATA_TYPE}({r.CHARACTER_MAXIMUM_LENGTH})  NULLABLE={r.IS_NULLABLE}')

print()
print('=== Sample existing URL_ProperName_Mapping rows (to see real value patterns) ===')
cur.execute("SELECT TOP 5 * FROM dbo.URL_ProperName_Mapping")
cols = [c[0] for c in cur.description]
print('  columns:', cols)
for r in cur.fetchall():
    print(' ', tuple(r))

# ---- Rebuild the same reconciliation as size_url_mapping_gap4.py ----
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

def normalize_url(u):
    while u.rstrip('/').endswith('/football'):
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

CITY_ABBREV = {'mt': 'mount', 'ft': 'fort', 'mtn': 'mountain', 'st': 'saint'}

def expand_city(city_slug):
    return ' '.join(CITY_ABBREV.get(w, w) for w in city_slug.split('-'))

def parse_url(url):
    m = re.match(r'https?://(?:www\.)?maxpreps\.com/([a-z]{2})/([^/]+)/([^/]+)/', url)
    if not m:
        return None
    state, city_slug, school_mascot_slug = m.groups()
    return state.upper(), city_slug, school_mascot_slug

def normalize(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

confident = []   # (team_id, Team_Name, chosen_url)
needs_review = []  # (team_id, Team_Name, City, State, reason, candidate_urls)

for team_id, (name, city, state) in teams.items():
    urls = candidates.get(team_id, set())
    name_norm = normalize(name)
    gated = []
    for u in urls:
        parsed = parse_url(u)
        if not parsed:
            continue
        url_state, city_slug, school_mascot_slug = parsed
        city_expanded = expand_city(city_slug)
        state_ok = state and url_state.upper() == state.strip('()').upper()
        city_ok = name_norm.startswith(normalize(city_expanded))
        if state_ok and city_ok:
            gated.append((u, school_mascot_slug))

    if not gated:
        needs_review.append((team_id, name, city, state, 'no_city_state_match', '; '.join(sorted(urls))))
        continue

    if len(gated) == 1:
        confident.append((team_id, name, gated[0][0]))
        continue

    scored = sorted(((u, SequenceMatcher(None, name_norm, normalize(sm)).ratio()) for u, sm in gated), key=lambda x: -x[1])
    best_url, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0
    if best_score - second_score >= 0.15:
        confident.append((team_id, name, best_url))
    else:
        needs_review.append((team_id, name, city, state, 'ambiguous_qualifier', '; '.join(u for u, _ in gated)))

with open('confident_url_backfill.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Team_ID', 'Team_Name', 'MaxPrepsURL'])
    for row in confident:
        w.writerow(row)

with open('needs_manual_review.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Team_ID', 'Team_Name', 'City', 'State', 'Reason', 'CandidateURLs'])
    for row in needs_review:
        w.writerow(row)

print()
print(f'Wrote {len(confident)} rows to confident_url_backfill.csv')
print(f'Wrote {len(needs_review)} rows to needs_manual_review.csv')
