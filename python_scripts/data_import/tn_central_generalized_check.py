import pyodbc
import re

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

# Step 1: pull every same-day conflict involving Knoxville Central (TN),
# i.e. every date where Knoxville Central appears more than once.
cur.execute("""
    SELECT s.ID, s.Date, s.Season, s.Home, s.Visitor, s.Home_Score, s.Visitor_Score, s.Source
    FROM HS_Scores s
    WHERE (s.Home = 'Knoxville Central (TN)' OR s.Visitor = 'Knoxville Central (TN)')
      AND s.Date IN (
          SELECT s2.Date FROM HS_Scores s2
          WHERE (s2.Home = 'Knoxville Central (TN)' OR s2.Visitor = 'Knoxville Central (TN)')
          GROUP BY s2.Date HAVING COUNT(*) > 1
      )
    ORDER BY s.Date
""")
conflict_rows = cur.fetchall()

# Group into per-date clusters, and for each row figure out who the "opponent" is
# (the team on the other side of Knoxville Central).
from collections import defaultdict
by_date = defaultdict(list)
for r in conflict_rows:
    opponent = r.Visitor if r.Home == 'Knoxville Central (TN)' else r.Home
    by_date[(r.Date, r.Season)].append((r, opponent))

# Step 2: get all distinct city-prefixed "Central" team names that exist in HS_Scores,
# e.g. "Nashville Central (TN)", "Memphis Central (TN)", etc. Build a City -> Full Name map.
cur.execute("""
    SELECT DISTINCT Home AS TeamName FROM HS_Scores WHERE Home LIKE '% Central (TN)'
    UNION
    SELECT DISTINCT Visitor FROM HS_Scores WHERE Visitor LIKE '% Central (TN)'
""")
central_teams = [r.TeamName for r in cur.fetchall()]
# Map first-word city -> full team name (e.g. "Nashville" -> "Nashville Central (TN)")
city_to_central = {}
for t in central_teams:
    m = re.match(r'^(\w+)\s+Central \(TN\)$', t)
    if m:
        city_to_central[m.group(1)] = t

print(f'Known "<City> Central (TN)" teams in TN data: {sorted(city_to_central.values())}')
print()

results = []
for (date, season), rows in sorted(by_date.items()):
    if len(rows) < 2:
        continue
    for r, opponent in rows:
        # Try to extract a city prefix from the opponent's name to see if it has its own Central team
        m = re.match(r'^(\w+)\s+', opponent)
        opp_city = m.group(1) if m else None
        candidate_central = city_to_central.get(opp_city) if opp_city else None

        if not candidate_central or candidate_central == 'Knoxville Central (TN)':
            continue  # no same-city Central rival to compare against, or opponent IS Knoxville Central itself

        # Does a game already exist this season between opponent and their own city's Central team?
        cur.execute("""
            SELECT Date FROM HS_Scores
            WHERE Season = ?
              AND ((Home = ? AND Visitor = ?) OR (Home = ? AND Visitor = ?))
        """, season, opponent, candidate_central, candidate_central, opponent)
        existing = cur.fetchall()
        verdict = 'DUPLICATE (already has game vs own Central)' if existing else 'RELABEL CANDIDATE (no game vs own Central found)'
        results.append((date, season, r.Home, r.Home_Score, r.Visitor_Score, r.Visitor, opponent, candidate_central, verdict, r.ID))

print(f'{"Date":<12} {"Season":<7} {"Matchup":<55} {"Opponent City-Central":<25} Verdict')
print('-' * 140)
for date, season, home, hs, vs, visitor, opponent, candidate_central, verdict, rid in results:
    matchup = f'{home} {hs}-{vs} {visitor}'
    print(f'{str(date):<12} {season:<7} {matchup:<55} {candidate_central:<25} {verdict}   [ID={rid}]')

print()
print(f'Total same-day Knoxville Central conflict rows examined: {len(conflict_rows)}')
print(f'Rows where opponent has an identifiable own-city Central team: {len(results)}')
relabel_count = sum(1 for x in results if x[8].startswith('RELABEL'))
dup_count = sum(1 for x in results if x[8].startswith('DUPLICATE'))
print(f'  -> Relabel candidates: {relabel_count}')
print(f'  -> Duplicate candidates: {dup_count}')

print()
print('=== Conflict rows where opponent has NO identifiable own-city Central team (needs manual review) ===')
handled_ids = {r[9] for r in results}
for (date, season), rows in sorted(by_date.items()):
    if len(rows) < 2:
        continue
    for r, opponent in rows:
        if r.ID not in handled_ids:
            print(f'  {r.Date}  {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]  ID={r.ID}')
