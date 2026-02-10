
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        # 1. Check if table exists
        cursor.execute("SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Rankings_Combined'")
        if not cursor.fetchone():
            print("Rankings_Combined table does NOT exist.")
        else:
            print("Rankings_Combined table EXISTS.")
            
            # 2. Get columns
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Rankings_Combined'")
            cols = [c[0] for c in cursor.fetchall()]
            print(f"Columns: {cols}")
            
            # 3. Sample data (top rating)
            if 'Combined_Rating' in cols:
                print("\n--- Top 3 by Combined_Rating ---")
                cursor.execute("SELECT TOP 3 Team, Season, Combined_Rating FROM Rankings_Combined ORDER BY Combined_Rating DESC")
                for row in cursor.fetchall():
                    print(f"Team: {row.Team}, Season: {row.Season}, Combined_Rating: {row.Combined_Rating}")
            else:
                print("Combined_Rating column not found.")

            # 4. Check Bixby 2025
            print("\n--- Bixby 2025 in Rankings_Combined ---")
            cursor.execute("SELECT * FROM Rankings_Combined WHERE Team = 'Bixby (OK)' AND Season = 2025")
            row = cursor.fetchone()
            if row:
                r_data = dict(zip(cols, row))
                print(f"Combined_Rating: {r_data.get('Combined_Rating')}")
                if 'Rating' in r_data: print(f"Rating: {r_data.get('Rating')}")
            else:
                print("Bixby 2025 not found in Rankings_Combined")

except Exception as e:
    print(f"Error: {e}")
