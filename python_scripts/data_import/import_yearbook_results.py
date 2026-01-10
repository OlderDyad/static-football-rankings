"""
Import Yearbook_Results.csv into HS_Scores table
Author: David McKnight
Date: January 10, 2026

This script imports game results from a CSV file into the HS_Scores table,
following the established data pipeline patterns for McKnight's American Football Rankings.
"""

import pyodbc
import pandas as pd
import uuid
from datetime import datetime
import os

# Configuration
CSV_FILE = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Yearbook_Results.csv"
SERVER = r'MCKNIGHTS-PC\SQLEXPRESS01'
DATABASE = 'hs_football_database'
SOURCE_NAME = 'Yearbook'  # Change this if you want a different source identifier

# Expected CSV columns (adjust based on your actual file structure)
# Common formats from your workflows:
# Option 1: HomeTeamRaw, HomeScore, VisitorTeamRaw, VisitorScore, Date, etc.
# Option 2: Date, Season, Home, Visitor, Home_Score, Visitor_Score, etc.


def get_connection():
    """Establish database connection"""
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'Trusted_Connection=yes;'
    )
    try:
        conn = pyodbc.connect(conn_str)
        print("✓ Connected to database")
        return conn
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        raise


def get_next_batch_id(cursor):
    """Get the next BatchID for this import"""
    cursor.execute("SELECT ISNULL(MAX(BatchID), 0) + 1 FROM dbo.HS_Scores")
    batch_id = cursor.fetchone()[0]
    print(f"✓ Generated BatchID: {batch_id}")
    return batch_id


def load_csv(file_path):
    """Load and validate CSV file"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    print(f"✓ Loaded {len(df)} rows from CSV")
    print(f"  Columns found: {', '.join(df.columns)}")
    return df


def standardize_data(df, batch_id):
    """
    Standardize CSV data to match HS_Scores schema
    
    Adjust column mapping based on your CSV structure
    """
    date_added = datetime.now()
    
    # Initialize standardized columns
    standardized = pd.DataFrame()
    
    # Try to detect column format and map accordingly
    columns = [col.lower() for col in df.columns]
    
    # Detect format type
    if 'hometeamraw' in columns or 'home_team_raw' in columns:
        # Format from newspaper OCR workflow
        print("  Detected format: OCR/Newspaper style")
        standardized['Home'] = df.get('HomeTeamRaw', df.get('Home'))
        standardized['Visitor'] = df.get('VisitorTeamRaw', df.get('Visitor'))
        standardized['Home_Score'] = df.get('HomeScore', df.get('Home_Score'))
        standardized['Visitor_Score'] = df.get('VisitorScore', df.get('Visitor_Score'))
    else:
        # Standard format
        print("  Detected format: Standard style")
        standardized['Home'] = df['Home']
        standardized['Visitor'] = df['Visitor']
        standardized['Home_Score'] = pd.to_numeric(df['Home_Score'], errors='coerce')
        standardized['Visitor_Score'] = pd.to_numeric(df['Visitor_Score'], errors='coerce')
    
    # Date handling
    if 'Date' in df.columns:
        standardized['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        # If no date, you'll need to add this manually or derive it
        print("  WARNING: No Date column found - using NULL")
        standardized['Date'] = None
    
    # Season (derive from date if not present)
    if 'Season' in df.columns:
        standardized['Season'] = pd.to_numeric(df['Season'], errors='coerce')
    elif 'Date' in df.columns:
        standardized['Season'] = pd.to_datetime(df['Date'], errors='coerce').dt.year
    else:
        print("  WARNING: No Season column found - using NULL")
        standardized['Season'] = None
    
    # Calculate margin (use existing if present, otherwise calculate)
    if 'Margin' in df.columns:
        standardized['Margin'] = pd.to_numeric(df['Margin'], errors='coerce')
    else:
        standardized['Margin'] = standardized['Home_Score'] - standardized['Visitor_Score']
    
    # Helper function to convert empty strings and 'FALSE'/'TRUE' to proper values
    def clean_bit_field(series):
        """Convert bit field to 0/1, treating empty strings as 0"""
        if series is None:
            return 0
        # Replace empty strings with 0
        cleaned = series.replace('', 0)
        # Handle TRUE/FALSE strings
        cleaned = cleaned.replace('TRUE', 1).replace('True', 1).replace('true', 1)
        cleaned = cleaned.replace('FALSE', 0).replace('False', 0).replace('false', 0)
        # Convert to numeric, coercing errors to 0
        return pd.to_numeric(cleaned, errors='coerce').fillna(0).astype(int)
    
    def clean_int_field(series):
        """Convert integer field, treating empty strings as NULL"""
        if series is None:
            return None
        # Replace empty strings with NaN
        cleaned = series.replace('', pd.NA)
        # Convert to numeric, coercing errors to NaN
        return pd.to_numeric(cleaned, errors='coerce')
    
    def clean_string_field(series):
        """Convert string field, treating empty strings as NULL"""
        if series is None:
            return None
        # Replace empty strings with None
        cleaned = series.replace('', None)
        # Also replace 'Unknown' with None if desired
        # cleaned = cleaned.replace('Unknown', None)
        return cleaned
    
    # Optional fields with proper type handling
    standardized['Neutral'] = clean_bit_field(df.get('Neutral'))
    standardized['Location'] = clean_string_field(df.get('Location'))
    standardized['Location2'] = clean_string_field(df.get('Location2'))
    standardized['Line'] = clean_int_field(df.get('Line'))
    standardized['Future_Game'] = clean_bit_field(df.get('Future_Game'))
    standardized['OT'] = clean_int_field(df.get('OT', df.get('Overtime')))
    standardized['Forfeit'] = clean_bit_field(df.get('Forfeit'))
    
    # Source handling - use existing if present, otherwise use default
    if 'Source' in df.columns:
        standardized['Source'] = df['Source']
    else:
        standardized['Source'] = SOURCE_NAME
    
    # Generated fields
    standardized['Date_Added'] = date_added
    standardized['BatchID'] = batch_id
    
    # Generate unique IDs and Access_IDs
    standardized['ID'] = [str(uuid.uuid4()) for _ in range(len(standardized))]
    
    # Create Access_ID (format: YYYYMMDD-Home-Visitor)
    def make_access_id(row):
        if pd.notna(row['Date']):
            date_str = row['Date'].strftime('%Y%m%d')
            return f"{date_str}-{row['Home']}-{row['Visitor']}"
        else:
            return None
    
    standardized['Access_ID'] = standardized.apply(make_access_id, axis=1)
    
    return standardized


def validate_data(df):
    """Validate data before import"""
    issues = []
    
    # Check for required fields
    required_fields = ['Home', 'Visitor', 'Home_Score', 'Visitor_Score']
    for field in required_fields:
        if df[field].isna().any():
            null_count = df[field].isna().sum()
            issues.append(f"  ✗ {field} has {null_count} NULL values")
    
    # Check for invalid scores
    if (df['Home_Score'] < 0).any() or (df['Visitor_Score'] < 0).any():
        issues.append("  ✗ Found negative scores")
    
    # Check for blank team names
    if (df['Home'].str.strip() == '').any() or (df['Visitor'].str.strip() == '').any():
        issues.append("  ✗ Found blank team names")
    
    if issues:
        print("⚠ Data validation warnings:")
        for issue in issues:
            print(issue)
        response = input("Continue with import? (y/n): ")
        if response.lower() != 'y':
            raise ValueError("Import cancelled due to validation issues")
    else:
        print("✓ Data validation passed")


def insert_data(cursor, df, batch_size=1000):
    """Insert data into HS_Scores table"""
    
    insert_query = """
    INSERT INTO dbo.HS_Scores (
        Date, Season, Home, Visitor, Home_Score, Visitor_Score, Margin,
        Neutral, Location, Location2, Line, Future_Game, Source, 
        Date_Added, OT, Forfeit, ID, BatchID, Access_ID
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Helper function to convert pandas NA/NaN to Python None
    def clean_value(val):
        if pd.isna(val):
            return None
        # Convert numpy types to Python types
        if hasattr(val, 'item'):
            return val.item()
        return val
    
    # Prepare data for insertion
    records = []
    for _, row in df.iterrows():
        record = (
            clean_value(row['Date']),
            clean_value(row['Season']),
            clean_value(row['Home']),
            clean_value(row['Visitor']),
            clean_value(row['Home_Score']),
            clean_value(row['Visitor_Score']),
            clean_value(row['Margin']),
            clean_value(row['Neutral']),
            clean_value(row['Location']),
            clean_value(row['Location2']),
            clean_value(row['Line']),
            clean_value(row['Future_Game']),
            clean_value(row['Source']),
            clean_value(row['Date_Added']),
            clean_value(row['OT']),
            clean_value(row['Forfeit']),
            clean_value(row['ID']),
            clean_value(row['BatchID']),
            clean_value(row['Access_ID'])
        )
        records.append(record)
    
    # Insert in batches
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        cursor.executemany(insert_query, batch)
        
        if (i + batch_size) % 10000 == 0 or i + batch_size >= total:
            print(f"  Processed {min(i + batch_size, total):,} / {total:,} rows")
    
    print(f"✓ Inserted {total:,} records")


def main():
    """Main import workflow"""
    print("=" * 60)
    print("Yearbook Results Import Script")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Load CSV
        print("Step 1: Loading CSV file...")
        df = load_csv(CSV_FILE)
        print()
        
        # Step 2: Show sample data
        print("Step 2: Sample data preview:")
        print(df.head(3))
        print()
        
        # Step 3: Connect to database
        print("Step 3: Connecting to database...")
        conn = get_connection()
        cursor = conn.cursor()
        print()
        
        # Step 4: Get BatchID
        print("Step 4: Generating BatchID...")
        batch_id = get_next_batch_id(cursor)
        print()
        
        # Step 5: Standardize data
        print("Step 5: Standardizing data...")
        standardized_df = standardize_data(df, batch_id)
        print(f"  Standardized {len(standardized_df)} rows")
        print()
        
        # Step 6: Validate data
        print("Step 6: Validating data...")
        validate_data(standardized_df)
        print()
        
        # Step 7: Insert data
        print("Step 7: Inserting into database...")
        insert_data(cursor, standardized_df)
        print()
        
        # Step 8: Commit transaction
        print("Step 8: Committing transaction...")
        conn.commit()
        print("✓ Transaction committed")
        print()
        
        # Step 9: Summary
        print("=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        print(f"  Records imported: {len(standardized_df):,}")
        print(f"  BatchID: {batch_id}")
        print(f"  Source: {SOURCE_NAME}")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("Next steps:")
        print("  1. Run duplicate removal: EXEC dbo.RemoveDuplicateGames;")
        print("  2. Verify margin calculation: SELECT * FROM HS_Scores WHERE Margin <> (Home_Score - Visitor_Score);")
        print(f"  3. Check new data: SELECT TOP 100 * FROM HS_Scores WHERE BatchID = {batch_id} ORDER BY Date DESC;")
        print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
            print("  Transaction rolled back")
        raise
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("✓ Database connection closed")


if __name__ == "__main__":
    main()