import pandas as pd
import re
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV = "nb_schedules.csv"
OUTPUT_SQL = "Import_NB_Clean.sql"
SEASON = 2025 

def clean_nb_date(date_str):
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    
    clean_str = date_str.replace('"', '').strip()
    
    # Split "Fri,Oct. 10" -> "Oct. 10"
    parts = clean_str.split(',')
    if len(parts) > 1:
        date_part = parts[1].strip()
    else:
        date_part = clean_str
    
    date_part = date_part.replace('.', '')
    full_date_str = f"{date_part} {SEASON}"
    
    try:
        dt = datetime.strptime(full_date_str, "%b %d %Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return None

def parse_team_and_score(raw_text):
    """
    Input: "Tantramar Regional Titansÿ52"
    Output: ("Tantramar Regional Titans (NB)", 52)
    """
    if not isinstance(raw_text, str):
        return "", 0

    # 1. NUCLEAR CLEANUP: Remove ghost chars immediately
    clean_text = raw_text.replace('ÿ', '').replace('', '').strip()

    # 2. Extract Score using Regex
    # Looks for digits at the very end of the string
    match = re.search(r"^(.*?)[\s\W]*(\d+)$", clean_text)
    
    if match:
        name_clean = match.group(1).strip()
        score = int(match.group(2))
        return f"{name_clean} (NB)", score
    
    # Fallback
    return f"{clean_text} (NB)", 0

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
try:
    # Use 'latin1' to ensure we capture the weird chars so Python can delete them
    df = pd.read_csv(INPUT_CSV, encoding='latin1')
except:
    df = pd.read_csv(INPUT_CSV)

print("Processing New Brunswick data...")
sql_lines = []
sql_lines.append("USE [hs_football_database];")
sql_lines.append(f"-- Import generated for NB Season {SEASON}")

for index, row in df.iterrows():
    raw_date = str(row.get('Date', ''))
    sql_date = clean_nb_date(raw_date)
    
    if not sql_date:
        continue 

    # Parse Teams
    # Note: CSV headers are 'Away Team' and 'Home Team'
    home, home_score = parse_team_and_score(str(row.get('Home Team', '')))
    away, away_score = parse_team_and_score(str(row.get('Away Team', '')))
    
    home = home.replace("'", "''")
    away = away.replace("'", "''")
    
    margin = home_score - away_score

    sql = (
        f"INSERT INTO [HS_Scores] ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added]) "
        f"VALUES (NEWID(), {SEASON}, '{sql_date}', '{home}', '{away}', {home_score}, {away_score}, {margin}, 0, 'GridironNB', GETDATE());"
    )
    sql_lines.append(sql)

print(f"Generating {OUTPUT_SQL} with {len(sql_lines)} inserts...")
with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"🎉 Success! Open '{OUTPUT_SQL}' in SSMS.")