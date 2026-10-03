import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== Alias rules where Alias_Name is exactly a bare/short "Central" variant (not a filter on the target) ===')
cur.execute("""
    SELECT Alias_Name, Standardized_Name, Newspaper_Region, Newspaper_City, Newspaper_State
    FROM HS_Team_Name_Alias
    WHERE Alias_Name IN ('Central', 'Cental', 'Central High', 'Central Hi', 'Central High School', 'Centrall')
    ORDER BY Alias_Name, Newspaper_Region
""")
rows = cur.fetchall()
for r in rows:
    print(f'  {r.Alias_Name!r} -> {r.Standardized_Name!r}  (Region={r.Newspaper_Region}, City={r.Newspaper_City}, State={r.Newspaper_State})')
print(f'  ({len(rows)} rows)')

print()
print('=== Same bare alias resolving to two different targets (scoped to the exact bare strings above only) ===')
cur.execute("""
    SELECT a1.Alias_Name, a1.Standardized_Name AS Resolution_A, a2.Standardized_Name AS Resolution_B,
           a1.Newspaper_Region AS Region_A, a2.Newspaper_Region AS Region_B
    FROM HS_Team_Name_Alias a1
    JOIN HS_Team_Name_Alias a2
      ON a1.Alias_Name = a2.Alias_Name
      AND a1.Standardized_Name <> a2.Standardized_Name
      AND a1.Standardized_Name < a2.Standardized_Name
    WHERE a1.Alias_Name IN ('Central', 'Cental', 'Central High', 'Central Hi', 'Central High School', 'Centrall')
    ORDER BY a1.Alias_Name
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  {r.Alias_Name!r}: {r.Resolution_A!r} (Region={r.Region_A}) vs {r.Resolution_B!r} (Region={r.Region_B})')
else:
    print('  None -- these exact bare alias strings never resolve to two different targets.')

print()
print('=== Does bare "Central" alias exist for a Memphis-area newspaper region at all? ===')
cur.execute("""
    SELECT Alias_Name, Standardized_Name, Newspaper_Region, Newspaper_City, Newspaper_State
    FROM HS_Team_Name_Alias
    WHERE Alias_Name = 'Central'
      AND (Newspaper_City LIKE '%Memphis%' OR Newspaper_Region LIKE '%Memphis%' OR Newspaper_Region LIKE '%Commercial Appeal%')
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  {r.Alias_Name!r} -> {r.Standardized_Name!r}  (Region={r.Newspaper_Region})')
else:
    print('  None found.')

print()
print('=== Any alias rule at all naming a Memphis newspaper as its region? ===')
cur.execute("""
    SELECT DISTINCT Newspaper_Region, Newspaper_City, Newspaper_State
    FROM HS_Team_Name_Alias
    WHERE Newspaper_Region LIKE '%Memphis%' OR Newspaper_Region LIKE '%Commercial Appeal%' OR Newspaper_City LIKE '%Memphis%'
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  Region={r.Newspaper_Region}, City={r.Newspaper_City}, State={r.Newspaper_State}')
else:
    print('  None found -- no Memphis newspaper region is registered in the alias table at all.')
