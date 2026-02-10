
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        # 1. Check type (BASE TABLE vs VIEW)
        cursor.execute("SELECT TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Rankings_Combined'")
        row = cursor.fetchone()
        if row:
            print(f"Rankings_Combined Type: {row.TABLE_TYPE}")
        else:
            print("Rankings_Combined not found in TABLES.")

        # 2. Check Bixby 2025 value
        print("\n--- Bixby 2025 in Rankings_Combined ---")
        cursor.execute("SELECT Combined_Rating, Margin, Win_Loss FROM Rankings_Combined WHERE Team = 'Bixby (OK)' AND Season = 2025")
        row = cursor.fetchone()
        if row:
            print(f"Combined_Rating: {row.Combined_Rating}")
            print(f"Margin: {row.Margin}")
            print(f"Win_Loss: {row.Win_Loss}")
        else:
            print("Bixby 2025 not found.")

except Exception as e:
    print(f"Error: {e}")
