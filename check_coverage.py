
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        # 1. Range of seasons in HS_Rankings
        cursor.execute("SELECT MIN(Season), MAX(Season), COUNT(*) FROM HS_Rankings")
        row = cursor.fetchone()
        print(f"HS_Rankings Range: {row[0]} to {row[1]} (Count: {row[2]})")
        
        # 2. Check Media Champions range
        cursor.execute("SELECT MIN(Season), MAX(Season), COUNT(*) FROM Media_National_Champions")
        row = cursor.fetchone()
        print(f"Media_Champions Range: {row[0]} to {row[1]} (Count: {row[2]})")
        
        # 3. Check Join coverage
        cursor.execute("""
            SELECT 
                COUNT(*) AS Total,
                SUM(CASE WHEN r.Home IS NOT NULL THEN 1 ELSE 0 END) AS Matched,
                SUM(CASE WHEN r.Home IS NULL THEN 1 ELSE 0 END) AS Unmatched
            FROM Media_National_Champions m
            LEFT JOIN HS_Rankings r ON m.Team_Name = r.Home AND m.Season = r.Season AND r.Week = 52
        """)
        row = cursor.fetchone()
        print(f"Join Coverage - Total: {row.Total}, Matched: {row.Matched}, Unmatched: {row.Unmatched}")

except Exception as e:
    print(f"Error: {e}")
