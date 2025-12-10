import pandas as pd
import re
import os

# --- CONFIGURATION ---
INPUT_CSV = "mhsaa_schedules.csv"
OUTPUT_SQL = "import_mhsaa_2025.sql"
SEASON = 2025
SOURCE = "MHSAA"

# Function to parse the score string
def parse_score_data(row):
    score_str = str(row['Score']).strip()
    
    # Defaults
    h_score = None
    v_score = None
    ot_flag = 0  # SQL bit/boolean: 0 for False, 1 for True
    
    # Skip empty or "Preview" scores
    if not score_str or score_str.lower() == 'nan' or '-' not in score_str:
        return pd.Series([None, None, 0])

    try:
        # Regex to capture: (Digits) - (Digits) (Optional Text)
        # Example: "21-14 OT" -> Group 1: 21, Group 2: 14, Group 3: OT
        match = re.search(r'(\d+)\s*-\s*(\d+)\s*(.*)', score_str)
        
        if match:
            # Assuming MHSAA format is usually "Home - Visitor" or "Winner - Loser"
            # NOTE: Verify if MHSAA always puts Home score first or Winner score first.
            # Usually scraped tables match the team order (Home - Away).
            val1 = int(match.group(1))
            val2 = int(match.group(2))
            remainder = match.group(3).strip().lower()

            h_score = val1
            v_score = val2
            
            # Check for Overtime indicators in the remainder text
            if 'ot' in remainder or 'overtime' in remainder:
                ot_flag = 1
                
    except Exception as e:
        print(f"Error parsing score '{score_str}': {e}")
        
    return pd.Series([h_score, v_score, ot_flag])

# --- MAIN EXECUTION ---
print(f"Reading {INPUT_CSV}...")
df = pd.read_csv(INPUT_CSV)

# 1. Parse Scores and OT
print("Cleaning scores and detecting Overtime...")
df[['Home_Score', 'Visitor_Score', 'OT']] = df.apply(parse_score_data, axis=1)

# 2. Filter out rows where scores couldn't be determined (e.g., future games)
import_df = df.dropna(subset=['Home_Score', 'Visitor_Score'])

# 3. Format Date for SQL (YYYY-MM-DD)
import_df['SQL_Date'] = pd.to_datetime(import_df['Date/Time'], errors='coerce').dt.strftime('%Y-%m-%d')

print(f"Generating SQL script for {len(import_df)} games...")

# 4. Generate SQL Insert Statements
with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
    f.write(f"-- Auto-generated import script for MHSAA {SEASON}\n")
    f.write("USE [hs_football_database];\n\n")
    
    for index, row in import_df.iterrows():
        # Escape single quotes in team names (e.g., O'Fallon)
        home_team = row['Home'].replace("'", "''")
        visitor_team = row['Away'].replace("'", "''")
        
        sql = (
            "INSERT INTO [HS_Scores] "
            "([Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [OT], [Source], [Date_Added]) "
            f"VALUES ({SEASON}, '{row['SQL_Date']}', '{home_team}', '{visitor_team}', "
            f"{int(row['Home_Score'])}, {int(row['Visitor_Score'])}, {row['OT']}, '{SOURCE}', GETDATE());\n"
        )
        f.write(sql)

print("------------------------------------------------")
print(f"🎉 Success! SQL script created: {os.path.abspath(OUTPUT_SQL)}")
print("Open this file in SSMS and execute it to import your data.")
print("------------------------------------------------")