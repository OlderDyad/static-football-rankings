
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        query = "SELECT OBJECT_DEFINITION(OBJECT_ID('Rankings_Combined'))"
        cursor.execute(query)
        row = cursor.fetchone()
        if row:
            with open("view_def.sql", "w", encoding="utf-8") as f:
                f.write(row[0])
            print("Successfully wrote view_def.sql")
        else:
            print("View not found or output empty.")
except Exception as e:
    print(f"Error: {e}")
