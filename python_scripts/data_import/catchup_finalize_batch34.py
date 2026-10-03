import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = 2026")
before = cur.fetchone().RowCount
print(f'Before: {before} 2026 MaxPreps rows in HS_Scores')

cur.execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = 34")
conn.commit()
print('Ran FinalizeMaxPrepsData for batch 34.')

cur.execute("SELECT COUNT(*) AS [RowCount] FROM dbo.HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = 2026")
after = cur.fetchone().RowCount
print(f'After: {after} 2026 MaxPreps rows in HS_Scores  (+{after - before})')

conn.close()
