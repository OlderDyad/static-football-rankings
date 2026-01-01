import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, text

# ==========================================
# CONFIGURATION
# ==========================================
SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'
JSON_KEY_FILE = 'service_account.json'
SHEET_NAME = 'HS Football Data Cleaning'
TAB_NAME = 'Missing_Data'

# ==========================================
# STEP 1: CONNECT TO GOOGLE SHEETS
# ==========================================
print("Connecting to Google Sheets...")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
client = gspread.authorize(creds)

try:
    sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)
except gspread.WorksheetNotFound:
    print(f"Error: Could not find tab '{TAB_NAME}'. Check spelling.")
    exit()

# Get all records
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ==========================================
# STEP 2: FILTER FOR "SYNC" ROWS
# ==========================================
# Normalize headers
df.columns = [c.strip() for c in df.columns]
lower_cols = [c.lower() for c in df.columns]

if 'sync' not in lower_cols:
    print("WARNING: No 'Sync' column found. Please add a column header named 'Sync'.")
    exit()

# Identify columns
id_col_name = next(c for c in df.columns if c.lower() == 'id')
sync_col_name = next(c for c in df.columns if c.lower() == 'sync')

# Filter for rows marked 'x'
rows_to_update = df[df[sync_col_name].astype(str).str.lower().isin(['x', 'yes', 'true', '1'])]

count = len(rows_to_update)
if count == 0:
    print("No rows marked for sync.")
    exit()

print(f"Found {count} rows to update.")

# ==========================================
# STEP 3: UPDATE SQL SERVER (SMART UPDATE)
# ==========================================
print("Connecting to SQL Server...")
connection_string = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver={DRIVER}&trusted_connection=yes"
engine = create_engine(connection_string)

print("Updating database...")
with engine.begin() as conn:
    for index, row in rows_to_update.iterrows():
        
        row_id = row[id_col_name]
        
        # SMART LOGIC:
        # We REMOVED [Team_Name] from the SET clause below.
        # This prevents the Trigger from blocking the update, even if the name in the Sheet 
        # is slightly different from the DB.
        sql_update = text("""
            UPDATE [dbo].[HS_Team_Names]
            SET 
                -- SECTION 1: USER MANAGED FIELDS (Overwrite DB)
                [City] = :city,
                [State] = :state,
                [Mascot] = :mascot,
                [PrimaryColor] = :p_color,
                [SecondaryColor] = :s_color,
                [TertiaryColor] = :t_color,
                [Stadium] = :stadium,        
                [Website] = :website,
                [YearFounded] = :founded,
                [Latitude] = :lat,
                [Longitude] = :long,
                
                -- SECTION 2: SCRIPT MANAGED FIELDS (Preserve DB)
                [LogoURL] = CASE WHEN :logo = '' THEN [LogoURL] ELSE :logo END,
                [School_Logo_URL] = CASE WHEN :school_logo = '' THEN [School_Logo_URL] ELSE :school_logo END,
                [PhotoUrl] = CASE WHEN :photo = '' THEN [PhotoUrl] ELSE :photo END,
                
                [LastUpdated] = GETDATE()
            WHERE [ID] = :id
        """)

        # HELPER: Handle numbers
        def clean_num(val):
            return val if val != '' else None

        # Execute parameters (Note: 'team' is NOT passed)
        conn.execute(sql_update, {
            'city': row['City'],
            'state': row['State'],
            'mascot': row['Mascot'],
            'p_color': row['PrimaryColor'],
            's_color': row['SecondaryColor'],
            't_color': row['TertiaryColor'],
            'stadium': row['Stadium'],
            'website': row['Website'],
            'founded': clean_num(row['YearFounded']),
            'lat': clean_num(row['Latitude']),
            'long': clean_num(row['Longitude']),
            'logo': str(row['LogoURL']),
            'school_logo': str(row['School_Logo_URL']),
            'photo': str(row['PhotoUrl']),
            'id': row_id
        })
        
        # We still print the Team Name from the sheet for your reference
        print(f"Updated ID {row_id}: {row['Team_Name']}")

print("SUCCESS: SQL Database updated.")
