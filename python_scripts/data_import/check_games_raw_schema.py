import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== games_raw schema (need the exact PK/identity column name) ===')
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'games_raw'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f'  {r.COLUMN_NAME}  {r.DATA_TYPE}  NULLABLE={r.IS_NULLABLE}')

print()
print('=== Does Unmatched_Opponents already have a RawGameID column? ===')
cur.execute("""
    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Unmatched_Opponents'
""")
cols = [r.COLUMN_NAME for r in cur.fetchall()]
print(f'  Existing columns: {cols}')
print(f'  Has RawGameID already: {"RawGameID" in cols}')

print()
print('=== Current Unmatched_Opponents row count (any prior use, e.g. past-season reimports) ===')
cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.Unmatched_Opponents")
print(f'  {cur.fetchone().RowCount} rows')

conn.close()
