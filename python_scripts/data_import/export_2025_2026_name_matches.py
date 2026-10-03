import pyodbc
import re
import csv
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

names_2025 = team_names_for_season(2025)
names_2026 = team_names_for_season(2026)
conn.close()

only_2025 = names_2025 - names_2026
only_2026 = names_2026 - names_2025

def extract_state(name):
    m = re.search(r'\(([A-Z]{2})\)\s*$', name)
    return m.group(1) if m else None

def normalize(s):
    s = re.sub(r'\([A-Z]{2}\)\s*$', '', s)
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()

by_state_2025 = {}
for n in only_2025:
    by_state_2025.setdefault(extract_state(n), []).append(n)

rows = []
for n26 in only_2026:
    state = extract_state(n26)
    names25 = by_state_2025.get(state, [])
    if not names25:
        continue
    norm26 = normalize(n26)
    best, best_score = None, 0.0
    for n25 in names25:
        score = SequenceMatcher(None, norm26, normalize(n25)).ratio()
        if score > best_score:
            best_score, best = score, n25
    if best and best_score >= 0.75:
        rows.append((state, n26, best, round(best_score, 3)))

rows.sort(key=lambda r: (r[0], -r[3]))

out_path = 'maxpreps_name_drift_candidates_2026.csv'
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['State', 'Alias_Name_2026_Scraped', 'Standardized_Name_2025_Existing', 'Similarity_Score', 'Review_Status'])
    for state, n26, n25, score in rows:
        review = 'auto-safe' if score >= 0.9 else 'REVIEW-NEEDED'
        w.writerow([state, n26, n25, score, review])

print(f'Wrote {len(rows)} candidate pairs to {out_path}')
print(f'  auto-safe (score >= 0.9): {sum(1 for r in rows if r[3] >= 0.9)}')
print(f'  REVIEW-NEEDED (score < 0.9): {sum(1 for r in rows if r[3] < 0.9)}')
