"""
Import LoneStar Football Data - UNIVERSAL BATCH IMPORT
=======================================================
Works for ANY batch - just specify the Excel file path

Usage:
    python import_lonestar_universal.py "path/to/file.xlsx"

The script will:
1. Auto-detect the Excel file
2. Read from "Lonestar_Import" sheet
3. Auto-generate new BatchID
4. Import all rows
5. Run verification

Requirements:
- Excel file must have "Lonestar_Import" sheet
- Columns A-P: Date, Season, Visitor, Visitor_Score, Home, Home_Score,
                Margin, Neutral, Location, Location2, Line, Future_Game,
                Source, Date_Added, OT, Forfeit
"""

import sys
import pandas as pd
import pyodbc
from datetime import datetime
from pathlib import Path

def main():
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    # Get Excel file path from command line or use default
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        # Default to most recent file pattern
        print("Usage: python import_lonestar_universal.py <excel_file>")
        print()
        print("Example:")
        print('  python import_lonestar_universal.py "HSF Texas 2025_teams_45-1801_v1.xlsx"')
        return
    
    sheet_name = "Lonestar_Import"
    
    # Database connection
    server = r'McKnights-PC\SQLEXPRESS01'
    database = 'hs_football_database'
    
    # ========================================================================
    # LOAD DATA
    # ========================================================================
    
    print("="*80)
    print("LONESTAR UNIVERSAL BATCH IMPORT")
    print("="*80)
    print()
    print(f"Excel File: {excel_file}")
    print(f"Sheet: {sheet_name}")
    print()
    
    # Check if file exists
    if not Path(excel_file).exists():
        print(f"❌ ERROR: File not found: {excel_file}")
        print()
        print("Make sure:")
        print("1. File path is correct")
        print("2. File name is spelled correctly")
        print("3. Excel file is closed")
        return
    
    # Read Excel file
    try:
        df_all = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # Extract only the cleaned columns
        cleaned_cols = ['Date', 'Season', 'Visitor', 'Visitor_Score', 'Home', 'Home_Score', 
                       'Margin', 'Neutral', 'Location', 'Location2', 'Line', 'Future_Game',
                       'Source', 'Date_Added', 'OT', 'Forfeit']
        
        df = df_all[cleaned_cols]
        
        print(f"✓ Loaded {len(df):,} rows")
        print()
    except FileNotFoundError:
        print(f"❌ ERROR: File not found: {excel_file}")
        return
    except Exception as e:
        print(f"❌ ERROR loading Excel: {e}")
        return
    
    # ========================================================================
    # DATABASE CONNECTION
    # ========================================================================
    
    print("Connecting to database...")
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("✓ Connected")
        print()
    except Exception as e:
        print(f"❌ ERROR connecting to database: {e}")
        return
    
    # ========================================================================
    # GENERATE BATCH ID
    # ========================================================================
    
    try:
        cursor.execute("SELECT ISNULL(MAX(BatchID), 0) + 1 FROM HS_Scores")
        batch_id = cursor.fetchone()[0]
        print(f"✓ Generated BatchID: {batch_id}")
        print()
    except Exception as e:
        print(f"❌ ERROR getting BatchID: {e}")
        conn.close()
        return
    
    # ========================================================================
    # PREPARE DATA
    # ========================================================================
    
    print("Preparing data for import...")
    
    # Replace NaN with None for SQL NULL
    df = df.where(pd.notnull(df), None)
    
    # Ensure Date column is datetime
    if df['Date'].dtype != 'datetime64[ns]':
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Convert boolean Neutral to integer (0/1) for SQL
    if df['Neutral'].dtype == 'bool':
        df['Neutral'] = df['Neutral'].astype(int)
    
    # Build insert statement
    # Note: ID is uniqueidentifier, use NEWID() to auto-generate
    insert_sql = """
    INSERT INTO HS_Scores (
        ID, Date, Season, Visitor, Visitor_Score, Home, Home_Score,
        Margin, Neutral, Location, Location2, Source, 
        BatchID, Date_Added, Forfeit
    ) VALUES (NEWID(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Prepare rows
    today = datetime.now()
    rows = []
    
    for idx, row in df.iterrows():
        # Convert numpy types to Python native types for pyodbc compatibility
        # PyODBC cannot handle numpy.int64, numpy.float64, etc.
        
        # Integer columns - convert numpy.int64 to Python int
        season = int(row['Season']) if pd.notna(row['Season']) else None
        visitor_score = int(row['Visitor_Score']) if pd.notna(row['Visitor_Score']) else None
        home_score = int(row['Home_Score']) if pd.notna(row['Home_Score']) else None
        margin = int(row['Margin']) if pd.notna(row['Margin']) else None
        neutral = int(row['Neutral']) if pd.notna(row['Neutral']) else None
        
        # Float columns - convert numpy.float64 to Python float or None
        location2 = float(row['Location2']) if pd.notna(row['Location2']) else None
        forfeit = float(row['Forfeit']) if pd.notna(row['Forfeit']) else None
        
        rows.append((
            row['Date'],      # pandas Timestamp is fine
            season,           # Python int
            row['Visitor'],   # str is fine
            visitor_score,    # Python int
            row['Home'],      # str is fine
            home_score,       # Python int
            margin,           # Python int
            neutral,          # Python int (0 or 1)
            row['Location'],  # str is fine
            location2,        # Python float or None
            row['Source'],    # str is fine
            batch_id,         # Python int
            today,            # Python datetime
            forfeit           # Python float or None
        ))
        
        # Progress update
        if (idx + 1) % 10000 == 0:
            print(f"  Prepared {idx + 1:,} rows...")
    
    print(f"✓ Prepared {len(rows):,} rows")
    print()
    
    # ========================================================================
    # INSERT DATA
    # ========================================================================
    
    print("Inserting into HS_Scores...")
    try:
        cursor.executemany(insert_sql, rows)
        conn.commit()
        print(f"✓ Inserted {len(rows):,} rows")
        print()
    except Exception as e:
        print(f"❌ ERROR during insert: {e}")
        conn.rollback()
        conn.close()
        return
    
    # ========================================================================
    # VERIFICATION
    # ========================================================================
    
    print("Verifying import...")
    cursor.execute("""
        SELECT COUNT(*) as GameCount,
               MIN(Season) as FirstSeason,
               MAX(Season) as LastSeason
        FROM HS_Scores
        WHERE BatchID = ?
    """, batch_id)
    
    result = cursor.fetchone()
    print(f"✓ Verification:")
    print(f"  Games imported: {result[0]:,}")
    print(f"  Season range: {result[1]} - {result[2]}")
    print(f"  BatchID: {batch_id}")
    print()
    
    conn.close()
    
    # ========================================================================
    # SUCCESS MESSAGE
    # ========================================================================
    
    print("="*80)
    print("✓ IMPORT COMPLETE!")
    print("="*80)
    print()
    print("📊 NEXT STEPS:")
    print("1. Run audit queries in SSMS to verify data quality")
    print("2. Check for junk names (should be 0)")
    print("3. Verify game count matches Excel")
    print("4. Review season distribution")
    print()
    print("🔍 QUICK AUDIT QUERY:")
    print(f"""
    SELECT COUNT(*) as JunkCount
    FROM HS_Scores
    WHERE BatchID = {batch_id}
      AND (Visitor LIKE '%v' OR Visitor LIKE '[0-9]%' 
           OR Home LIKE '%v' OR Home LIKE '[0-9]%');
    """)
    print()

if __name__ == "__main__":
    main()