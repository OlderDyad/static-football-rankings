import argparse
import csv
import pyodbc

parser = argparse.ArgumentParser()
parser.add_argument('--commit', action='store_true', help='Actually insert rows. Without this flag, runs as a dry-run preview only.')
args = parser.parse_args()

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

rows = []
with open('confident_url_backfill.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append((int(r['Team_ID']), r['Team_Name'], r['MaxPrepsURL']))

print(f'Loaded {len(rows)} candidate rows from confident_url_backfill.csv')

to_insert = []
skipped_already_mapped = []
skipped_url_taken = []

for team_id, team_name, base_url in rows:
    full_url = base_url.rstrip('/') + '/schedule/'

    cur.execute("SELECT 1 FROM dbo.URL_ProperName_Mapping WHERE Team_ID = ?", team_id)
    if cur.fetchone():
        skipped_already_mapped.append((team_id, team_name))
        continue

    cur.execute("SELECT ProperName, Team_ID FROM dbo.URL_ProperName_Mapping WHERE URL = ?", full_url)
    existing = cur.fetchone()
    if existing:
        skipped_url_taken.append((team_id, team_name, full_url, existing.ProperName, existing.Team_ID))
        continue

    to_insert.append((full_url, team_name, team_id))

print()
print(f'Safe to insert: {len(to_insert)}')
print(f'Skipped -- team_id already has a mapping (race condition since sizing?): {len(skipped_already_mapped)}')
print(f'Skipped -- URL already mapped to a DIFFERENT team_id (needs investigation): {len(skipped_url_taken)}')

if skipped_url_taken:
    print()
    print('=== URL-already-taken conflicts (not inserted, needs a look) ===')
    for row in skipped_url_taken[:20]:
        print(f'  team_id={row[0]} {row[1]}  wants {row[2]}  but it is already mapped to team_id={row[4]} ({row[3]})')

print()
print('=== Sample of what will be inserted ===')
for row in to_insert[:10]:
    print(f'  INSERT URL_ProperName_Mapping (URL, ProperName, Team_ID) VALUES ({row[0]!r}, {row[1]!r}, {row[2]})')

if args.commit:
    print()
    print(f'--commit passed: inserting {len(to_insert)} rows now...')
    cur.executemany(
        "INSERT INTO dbo.URL_ProperName_Mapping (URL, ProperName, Team_ID) VALUES (?, ?, ?)",
        to_insert
    )
    conn.commit()
    print('Done. Committed.')
else:
    print()
    print('DRY RUN ONLY -- no rows inserted. Re-run with --commit to actually apply.')

conn.close()
