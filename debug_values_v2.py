
import pyodbc

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

output_lines = []

try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        # 1. Get Coefficients
        cursor.execute("SELECT TOP 1 Avg_Adjusted_Margin_Coef, Power_Ranking_Coef_Win_Loss, Power_Ranking_Coef FROM Coefficients ORDER BY ID DESC")
        coefs = cursor.fetchone()
        output_lines.append("--- Coefficients ---")
        if coefs:
            output_lines.append(f"Avg_Adjusted_Margin_Coef: {coefs[0]}")
            output_lines.append(f"Power_Ranking_Coef_Win_Loss: {coefs[1]}")
            output_lines.append(f"Power_Ranking_Coef: {coefs[2]}")
        else:
            output_lines.append("No coefficients found!")

        # 2. Get top 1 Media Champion
        output_lines.append("\n--- Top 1 Media Champion (SP Result) ---")
        cursor.execute("EXEC Get_Media_National_Champions")
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
        
        if row:
            data = dict(zip(cols, row))
            for k, v in data.items():
                output_lines.append(f"{k}: {v}")
            
            # Drill down into HS_Rankings
            team = data.get('team')
            year = data.get('year')
            output_lines.append(f"\n--- Checking HS_Rankings for {team} ({year}, Week 52) ---")
            query = "SELECT * FROM HS_Rankings WHERE Home = ? AND Season = ? AND Week = 52"
            cursor.execute(query, (team, year))
            rank_row = cursor.fetchone()
            if rank_row:
                rank_cols = [c[0] for c in cursor.description]
                rank_data = dict(zip(rank_cols, rank_row))
                for k, v in rank_data.items():
                    output_lines.append(f"{k}: {v}")
            else:
                output_lines.append("No data in HS_Rankings for this team/year/week=52")
        else:
            output_lines.append("No rows returned by Get_Media_National_Champions")

except Exception as e:
    output_lines.append(f"Error: {e}")

with open("debug_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))
    print("Logged to debug_output.txt")
