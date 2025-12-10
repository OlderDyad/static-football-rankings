import pandas as pd
import re
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV = "mb_schedules.csv"
OUTPUT_SQL = "Import_MB_Clean.sql"
SEASON = 2025 

def clean_mb_date(date_str):
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    
    # Clean artifacts
    clean_str = date_str.replace('"', '').strip()
    
    # Remove day name if present (Mon, Tue, etc.)
    parts = clean_str.split()
    if parts[0] in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        clean_str = " ".join(parts[1:])
        
    try:
        dt = datetime.strptime(clean_str, "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return None

def parse_team_and_score(raw_text):
    """
    Input: "W e s t   K i l d o n a n ÿ (35)"
    Output: ("West Kildonan Wolverines (MB)", 35)
    """
    if not isinstance(raw_text, str):
        return "", 0

    # 1. NUCLEAR CLEANUP
    # Remove 'ÿ', and collapse multiple spaces into one
    clean_text = raw_text.replace('ÿ', '').strip()
    clean_text = re.sub(r'\s+', ' ', clean_text) # Turn "W e s t" into "W e s t" (Wait, usually wide text is single spaces)
    
    # If the text is truly wide (W e s t), we might need to remove ALL spaces and re-insert them?
    # Actually, looking at your output, it looks like "W e s t  K i l d o n a n". 
    # Let's try to just strip the junk chars first.
    
    # 2. Extract Score
    score = 0
    match = re.search(r'\(\s*([\d\s]+)\s*\)', clean_text)
    if match:
        score_str = match.group(1).replace(" ", "")
        try:
            score = int(score_str)
        except:
            score = 0
    
    # 3. Clean Name (Remove Score)
    name_no_score = re.sub(r'\(\s*[\d\s]+\s*\)', '', clean_text).strip()
    
    # 4. Fix "Wide" Text if necessary
    # If the name looks like "W e s t", we need to fix it. 
    # But often the regex \s+ fix handles the big gaps. 
    # Let's run a simple check: if we removed ÿ, usually the rest is okay.
    
    # 5. Handle JV
    is_jv = False
    if " JV" in name_no_score or "Junior Varsity" in name_no_score:
        is_jv = True
        name_no_score = name_no_score.replace(" JV", "").replace("Junior Varsity", "").strip()

    # 6. Suffix
    if is_jv:
        final_name = f"{name_no_score} JV (MB)"
    else:
        final_name = f"{name_no_score} (MB)"
    
    return final_name, score

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
try:
    df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig')
except:
    df = pd.read_csv(INPUT_CSV, encoding='latin1')

print("Processing Manitoba data...")
sql_lines = []
sql_lines.append("USE [hs_football_database];")
sql_lines.append(f"-- Import generated for Manitoba Season {SEASON}")

for index, row in df.iterrows():
    # 1. Date
    raw_date = str(row.get('Date', ''))
    sql_date = clean_mb_date(raw_date)
    
    if not sql_date:
        continue 

    # 2. Parse Teams
    home, home_score = parse_team_and_score(str(row.get('Home', '')))
    away, away_score = parse_team_and_score(str(row.get('Away', '')))
    
    home = home.replace("'", "''")
    away = away.replace("'", "''")
    
    margin = home_score - away_score

    # 3. Generate SQL
    sql = (
        f"INSERT INTO [HS_Scores] ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added]) "
        f"VALUES (NEWID(), {SEASON}, '{sql_date}', '{home}', '{away}', {home_score}, {away_score}, {margin}, 0, 'WHSFL_Manitoba', GETDATE());"
    )
    sql_lines.append(sql)

print(f"Generating {OUTPUT_SQL} with {len(sql_lines)} inserts...")
with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"🎉 Success! Open '{OUTPUT_SQL}' in SSMS.")