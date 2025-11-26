import pandas as pd
import pyodbc
import os
from datetime import datetime

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
EXPORT_FOLDER = r"C:\Users\demck\Desktop\HS_Football_Updates"
# ---------------------

def export_data():
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
    conn = pyodbc.connect(conn_str)

    # QUERY: Select columns you want to edit. 
    # CRITICAL: MUST INCLUDE 'ID' FOR THE RETURN TRIP!
    sql_query = """
    SELECT 
        ID, 
        Team_Name, 
        City, 
        State, 
        Mascot, 
        PrimaryColor, 
        SecondaryColor, 
        Website, 
        YearFounded, 
        Latitude, 
        Longitude
    FROM [dbo].[HS_Team_Names]
    WHERE 
        Website IS NULL 
        OR PrimaryColor IS NULL 
        OR Latitude IS NULL
    ORDER BY State, City
    """

    try:
        df = pd.read_sql(sql_query, conn)
        
        # Create folder if not exists
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        
        # Generate filename with timestamp to prevent overwriting
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"Teams_Missing_Data_{timestamp}.csv"
        full_path = os.path.join(EXPORT_FOLDER, filename)

        # Export to CSV (index=False removes the pandas row numbers)
        df.to_csv(full_path, index=False)
        
        print(f"✅ Success! {len(df)} rows exported to:\n{full_path}")
        print("--> Upload this file to Google Sheets to edit.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_data()