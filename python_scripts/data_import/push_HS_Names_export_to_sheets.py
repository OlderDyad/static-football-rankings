import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine

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
# STEP 1: FETCH DATA
# ==========================================
print("Connecting to SQL Server...")
connection_string = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver={DRIVER}&trusted_connection=yes"
engine = create_engine(connection_string)

# We explicitly define the order here. This is the order they will appear in Sheets.
sql_query = """
SELECT 
       [ID],
       [Team_Name],
       [City],
       [State],
       [Mascot],
       [PrimaryColor],
       [SecondaryColor],
       [TertiaryColor],
       [Stadium],
       [YearFounded],
       [Website],
       [LogoURL],
       [School_Logo_URL],
       [PhotoUrl],
       [Latitude],
       [Longitude],
       [LastUpdated]
  FROM [hs_football_database].[dbo].[HS_Team_Names]
  WHERE [LogoURL] IS NULL 
     OR [PrimaryColor] IS NULL 
     OR [Website] IS NULL
"""

with engine.connect() as conn:
    df = pd.read_sql(sql_query, conn)

# Clean Data
df = df.fillna('')
df['LastUpdated'] = df['LastUpdated'].astype(str)
df = df.replace('NaT', '')

# --- ADD SYNC COLUMN ---
# Add 'Sync' at the very start
df.insert(0, 'Sync', "")

print(f"Retrieved {len(df)} rows.")

# ==========================================
# STEP 2: PUSH TO SHEETS (WITH HEADERS)
# ==========================================
print("Connecting to Google Sheets...")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)

print("Clearing sheet...")
sheet.clear() # We clear everything to reset headers

print("Uploading headers and data...")
# Update headers and data in one go [Headers] + [Data]
# This ensures Row 1 matches the data perfectly
sheet.update(range_name="A1", values=[df.columns.values.tolist()] + df.values.tolist())

print("SUCCESS: Google Sheet headers and data synchronized.")