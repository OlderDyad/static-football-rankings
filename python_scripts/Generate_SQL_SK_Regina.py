import pandas as pd
import re
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV = "sk_regina_schedules.csv" # Updated to match your filename
OUTPUT_SQL = "Import_SK_Regina.sql"
SEASON = 2025 

def clean_regina_date(date_str):
    """
    Parses: "August 29 2025" or "Aug 29 2025"
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    
    clean_str = date_str.strip()

    # List of formats to try based on your sample data
    formats = [
        "%B %d %Y",     # "August 29 2025"
        "%b %d %Y",     # "Aug 29 2025"
        "%B %d, %Y",    # "August 29, 2025" (Just in case)
        "%Y-%m-%d"      # ISO
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(clean_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            continue
    return None

def parse_team_and_score(raw_text):
    """
    Input: "WKC (35)"
    Output: ("WKC (SK)", 35)
    """
    if not isinstance(raw_text, str):
        return "", 0

    clean_text = raw_text.strip()

    # 1. Extract Score
    score = 0
    match = re.search(r'\((\d+)\)', clean_text)
    if match:
        score = int(match.group(1))
    
    # 2. Clean Name (Remove "(35)")
    name_no_score = re.sub(r'\(\d+\)', '', clean_text).strip()
    
    # 3. Add Suffix
    final_name = f"{name_no_score} (SK)"
    
    return final_name, score

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
try:
    # utf-8-sig handles the Byte Order Mark if Excel added one
    df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig')
except:
    df = pd.read_csv(INPUT_CSV, encoding='latin1')

print("Processing Regina data...")
sql_lines = []
sql_lines.append("USE [hs_football_database];")
sql_lines.append(f"-- Import generated for SK Regina Season {SEASON}")

for index, row in df.iterrows():
    # 1. Date
    raw_date = str(row.get('Date', ''))
    sql_date = clean_regina_date(raw_date)
    
    if not sql_date:
        continue 

    # 2. Parse Home
    raw_home = str(row.get('Home', ''))
    home_team, home_score = parse_team_and_score(raw_home)
    home = home_team.replace("'", "''")

    # 3. Parse Away
    raw_away = str(row.get('Away', ''))
    away_team, away_score = parse_team_and_score(raw_away)
    away = away_team.replace("'", "''")
    
    # 4. Margin
    margin = home_score - away_score

    # 5. Generate SQL
    sql = (
        f"INSERT INTO [HS_Scores] ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added]) "
        f"VALUES (NEWID(), {SEASON}, '{sql_date}', '{home}', '{away}', {home_score}, {away_score}, {margin}, 0, 'RHSAA_Regina', GETDATE());"
    )
    sql_lines.append(sql)

print(f"Generating {OUTPUT_SQL} with {len(sql_lines)} inserts...")
with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"🎉 Success! Open '{OUTPUT_SQL}' in SSMS.")