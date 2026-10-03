import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== ALL alias rules where Alias_Name is a bare/short "Central"-type string, any target ===')
cur.execute("""
    SELECT Alias_Name, Standardized_Name, Newspaper_Region, Newspaper_City, Newspaper_State
    FROM HS_Team_Name_Alias
    WHERE Alias_Name IN ('Central', 'Cental', 'Central High', 'Central Hi', 'Knex Central')
       OR Alias_Name LIKE '%Central%'
    ORDER BY Alias_Name, Newspaper_Region
""")
rows = cur.fetchall()
for r in rows:
    print(f'  {r.Alias_Name!r} -> {r.Standardized_Name!r}  (Region={r.Newspaper_Region}, City={r.Newspaper_City}, State={r.Newspaper_State})')

print()
print('=== Same-alias-different-resolution self-join for "Central"-family aliases specifically ===')
cur.execute("""
    SELECT a1.Alias_Name, a1.Standardized_Name AS Resolution_A, a2.Standardized_Name AS Resolution_B,
           a1.Newspaper_Region AS Region_A, a2.Newspaper_Region AS Region_B
    FROM HS_Team_Name_Alias a1
    JOIN HS_Team_Name_Alias a2
      ON a1.Alias_Name = a2.Alias_Name
      AND a1.Standardized_Name <> a2.Standardized_Name
      AND a1.Standardized_Name < a2.Standardized_Name
    WHERE a1.Alias_Name LIKE '%Central%'
    ORDER BY a1.Alias_Name
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  {r.Alias_Name!r}: {r.Resolution_A!r} (Region={r.Region_A}) vs {r.Resolution_B!r} (Region={r.Region_B})')
else:
    print('  None found -- no alias name resolves to two different Standardized_Names.')

print()
print('=== Does any alias rule resolve to Memphis Central (TN)? ===')
cur.execute("""
    SELECT Alias_Name, Standardized_Name, Newspaper_Region, Newspaper_City, Newspaper_State
    FROM HS_Team_Name_Alias
    WHERE Standardized_Name = 'Memphis Central (TN)'
    ORDER BY Newspaper_Region
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'  {r.Alias_Name!r} -> {r.Standardized_Name!r}  (Region={r.Newspaper_Region}, City={r.Newspaper_City}, State={r.Newspaper_State})')
else:
    print('  None found -- Memphis Central has no alias rule pointing to it at all (any bare "Central" mention from a Memphis-area source has nowhere correct to resolve to).')

print()
print('=== Newspaper_Region values that exist in the alias table for Memphis-area papers ===')
cur.execute("""
    SELECT DISTINCT Newspaper_Region, Newspaper_City, Newspaper_State
    FROM HS_Team_Name_Alias
    WHERE Newspaper_City LIKE '%Memphis%' OR Newspaper_Region LIKE '%Memphis%' OR Newspaper_State = 'TN'
    ORDER BY Newspaper_Region
""")
for r in cur.fetchall():
    print(f'  Region={r.Newspaper_Region}, City={r.Newspaper_City}, State={r.Newspaper_State}')
