
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        query = "sp_helptext 'Get_Media_National_Champions'"
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"--- Definition of Get_Media_National_Champions ---")
        for row in rows:
            print(row[0], end='')
        print("\n--- End of Definition ---")
except Exception as e:
    print(f"Error: {e}")
