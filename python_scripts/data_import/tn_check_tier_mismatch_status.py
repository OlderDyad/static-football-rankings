import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== TierMismatch investigations already registered for TN ===')
cur.execute("""
    SELECT Status, COUNT(*) AS [RowCount]
    FROM HS_Mapping_Investigations
    WHERE State = '(TN)' AND ConflictType = 'TierMismatch'
    GROUP BY Status
    ORDER BY Status
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  {r[0]}: {r[1]}')
else:
    print('  None found.')

print()
print('=== Total TierMismatch investigations across all states (for context) ===')
cur.execute("""
    SELECT State, COUNT(*) AS [RowCount]
    FROM HS_Mapping_Investigations
    WHERE ConflictType = 'TierMismatch'
    GROUP BY State
    ORDER BY [RowCount] DESC
""")
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

print()
print('=== HS_Team_Tier_Classification rows for (TN) teams (nationwide table, TN-tagged) ===')
cur.execute("""
    SELECT Tier, Basis, COUNT(*) AS [RowCount]
    FROM HS_Team_Tier_Classification
    WHERE TeamName LIKE '%(TN)'
    GROUP BY Tier, Basis
    ORDER BY Tier, Basis
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  Tier={r[0]}, Basis={r[1]}: {r[2]}')
else:
    print('  None found -- suggests classify_team_tiers.py has not been run, or no TN team met the Weak/Strong bar.')
