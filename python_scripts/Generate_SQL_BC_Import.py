import pandas as pd
from datetime import datetime
import re

# --- CONFIGURATION ---
INPUT_CSV = "bc_schedules.csv"
OUTPUT_SQL = "Import_BC_Clean.sql"
SEASON = 2025 

def clean_bc_date(date_str):
    """
    Robust date parser for BC schedules.
    Expected raw format examples:
    - "Thu Aug 28, 2025"
    - "Filter\nThu Aug 28, 2025"
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    
    # 1. Regex to extract purely the date part: "Aug 28, 2025" or "August 28, 2025"
    # Looks for: Month Name + Space + Digits + Comma? + Space + 4 Digits
    match = re.search(r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', date_str)
    
    if match:
        clean_str = f"{match.group(1)} {match.group(2)} {match.group(3)}"
        try:
            # Try "Aug 28 2025"
            dt = datetime.strptime(clean_str, "%b %d %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try "August 28 2025"
                dt = datetime.strptime(clean_str, "%B %d %Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
    
    return None

def clean_team_name(team_str):
    if not isinstance(team_str, str) or not team_str.strip():
        return ""
    name = team_str.split('\n')[0].strip()
    return f"{name} (BC)"

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
df = pd.read_csv(INPUT_CSV)
print(f"Found {len(df)} rows. Processing...")

sql_lines = []
sql_lines.append("USE [hs_football_database];")
sql_lines.append(f"-- Import generated for BC Season {SEASON}")

skipped = 0

for index, row in df.iterrows():
    # 1. Parse Date
    raw_date = str(row.get('Date', ''))
    sql_date = clean_bc_date(raw_date)
    
    if not sql_date:
        skipped += 1
        continue 

    # 2. Parse Teams
    home = clean_team_name(str(row.get('Home', ''))).replace("'", "''")
    away = clean_team_name(str(row.get('Away', ''))).replace("'", "''")
    
    # 3. Parse Scores
    try:
        h_score = int(row.get('Home_Score', 0))
        v_score = int(row.get('Away_Score', 0))
        margin = h_score - v_score
    except:
        h_score = 0
        v_score = 0
        margin = 0

    # 4. Generate SQL
    sql = (
        f"INSERT INTO [HS_Scores] ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added]) "
        f"VALUES (NEWID(), {SEASON}, '{sql_date}', '{home}', '{away}', {h_score}, {v_score}, {margin}, 0, 'BC_HS_Football', GETDATE());"
    )
    sql_lines.append(sql)

print(f"Generating {OUTPUT_SQL} with {len(sql_lines)} inserts...")
if skipped > 0:
    print(f"⚠️ Warning: Skipped {skipped} rows due to unreadable dates.")

with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"🎉 Success! Open '{OUTPUT_SQL}' in SSMS and execute it.")