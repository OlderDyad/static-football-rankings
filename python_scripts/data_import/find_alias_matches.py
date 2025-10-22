import pandas as pd
import pyodbc
from fuzzywuzzy import process
import os

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
CORRECTION_CSV = os.path.join(STAGING_DIRECTORY, 'Alias_Correction_Sheet.csv')
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"

print("--- Starting Advanced Alias Search Script (Python Version) ---")

# Database connection
try:
    cnxn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;')
    print(f"Successfully connected to database '{DATABASE_NAME}' on server '{SERVER_NAME}'.")
except Exception as e:
    print(f"FATAL: Could not connect to database: {e}")
    exit(1)

# Load all team names from database
query = """
SELECT DISTINCT Team_Name, City, State 
FROM HS_Team_Names 
WHERE Team_Name IS NOT NULL AND Team_Name != ''
ORDER BY Team_Name
"""

try:
    all_teams_df = pd.read_sql(query, cnxn)
    print(f"Successfully retrieved {len(all_teams_df)} team names from the database.")
except Exception as e:
    print(f"FATAL: Could not retrieve team names: {e}")
    cnxn.close()
    exit(1)

# Check if correction sheet exists
if not os.path.exists(CORRECTION_CSV):
    print(f"No correction sheet found at: {CORRECTION_CSV}")
    print("Nothing to process.")
    cnxn.close()
    exit(0)

# Load correction sheet
try:
    correction_df = pd.read_csv(CORRECTION_CSV)
    print(f"Loaded correction sheet with {len(correction_df)} total rows.")
except Exception as e:
    print(f"FATAL: Could not load correction sheet: {e}")
    cnxn.close()
    exit(1)

# FIXED LOGIC: Only process rows where Final_Proper_Name is actually empty
if 'Final_Proper_Name' not in correction_df.columns:
    print("FATAL: 'Final_Proper_Name' column not found in correction sheet.")
    cnxn.close()
    exit(1)

# Filter for truly empty Final_Proper_Name values
empty_mask = (
    correction_df['Final_Proper_Name'].isna() | 
    (correction_df['Final_Proper_Name'].astype(str).str.strip() == '') |
    (correction_df['Final_Proper_Name'].astype(str) == 'nan')
)

aliases_to_process = correction_df[empty_mask]

print(f"Found {len(aliases_to_process)} aliases needing proper names (empty Final_Proper_Name).")

if len(aliases_to_process) == 0:
    print("All aliases already have Final_Proper_Name filled in. Nothing to process.")
    cnxn.close()
    exit(0)

# Show which ones we're processing
print("Processing the following aliases:")
for _, row in aliases_to_process.iterrows():
    print(f"  - '{row['Unrecognized_Alias']}' (Region: {row['Newspaper_Region']})")

# Create list of all team names for fuzzy matching
all_team_names = all_teams_df['Team_Name'].tolist()

# Generate report
report_lines = []

for _, alias_row in aliases_to_process.iterrows():
    alias_name = alias_row['Unrecognized_Alias']
    region = alias_row['Newspaper_Region']
    
    report_lines.append("=" * 70)
    report_lines.append(f"Searching for Alias: '{alias_name}' (Region: {region})")
    report_lines.append("=" * 70)
    
    # Get fuzzy matches
    matches = process.extract(alias_name, all_team_names, limit=5)
    
    if matches:
        report_lines.append("Found the following top 5 matches (lower score is better):")
        
        # Create a mini dataframe for nice formatting
        match_data = []
        for match_name, score in matches:
            # Find the corresponding row for city/state info
            team_info = all_teams_df[all_teams_df['Team_Name'] == match_name].iloc[0]
            match_data.append({
                'score': 100 - score,  # Convert to distance score (lower is better)
                'Team_Name': match_name,
                'City': team_info['City'] if pd.notna(team_info['City']) else 'None',
                'State': team_info['State'] if pd.notna(team_info['State']) else 'None'
            })
        
        match_df = pd.DataFrame(match_data)
        report_lines.append(match_df.to_string(index=False))
    else:
        report_lines.append("No close matches found.")
    
    report_lines.append("")

# Save report
report_content = "\n".join(report_lines)
with open("Alias_Match_Report.txt", "w", encoding="utf-8") as f:
    f.write(report_content)

cnxn.close()
print("--- Script Complete. ---")
print("Report saved to: Alias_Match_Report.txt")

if len(aliases_to_process) > 0:
    print(f"\nNext steps:")
    print(f"1. Review the report and choose proper names for the {len(aliases_to_process)} unmatched aliases")
    print(f"2. Fill in the 'Final_Proper_Name' column in: {CORRECTION_CSV}")
    print(f"3. Run apply_corrections.py to add the aliases to the database")
else:
    print("\nAll aliases are complete! You can proceed with master_scores_importer.py")