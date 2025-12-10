import pandas as pd
import re
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV = "sk_saskatoon_schedules.csv"
OUTPUT_SQL = "Import_SK_Saskatoon.sql"
SEASON = 2025 

def clean_sk_date(date_str):
    if not isinstance(date_str, str): return None
    # Aggressive cleanup of the date string
    clean = re.sub(r'[^A-Za-z0-9, ]', '', date_str) # Keep only letters, numbers, comma, space
    clean = clean.replace("Wednesday", "").replace("Thursday", "").replace("Friday", "").replace("Tuesday", "")
    clean = clean.replace("Wed", "").replace("Thu", "").replace("Fri", "").replace("Tue", "").strip()
    
    try:
        dt = datetime.strptime(clean, "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return None

def parse_team_and_score(raw_text):
    if not isinstance(raw_text, str): return "", 0

    # 1. NUCLEAR CLEANUP: Remove "ghost" spaces and weird chars
    # We replace multiple spaces with single space, and strip weird chars
    # "H C   -   S r" becomes "H C - S r"
    clean_text = re.sub(r'\s+', ' ', raw_text).strip()
    clean_text = clean_text.replace('ÿ', '')

    # 2. FIND SCORE: Look for digits inside parentheses, allowing for spaces like ( 2 0 )
    score = 0
    # Regex: literal '(', optional space, digits/spaces, optional space, literal ')'
    match = re.search(r'\(\s*([\d\s]+)\s*\)', clean_text)
    
    if match:
        score_str = match.group(1).replace(" ", "") # Turn "2 0" into "20"
        try:
            score = int(score_str)
        except:
            score = 0
    
    # 3. CLEAN NAME: Remove the score part
    name_no_score = re.sub(r'\(\s*[\d\s]+\s*\)', '', clean_text).strip()
    
    # 4. REMOVE JUNK TEXT (Case insensitive)
    # Remove "Sr. Football", "Jr. Football", and the dashes
    name_clean = re.sub(r'(?i)-\s*sr\.?\s*football', '', name_no_score)
    name_clean = re.sub(r'(?i)-\s*jr\.?\s*football', '', name_clean)
    name_clean = re.sub(r'(?i)sr\.?\s*football', '', name_clean)
    name_clean = re.sub(r'(?i)jr\.?\s*football', '', name_clean)
    
    # 5. FIX SPACING IN TEAM NAMES ("H C" -> "Holy Cross")
    # We remove ALL spaces from the name temporarily to check the map
    # e.g. "H C" -> "HC"
    compact_name = name_clean.replace(" ", "").upper()
    
    final_name = name_clean # Fallback
    is_jv = "JR" in compact_name or "JV" in compact_name
    
    # Map based on the COMPACT string
    name_map = {
        "HC": "Holy Cross",
        "STJ": "St. Joseph",
        "STM": "St. Thomas More",
        "BJM": "Bishop James Mahoney",
        "AB": "Aden Bowman",
        "BETH": "Bethlehem",
        "EH": "Evan Hardy",
        "CENT": "Centennial",
        "WM": "Walter Murray",
        "TD": "Tommy Douglas",
        "MG": "Marion Graham",
        "MR": "Mount Royal",
        "BR": "Bedford Road",
        "EDF": "E.D. Feehan",
        "SWC": "Sheldon-Williams",
        "FWJ": "FW Johnson"
    }

    for key, val in name_map.items():
        if compact_name.startswith(key):
            if is_jv:
                final_name = f"{val} JV"
            else:
                final_name = val
            break
            
    return f"{final_name} (SK)", score

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
try:
    df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig')
except:
    df = pd.read_csv(INPUT_CSV, encoding='latin1')

print("\n--- DEBUGGING SCORES ---")
sql_lines = []
sql_lines.append("USE [hs_football_database];")

for index, row in df.iterrows():
    # Parse Date
    raw_date = str(row.get('Date', ''))
    sql_date = clean_sk_date(raw_date)
    
    if not sql_date:
        continue 

    # Parse Teams
    raw_home = str(row.get('Home', ''))
    home, home_score = parse_team_and_score(raw_home)
    
    raw_away = str(row.get('Away', ''))
    away, away_score = parse_team_and_score(raw_away)
    
    # DEBUG PRINT
    print(f"Row {index}: {home} ({home_score}) vs {away} ({away_score})")

    margin = home_score - away_score
    home = home.replace("'", "''")
    away = away.replace("'", "''")

    sql = (
        f"INSERT INTO [HS_Scores] ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added]) "
        f"VALUES (NEWID(), {SEASON}, '{sql_date}', '{home}', '{away}', {home_score}, {away_score}, {margin}, 0, 'SSSAD_Saskatoon', GETDATE());"
    )
    sql_lines.append(sql)

print(f"\nGenerating {OUTPUT_SQL} with {len(sql_lines)} inserts...")
with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"🎉 Success! Open '{OUTPUT_SQL}' in SSMS.")