import pandas as pd
import re
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV = "mhsaa_schedules.csv"
OUTPUT_SQL = "Import_MHSAA_Clean.sql"
SEASON = 2025 

def clean_date(date_str):
    """
    Converts strings like "11/8-12:00 PM" or "OCTOBER 3" into "2025-11-08"
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    
    clean_str = date_str.split('-')[0].strip()
    clean_str = f"{clean_str} {SEASON}"
    
    try:
        dt = datetime.strptime(clean_str, "%m/%d %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
        
    try:
        dt = datetime.strptime(clean_str, "%B %d %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    return None 

def parse_score(score_str):
    if not isinstance(score_str, str) or '-' not in score_str:
        return None, None, 0
    
    try:
        match = re.search(r'(\d+)\s*-\s*(\d+)\s*(.*)', score_str)
        if match:
            h_score = int(match.group(1))
            v_score = int(match.group(2))
            remainder = match.group(3).lower()
            ot = 1 if 'ot' in remainder or 'overtime' in remainder else 0
            return h_score, v_score, ot
    except:
        pass
    return None, None, 0

def add_state_suffix(team_name):
    """
    Appends ' (MI)' to the team name unless it already has a state code like (OH), (PA), (CN).
    """
    if not isinstance(team_name, str) or not team_name.strip():
        return team_name
    
    # Check if team already ends with (XX) where XX are 2 uppercase letters
    if re.search(r'\([A-Z]{2}\)$', team_name.strip()):
        return team_name # Return as-is (Out of state)
    
    # Otherwise, append Michigan suffix
    return f"{team_name.strip()} (MI)"

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
df = pd.read_csv(INPUT_CSV)

print("Processing dates, scores, and team names...")
sql_lines = []

# --- SQL HEADER ---
sql_lines.append("USE [hs_football_database];")
sql_lines.append(f"-- Import generated for MHSAA Season {SEASON}")
# REMOVED: @NextID logic (Not compatible with GUIDs)

for index, row in df.iterrows():
    raw_date = str(row.get('Date/Time', ''))
    sql_date = clean_date(raw_date)
    
    if not sql_date:
        continue 

    raw_home = str(row.get('Home', ''))
    raw_away = str(row.get('Away', ''))
    
    home_fixed = add_state_suffix(raw_home)
    away_fixed = add_state_suffix(raw_away)
    
    home = home_fixed.replace("'", "''")
    away = away_fixed.replace("'", "''")
    
    h_score, v_score, ot = parse_score(str(row.get('Score', '')))
    
    if h_score is None:
        continue 

    # --- INSERT STATEMENT WITH NEWID() ---
    # We use NEWID() to generate the uniqueidentifier for [ID]
    sql = (
        f"INSERT INTO [HS_Scores] ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [OT], [Source], [Date_Added]) "
        f"VALUES (NEWID(), {SEASON}, '{sql_date}', '{home}', '{away}', {h_score}, {v_score}, {ot}, 'MHSAA', GETDATE());"
    )
    sql_lines.append(sql)

print(f"Generating {OUTPUT_SQL} with {len(sql_lines)} inserts...")
with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"🎉 Success! Open '{OUTPUT_SQL}' in SSMS and execute it.")