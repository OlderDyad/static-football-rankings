"""
Test: Insert ONE row to identify the exact failing parameter
"""

import pandas as pd
import pyodbc
from datetime import datetime

# Configuration
excel_file = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HSF Texas 2025_teams_45-1601_v1.xlsx"
sheet_name = "Lonestar_Import"

# Database connection
server = r'McKnights-PC\SQLEXPRESS01'
database = 'hs_football_database'

print("Loading first row from Excel...")
df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=1)
print(f"✓ Loaded 1 row")
print()

# Show the row
print("Row data:")
for col in df.columns:
    val = df[col].iloc[0]
    print(f"  {col}: {val} (type: {type(val).__name__})")
print()

# Connect to database
print("Connecting to database...")
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
print("✓ Connected")
print()

# Convert boolean to int
if df['Neutral'].dtype == 'bool':
    df['Neutral'] = df['Neutral'].astype(int)

# Prepare single row
row = df.iloc[0]
today = datetime.now()
batch_id = 999  # Test batch

# Handle NaN values
location2 = None if pd.isna(row['Location2']) else row['Location2']
forfeit = None if pd.isna(row['Forfeit']) else row['Forfeit']

# Print what we're about to insert
print("Values to insert:")
values = (
    row['Date'],           # 1
    row['Season'],         # 2
    row['Visitor'],        # 3
    row['Visitor_Score'],  # 4
    row['Home'],           # 5
    row['Home_Score'],     # 6
    row['Margin'],         # 7
    row['Neutral'],        # 8
    row['Location'],       # 9
    location2,             # 10
    row['Source'],         # 11
    batch_id,              # 12
    today,                 # 13 - THIS IS THE SUSPECT
    forfeit                # 14
)

for i, val in enumerate(values, 1):
    print(f"  {i:2d}. {val} (type: {type(val).__name__})")
print()

# Try to insert
insert_sql = """
INSERT INTO HS_Scores (
    Date, Season, Visitor, Visitor_Score, Home, Home_Score,
    Margin, Neutral, Location, Location2, Source, 
    BatchID, Date_Added, Forfeit
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

print("Attempting insert...")
try:
    cursor.execute(insert_sql, values)
    conn.commit()
    print("✓ SUCCESS! Insert worked!")
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()
    
    # Try to identify which parameter is failing
    print("Testing each parameter individually...")
    for i in range(len(values)):
        try:
            test_val = values[i]
            # Test if this value can be used in a simple query
            cursor.execute("SELECT ?", (test_val,))
            print(f"  {i+1:2d}. OK: {test_val}")
        except Exception as param_err:
            print(f"  {i+1:2d}. FAIL: {test_val} - {param_err}")

conn.close()