import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV = "ab_schedules.csv"
OUTPUT_SQL = "Import_AB_Clean.sql"
SEASON = 2025 

def clean_ab_date(date_str):
    """
    Parses '22-Aug-25' -> '2025-08-22'
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    
    try:
        # Format: DD-Mon-YY (e.g., 22-Aug-25)
        dt = datetime.strptime(date_str.strip(), "%d-%b-%y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    return None

def clean_team_name(team_str):
    """
    Adds (AB) suffix
    """
    if not isinstance(team_str, str) or not team_str.strip():
        return ""
    name = team_str.strip()
    return f"{name} (AB)"

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
df = pd.read_csv(INPUT_CSV)

print("Processing Alberta data...")
sql_lines = []

sql_lines.append("USE [hs_football_database];")
sql_lines.append(f"-- Import generated for Alberta Season {SEASON}")

for index, row in df.iterrows():
    # 1. Clean Date
    raw_date = str(row.get('Date', ''))
    sql_date = clean_ab_date(raw_date)
    
    if not sql_date:
        continue 

    # 2. Clean Teams
    home = clean_team_name(str(row.get('Home', ''))).replace("'", "''")
    away = clean_team_name(str(row.get('Away', ''))).replace("'", "''")
    
    # 3. Clean Scores (Handle 'DNP' or empty)
    try:
        h_raw = row.get('Home_Score', 0)
        v_raw = row.get('Away_Score', 0)
        
        # If score is DNP or non-numeric, treat as 0
        if str(h_raw).upper() == 'DNP' or str(v_raw).upper() == 'DNP':
            h_score = 0
            v_score = 0
        else:
            h_score = int(h_raw)
            v_score = int(v_raw)
            
        margin = h_score - v_score
    except:
        h_score = 0
        v_score = 0
        margin = 0

    # 4. Generate SQL
    # Source is explicitly set to the website URL as requested
    sql = (
        f"INSERT INTO [HS_Scores] ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added]) "
        f"VALUES (NEWID(), {SEASON}, '{sql_date}', '{home}', '{away}', {h_score}, {v_score}, {margin}, 0, 'www.footballalberta.ab.ca', GETDATE());"
    )
    sql_lines.append(sql)

print(f"Generating {OUTPUT_SQL} with {len(sql_lines)} inserts...")
with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"🎉 Success! Open '{OUTPUT_SQL}' in SSMS and execute it.")