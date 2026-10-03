import csv
import pyodbc
import re

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', s.lower())

print('=== Testing the duplicate-team-record theory across ALL 709 "confident" rows ===')
rows = []
with open('confident_url_backfill.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        rows.append((int(r['Team_ID']), r['Team_Name'], r['MaxPrepsURL']))

is_duplicate = 0
truly_new = 0
dup_examples = []
new_examples = []

for team_id, team_name, base_url in rows:
    full_url = base_url.rstrip('/') + '/schedule/'
    cur.execute("SELECT ProperName, Team_ID FROM dbo.URL_ProperName_Mapping WHERE URL = ?", full_url)
    existing = cur.fetchone()
    if existing:
        is_duplicate += 1
        if len(dup_examples) < 5:
            dup_examples.append((team_id, team_name, existing.Team_ID, existing.ProperName))
    else:
        truly_new += 1
        if len(new_examples) < 5:
            new_examples.append((team_id, team_name, full_url))

print(f'  Duplicate of an already-mapped team_id: {is_duplicate} / {len(rows)}')
print(f'  Genuinely new/unmapped team_id:         {truly_new} / {len(rows)}')

print()
print('=== Same test against the 264 "needs manual review" bucket ===')
review_rows = []
with open('needs_manual_review.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        review_rows.append((int(r['Team_ID']), r['Team_Name'], r['CandidateURLs']))

review_dup = 0
review_new = 0
for team_id, team_name, cand_urls in review_rows:
    found_dup = False
    for u in cand_urls.split('; '):
        full_url = u.rstrip('/') + '/schedule/'
        cur.execute("SELECT 1 FROM dbo.URL_ProperName_Mapping WHERE URL = ?", full_url)
        if cur.fetchone():
            found_dup = True
            break
    if found_dup:
        review_dup += 1
    else:
        review_new += 1

print(f'  At least one candidate URL already mapped elsewhere: {review_dup} / {len(review_rows)}')
print(f'  No candidate URL mapped anywhere (genuinely unknown): {review_new} / {len(review_rows)}')

print()
print('=== Are the duplicate pairs true duplicates (near-identical normalized names)? Spot check ===')
sample_pairs = []
for team_id, team_name, base_url in rows[:50]:
    full_url = base_url.rstrip('/') + '/schedule/'
    cur.execute("SELECT ProperName, Team_ID FROM dbo.URL_ProperName_Mapping WHERE URL = ?", full_url)
    existing = cur.fetchone()
    if existing:
        same_normalized = norm(team_name) == norm(existing.ProperName)
        sample_pairs.append((team_id, team_name, existing.Team_ID, existing.ProperName, same_normalized))

exact_after_norm = sum(1 for p in sample_pairs if p[4])
print(f'  Of first 50: {exact_after_norm} match exactly after stripping punctuation/spacing, {len(sample_pairs)-exact_after_norm} differ more than that')
for p in sample_pairs:
    if not p[4]:
        print(f'    DIFFERS: team_id={p[0]} "{p[1]}"  vs  team_id={p[2]} "{p[3]}"')

conn.close()
