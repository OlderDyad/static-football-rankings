"""
Diagnostic: Find problematic rows with empty strings in numeric columns
"""

import pandas as pd

# Configuration
excel_file = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HSF Texas 2025_teams_45-1601_v1.xlsx"
sheet_name = "Lonestar_Import"

print(f"Loading: {excel_file}")
print(f"Sheet: {sheet_name}")
df = pd.read_excel(excel_file, sheet_name=sheet_name)
print(f"✓ Loaded {len(df)} rows")
print()

# Check data types
print("Column Data Types:")
for col in df.columns:
    print(f"  {col}: {df[col].dtype}")
print()

# Check for problematic values in each column we're trying to insert
insert_cols = ['Date', 'Season', 'Visitor', 'Visitor_Score', 'Home', 'Home_Score', 
               'Margin', 'Neutral', 'Location', 'Location2', 'Source', 'Forfeit']

print("Checking for problematic values:")
for i, col in enumerate(insert_cols, 1):
    if col not in df.columns:
        print(f"  {i}. {col}: MISSING!")
        continue
        
    null_count = df[col].isna().sum()
    
    # Check for empty strings
    if df[col].dtype == 'object':
        empty_str_count = (df[col] == '').sum()
        print(f"  {i}. {col} (object): {null_count} nulls, {empty_str_count} empty strings")
    else:
        print(f"  {i}. {col} ({df[col].dtype}): {null_count} nulls")
        
        # For numeric columns, check for NaN
        if df[col].dtype in ['float64', 'int64']:
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                print(f"     WARNING: {nan_count} NaN values - will be converted to NULL")

print()

# Look at rows with NaN in Date_Added
if 'Date_Added' in df.columns:
    print("Date_Added analysis:")
    print(f"  Total rows: {len(df)}")
    print(f"  Non-null: {df['Date_Added'].notna().sum()}")
    print(f"  Null/NaN: {df['Date_Added'].isna().sum()}")
    
    # Show a few rows with null Date_Added
    null_dates = df[df['Date_Added'].isna()]
    if len(null_dates) > 0:
        print(f"\n  First 5 rows with NULL Date_Added:")
        print(null_dates[['Date', 'Visitor', 'Home', 'Date_Added']].head())
    print()

# Show first 3 rows
print("First 3 rows:")
print(df.head(3)[['Date', 'Season', 'Visitor', 'Visitor_Score', 'Home', 'Home_Score', 'Date_Added']])
print()

# Show last 3 rows
print("Last 3 rows:")
print(df.tail(3)[['Date', 'Season', 'Visitor', 'Visitor_Score', 'Home', 'Home_Score', 'Date_Added']])