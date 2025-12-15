"""
LoneStar Excel to SQL Importer (Python)
Reads directly from Excel workbook, converts formats, imports to staging table
"""

import pandas as pd
import pyodbc
from datetime import datetime
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

EXCEL_PATH = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HSF Texas 2025.xlsx"
SHEET_NAME = "Lonestar"
SERVER_NAME = r"McKnights-PC\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"

# Column mapping - Excel columns AA through AM plus AO (Forfeit)
# We'll read: Date, Season, Visitor, Visitor_Score, Home, Home_Score, Margin, Neutral, Location, Location2, Source, Forfeit
# Skipping: Line (AK), Future_Game (AL), OT (AN)
# Reading columns: AA, AB, AC, AD, AE, AF, AG, AH, AI, AJ, AM, AO
EXCEL_COLUMNS_TO_READ = [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 38, 40]  # 0-based indices
COLUMN_NAMES = ['Date', 'Season', 'Visitor', 'Visitor_Score', 'Home', 'Home_Score', 
                'Margin', 'Neutral', 'Location', 'Location2', 'Source', 'Forfeit']

print("=" * 80)
print("LoneStar Excel to SQL Importer")
print("=" * 80)
print(f"Excel File: {EXCEL_PATH}")
print(f"Sheet: {SHEET_NAME}")
print()

# ============================================================================
# STEP 1: Read Excel File
# ============================================================================

print("Reading Excel file...")
try:
    # Read only the specific columns we need
    df = pd.read_excel(
        EXCEL_PATH,
        sheet_name=SHEET_NAME,
        usecols=EXCEL_COLUMNS_TO_READ,
        header=0,
        names=COLUMN_NAMES
    )
    
    print(f"✓ Loaded {len(df)} rows from Excel")
    print(f"\nColumn names: {list(df.columns)}")
    
    # Show first row
    print("\nFirst row sample:")
    print(df.head(1).to_dict('records')[0])
    
except Exception as e:
    print(f"✗ Error reading Excel: {e}")
    sys.exit(1)

# ============================================================================
# STEP 2: Clean and Prepare Data
# ============================================================================

# ============================================================================
# STEP 2: Clean and Prepare Data
# ============================================================================
print("\nCleaning data...")

# Remove rows where Home or Visitor is missing
initial_count = len(df)
df = df.dropna(subset=['Home', 'Visitor'])
print(f"✓ Removed {initial_count - len(df)} rows with missing teams")

# 1. Convert Date column
def convert_excel_date(val):
    if pd.isna(val): 
        return None
    if isinstance(val, datetime): 
        return val.date()
    try:
        # Handle Excel serial dates or strings
        return pd.to_datetime(val).date()
    except:
        return None

df['Date'] = df['Date'].apply(convert_excel_date)

# 2. Convert Boolean fields
df['Neutral'] = df['Neutral'].apply(lambda x: 1 if x in [True, 'TRUE', 1, '1'] else 0)

# 3. Handle Forfeit (Logic: Explicit True OR 1-0 scores)
def detect_forfeit(row):
    if pd.notna(row['Forfeit']) and row['Forfeit'] in [True, 'TRUE', 1, '1']:
        return 1
    if (row['Home_Score'] == 1 and row['Visitor_Score'] == 0) or \
       (row['Home_Score'] == 0 and row['Visitor_Score'] == 1):
        return 1
    return 0

df['Forfeit'] = df.apply(detect_forfeit, axis=1)

# 4. Handle Numeric Columns (Season, Scores) -> Force to Int, 0 if missing
for col in ['Season', 'Visitor_Score', 'Home_Score', 'Margin']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 5. Handle String/Nullable fields (The critical fix for NaN/None)
# Force columns to object type first so they can accept None
cols_to_fix = ['Location', 'Location2', 'Source']
for col in cols_to_fix:
    if col in df.columns:
        df[col] = df[col].astype(object)
        # Replace NaN/NaT with None
        df[col] = df[col].where(pd.notnull(df[col]), None)
        # Replace string "Unknown" with None
        df[col] = df[col].replace({'Unknown': None})

# 6. Apply Defaults
# Set Source default if it ended up as None
df['Source'] = df['Source'].fillna('LoneStar')

print(f"✓ Data cleaned, {len(df)} rows ready for import")

# ============================================================================
# STEP 3: Connect to SQL Server
# ============================================================================

print("\nConnecting to SQL Server...")

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER_NAME};"
    f"DATABASE={DATABASE_NAME};"
    f"Trusted_Connection=yes;"
    f"TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("✓ Connected to SQL Server")
except Exception as e:
    print(f"✗ Database connection error: {e}")
    sys.exit(1)

# ============================================================================
# STEP 4: Get Next BatchID
# ============================================================================

try:
    cursor.execute("SELECT ISNULL(MAX(BatchID), 0) + 1 FROM dbo.HS_Scores_LoneStar_Staging")
    batch_id = cursor.fetchone()[0]
    print(f"✓ Using Batch ID: {batch_id}")
except Exception as e:
    print(f"✗ Error getting BatchID: {e}")
    conn.close()
    sys.exit(1)

# ============================================================================
# STEP 5: Insert Data
# ============================================================================

print("\nImporting data to staging table...")

insert_sql = """
INSERT INTO dbo.HS_Scores_LoneStar_Staging (
    [Date], Season, Home, Visitor, Neutral, Location, Location2, 
    Line, Future_Game, Source, OT, Forfeit, Visitor_Score, Home_Score, 
    Margin, BatchID, Status
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
"""

success_count = 0
error_count = 0
errors = []

print("\nImporting data to staging table...")

# Debug: Show first row values that will be inserted
first_row = df.iloc[0]
print("\nDEBUG - First row values to insert:")
print(f"  Date: {first_row['Date']} (type: {type(first_row['Date'])})")
print(f"  Season: {int(first_row['Season'])} (type: int)")
print(f"  Home: {first_row['Home']}")
print(f"  Visitor: {first_row['Visitor']}")
print(f"  Neutral: {int(first_row['Neutral'])}")
print(f"  Location: {first_row['Location']}")
print(f"  Location2: {first_row['Location2']}")
print(f"  Line: None (not tracked)")
print(f"  Future_Game: None (not tracked)")
print(f"  Source: {first_row['Source']}")
print(f"  OT: None (not tracked)")
print(f"  Forfeit: {int(first_row['Forfeit'])}")
print(f"  Visitor_Score: {int(first_row['Visitor_Score'])}")
print(f"  Home_Score: {int(first_row['Home_Score'])}")
print(f"  Margin: {int(first_row['Margin'])}")
print(f"  BatchID: {batch_id}")
print()

for idx, row in df.iterrows():
    try:
        # Prepare values - simplified since we removed columns
        values = (
            row['Date'],
            int(row['Season']),
            row['Home'],
            row['Visitor'],
            int(row['Neutral']),
            row['Location'],
            row['Location2'],
            None,  # Line - not tracked
            None,  # Future_Game - not tracked
            row['Source'],  # Already defaulted to 'LoneStar' if missing
            None,  # OT - not tracked
            int(row['Forfeit']),
            int(row['Visitor_Score']),
            int(row['Home_Score']),
            int(row['Margin']),
            batch_id
        )
        
        cursor.execute(insert_sql, values)
        success_count += 1
        
        # Progress indicator
        if success_count % 500 == 0:
            print(f"  Imported {success_count} rows...")
            
    except Exception as e:
        error_count += 1
        error_msg = f"Row {idx}: {e} | Home: {row['Home']} | Visitor: {row['Visitor']}"
        errors.append(error_msg)
        
        if error_count <= 10:
            print(f"  ✗ {error_msg}")

# Commit transaction
try:
    conn.commit()
    print(f"\n✓ Transaction committed")
except Exception as e:
    print(f"\n✗ Commit failed: {e}")
    conn.rollback()
    conn.close()
    sys.exit(1)

# ============================================================================
# STEP 6: Report Results
# ============================================================================

print("\n" + "=" * 80)
print("IMPORT COMPLETE")
print("=" * 80)
print(f"Successfully imported: {success_count} rows")
print(f"Errors: {error_count} rows")
print(f"Batch ID: {batch_id}")

if errors:
    print(f"\nFirst 10 errors:")
    for error in errors[:10]:
        print(f"  {error}")
    
    # Save all errors to file
    error_file = f"C:\\Temp\\lonestar_import_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(error_file, 'w') as f:
            f.write('\n'.join(errors))
        print(f"\nAll errors saved to: {error_file}")
    except:
        pass

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("1. Verify data in staging table:")
print(f"   SELECT TOP 10 * FROM HS_Scores_LoneStar_Staging WHERE BatchID = {batch_id}")
print("")
print("2. Run validation and import to production:")
print(f"   EXEC dbo.sp_Import_LoneStar_Batch @BatchID = {batch_id}")
print("=" * 80)

conn.close()
