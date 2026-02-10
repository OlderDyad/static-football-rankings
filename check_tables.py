
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        # List tables matching HS_%
        query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'HS_%' ORDER BY TABLE_NAME"
        cursor.execute(query)
        rows = cursor.fetchall()
        print("--- Tables matching HS_% ---")
        for row in rows:
            print(row[0])
            
        # Check specific table HS_Ratings
        query = "SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'HS_Ratings'"
        cursor.execute(query)
        if cursor.fetchone():
            print("\nHS_Ratings table EXISTS.")
            # Get columns
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'HS_Ratings'")
            cols = cursor.fetchall()
            print("Columns in HS_Ratings:", [c[0] for c in cols])
        else:
            print("\nHS_Ratings table does NOT exist.")

except Exception as e:
    print(f"Error: {e}")
