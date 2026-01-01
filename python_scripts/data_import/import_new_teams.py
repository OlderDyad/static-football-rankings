import pandas as pd
from sqlalchemy import create_engine, text

# ==========================================
# CONFIGURATION
# ==========================================
CSV_FILE_PATH = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\New_HS_Team_Names.csv"
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
TABLE_NAME = "HS_Team_Names"

# ==========================================
# STEP 1: LOAD DATA
# ==========================================
print("Connecting to SQL Server...")
connection_string = f"mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
engine = create_engine(connection_string)

print(f"Reading CSV file: {CSV_FILE_PATH}")
try:
    # Read CSV with no header, assigning the column name 'Team_Name' manually
    new_teams_df = pd.read_csv(CSV_FILE_PATH, header=None, names=['Team_Name'])
    
    # Clean up whitespace
    new_teams_df['Team_Name'] = new_teams_df['Team_Name'].astype(str).str.strip()
    
    # Remove empty rows or extremely short names
    new_teams_df = new_teams_df[new_teams_df['Team_Name'].str.len() > 1]
    
    # Remove duplicates inside the CSV itself
    new_teams_df = new_teams_df.drop_duplicates()
    
    print(f"Found {len(new_teams_df)} unique names in CSV.")

except Exception as e:
    print(f"Error reading CSV: {e}")
    exit()

# ==========================================
# STEP 2: DUPLICATE PROTECTION
# ==========================================
print("Checking for existing teams in database...")

with engine.connect() as conn:
    # Pull all current team names to compare against
    existing_teams = pd.read_sql("SELECT Team_Name FROM HS_Team_Names", conn)
    
    # Convert to a set for instant lookup (faster than SQL WHERE checks for thousands of rows)
    existing_set = set(existing_teams['Team_Name'].str.upper())

# Filter the CSV dataframe
# Only keep rows where the UPPERCASE name is NOT in our existing set
teams_to_insert = new_teams_df[~new_teams_df['Team_Name'].str.upper().isin(existing_set)]

count = len(teams_to_insert)

if count == 0:
    print("\nNo new teams to add. All names in the CSV already exist in the database.")
    exit()

print(f"\nIdentified {count} NEW teams to insert.")
print(f"Skipped {len(new_teams_df) - count} duplicates.")

# ==========================================
# STEP 3: INSERT NEW TEAMS
# ==========================================
confirm = input(f"Ready to insert {count} rows into {TABLE_NAME}? (y/n): ")
if confirm.lower() != 'y':
    print("Operation cancelled.")
    exit()

print("Inserting rows...")

# We use 'append' to add to the existing table
# The trigger we added earlier ONLY blocks Deletes/Updates, so Inserts are safe.
try:
    teams_to_insert.to_sql(TABLE_NAME, engine, if_exists='append', index=False)
    print("SUCCESS: Teams imported successfully.")
except Exception as e:
    print(f"Error during insert: {e}")
    print("NOTE: If you have a UNIQUE constraint on the SQL column, a remaining duplicate might have caused this.")