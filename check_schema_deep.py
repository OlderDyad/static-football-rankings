
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        # 1. List all columns in HS_Rankings
        print("--- Columns in HS_Rankings ---")
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'HS_Rankings'")
        cols = cursor.fetchall()
        for c in cols:
            print(c[0])
            
        # 2. Check views
        print("\n--- Views matching HS_% ---")
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME LIKE 'HS_%'")
        views = cursor.fetchall()
        for v in views:
            print(v[0])
            
        # 3. Check for any table/view named *Ratings*
        print("\n--- Tables/Views matching %Ratings% ---")
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%Ratings%'")
        objs = cursor.fetchall()
        for o in objs:
            print(o[0])

except Exception as e:
    print(f"Error: {e}")
