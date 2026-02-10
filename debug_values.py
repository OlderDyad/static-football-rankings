
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        # 1. Get Coefficients
        cursor.execute("SELECT TOP 1 Avg_Adjusted_Margin_Coef, Power_Ranking_Coef_Win_Loss, Power_Ranking_Coef FROM Coefficients ORDER BY ID DESC")
        coefs = cursor.fetchone()
        print("--- Coefficients ---")
        if coefs:
            print(f"Avg_Adjusted_Margin_Coef: {coefs[0]}")
            print(f"Power_Ranking_Coef_Win_Loss: {coefs[1]}")
            print(f"Power_Ranking_Coef: {coefs[2]}")
        else:
            print("No coefficients found!")

        # 2. Get top 5 Media Champions to see the "Combined" value
        print("\n--- Top 5 Media Champions (SP Result) ---")
        cursor.execute("EXEC Get_Media_National_Champions")
        cols = [c[0] for c in cursor.description]
        print(f"Columns: {cols}")
        rows = cursor.fetchmany(5)
        for row in rows:
            # zip cols and row
            data = dict(zip(cols, row))
            print(f"Year: {data.get('year')}, Team: {data.get('team')}, Combined: {data.get('combined')}")
            
            # For the first one, let's drill down into HS_Rankings
            if row == rows[0]:
                team = data.get('team')
                year = data.get('year')
                print(f"\n--- Checking HS_Rankings for {team} ({year}) ---")
                query = "SELECT * FROM HS_Rankings WHERE Home = ? AND Season = ? AND Week = 52"
                cursor.execute(query, (team, year))
                rank_row = cursor.fetchone()
                if rank_row:
                    rank_cols = [c[0] for c in cursor.description]
                    rank_data = dict(zip(rank_cols, rank_row))
                    print(f"Avg_Of_Avg_Of_Home_Modified_Score: {rank_data.get('Avg_Of_Avg_Of_Home_Modified_Score')}")
                    print(f"Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss: {rank_data.get('Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss')}")
                    print(f"Avg_Of_Avg_Of_Home_Modified_Log_Score: {rank_data.get('Avg_Of_Avg_Of_Home_Modified_Log_Score')}")
                else:
                    print("No data in HS_Rankings for this team/year/week=52")

except Exception as e:
    print(f"Error: {e}")
