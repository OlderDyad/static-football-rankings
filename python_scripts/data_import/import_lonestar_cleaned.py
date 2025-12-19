#!/usr/bin/env python3
"""
Import Cleaned LoneStar Data from Lonestar_Import Tab
======================================================

Reads properly cleaned data from the Lonestar_Import tab
which has already been processed by Excel formulas.

Columns A-P:
A: Date
B: Season  
C: Visitor (CLEANED)
D: Visitor_Score
E: Home (CLEANED)
F: Home_Score
G: Margin
H: Neutral
I: Location
J: Location2
K: Line (skip)
L: Future_Game (skip)
M: Source
N: Date_Added
O: OT (skip)
P: Forfeit
"""

import pandas as pd
import pyodbc
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

EXCEL_FILE = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HSF Texas 2025_teams_1-720_v1.xlsx"
SHEET_NAME = "Lonestar_Import"

DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=McKnights-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

# ============================================================================
# MAIN IMPORT
# ============================================================================

def main():
    print("="*80)
    print("LoneStar CLEANED Data Import")
    print("="*80)
    print()
    
    # Load Excel from cleaned tab
    print(f"Loading: {EXCEL_FILE}")
    print(f"Sheet: {SHEET_NAME}")
    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
    print(f"✓ Loaded {len(df)} rows")
    print(f"✓ Columns: {list(df.columns)}")
    print()
    
    # Connect to database
    print("Connecting to database...")
    conn = pyodbc.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    print("✓ Connected")
    print()
    
    """  # <-- ADD THIS LINE TO SKIP DELETES
    # Delete previous bad import (BatchID = 2 from today only)
    print("Deleting previous bad import (BatchID = 2 from today)...")
    cursor.execute(...)
    ...
    conn.commit()
    print()
    """  # <-- ADD THIS LINE TO END SKIP
    
    # Get next batch ID (generate new unique ID)
    cursor.execute("SELECT ISNULL(MAX(BatchID), 0) + 1 FROM HS_Scores")
    batch_id = cursor.fetchone()[0]
    print(f"Using NEW Batch ID: {batch_id}")
    print()
    
    # Process and import
    print("Importing cleaned data...")
    imported = 0
    errors = 0
    
    for idx, row in df.iterrows():
        try:
            # Read from columns A-P
            date = row.iloc[0]  # A: Date
            season = int(row.iloc[1]) if not pd.isna(row.iloc[1]) else None  # B: Season
            visitor = str(row.iloc[2]) if not pd.isna(row.iloc[2]) else None  # C: Visitor
            visitor_score = int(row.iloc[3]) if not pd.isna(row.iloc[3]) else 0  # D: Visitor_Score
            home = str(row.iloc[4]) if not pd.isna(row.iloc[4]) else None  # E: Home
            home_score = int(row.iloc[5]) if not pd.isna(row.iloc[5]) else 0  # F: Home_Score
            margin = int(row.iloc[6]) if not pd.isna(row.iloc[6]) else 0  # G: Margin
            neutral = 1 if row.iloc[7] == True or row.iloc[7] == 1 else 0  # H: Neutral
            location = str(row.iloc[8]) if not pd.isna(row.iloc[8]) and row.iloc[8] != 'Unknown' else None  # I: Location
            location2 = str(row.iloc[9]) if not pd.isna(row.iloc[9]) else None  # J: Location2
            # K: Line - skip
            # L: Future_Game - skip
            source = str(row.iloc[12]) if not pd.isna(row.iloc[12]) else 'LoneStar'  # M: Source
            # N: Date_Added - skip (use current time)
            # O: OT - skip
            forfeit = 1 if row.iloc[15] == True or row.iloc[15] == 1 else 0  # P: Forfeit
            
            # Skip rows with missing critical data
            if not home or not visitor or not season:
                continue
            
            # Handle date - convert Excel date if needed
            if isinstance(date, (int, float)):
                # Excel serial date
                from datetime import datetime, timedelta
                date = datetime(1899, 12, 30) + timedelta(days=date)
            elif isinstance(date, str):
                # Try to parse string date
                try:
                    date = datetime.strptime(date, '%m/%d/%Y')
                except:
                    # Default to September 1st of season
                    date = datetime(season, 9, 1)
            
            # Insert directly to HS_Scores
            sql = """
                INSERT INTO HS_Scores (
                    ID, Date, Season, Home, Visitor, 
                    Home_Score, Visitor_Score, Margin,
                    Neutral, Location, Location2,
                    Forfeit, Source, Date_Added, BatchID
                ) VALUES (
                    NEWID(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?
                )
            """
            
            cursor.execute(sql,
                date, season, home, visitor,
                home_score, visitor_score, margin,
                neutral, location, location2,
                forfeit, source, batch_id
            )
            
            imported += 1
            
            if imported % 1000 == 0:
                print(f"  Imported {imported} games...")
                conn.commit()
            
        except Exception as e:
            print(f"  ERROR on row {idx}: {e}")
            errors += 1
            if errors > 100:
                print("Too many errors, stopping")
                break
    
    # Final commit
    conn.commit()
    
    print()
    print("="*80)
    print("IMPORT COMPLETE")
    print("="*80)
    print(f"Batch ID: {batch_id}")
    print(f"Imported: {imported} games")
    print(f"Errors: {errors}")
    print()
    
    # Verify
    cursor.execute("""
        SELECT Season, COUNT(*) as GameCount
        FROM HS_Scores
        WHERE BatchID = ?
        GROUP BY Season
        ORDER BY Season
    """, batch_id)
    
    print("Games by season:")
    for row in cursor.fetchall():
        print(f"  {row.Season}: {row.GameCount} games")
    
    print()
    print("✓ Import successful!")
    print("="*80)
    
    conn.close()

if __name__ == "__main__":
    main()
