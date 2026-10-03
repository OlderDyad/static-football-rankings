import pyodbc
import re
from difflib import SequenceMatcher

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

def team_names_for_season(season):
    cur.execute("""
        SELECT DISTINCT Home AS TeamName FROM dbo.HS_Scores WHERE Season = ?
        UNION
        SELECT DISTINCT Visitor AS TeamName FROM dbo.HS_Scores WHERE Season = ?
    """, season, season)
    return {r.TeamName for r in cur.fetchall() if r.TeamName}

print('=== Pulling distinct team names per season ===')
names_2025 = team_names_for_season(2025)
names_2026 = team_names_for_season(2026)
print(f'  2025: {len(names_2025)} distinct names')
print(f'  2026: {len(names_2026)} distinct names')

both = names_2025 & names_2026
only_2025 = names_2025 - names_2026
only_2026 = names_2026 - names_2025

print(f'  In both seasons (ignoring these): {len(both)}')
print(f'  2025-only (residual): {len(only_2025)}')
print(f'  2026-only (residual): {len(only_2026)}')

conn.close()

def extract_state(name):
    m = re.search(r'\(([A-Z]{2})\)\s*$', name)
    return m.group(1) if m else None

def normalize(s):
    s = re.sub(r'\([A-Z]{2}\)\s*$', '', s)  # strip trailing state tag
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()

# Bucket residuals by state so we only compare same-state candidates.
by_state_2025 = {}
for n in only_2025:
    by_state_2025.setdefault(extract_state(n), []).append(n)
by_state_2026 = {}
for n in only_2026:
    by_state_2026.setdefault(extract_state(n), []).append(n)

print()
print('=== Cross-matching residuals within the same state (likely same-team naming drift) ===')
candidates = []
for state, names26 in by_state_2026.items():
    names25 = by_state_2025.get(state, [])
    if not names25:
        continue
    for n26 in names26:
        norm26 = normalize(n26)
        best = None
        best_score = 0.0
        for n25 in names25:
            score = SequenceMatcher(None, norm26, normalize(n25)).ratio()
            if score > best_score:
                best_score = score
                best = n25
        if best and best_score >= 0.75:
            candidates.append((n26, best, round(best_score, 2)))

candidates.sort(key=lambda x: -x[2])
print(f'  Found {len(candidates)} likely-same-team candidate pairs (similarity >= 0.75)')
for n26, n25, score in candidates:
    print(f'  {score}  2026: {n26!r:55s}  <->  2025: {n25!r}')

print()
print(f'=== Residual counts after removing matched candidates ===')
matched_26 = {c[0] for c in candidates}
matched_25 = {c[1] for c in candidates}
print(f'  2026-only names with NO plausible 2025 match: {len(only_2026 - matched_26)}')
print(f'  2025-only names with NO plausible 2026 match: {len(only_2025 - matched_25)}')
