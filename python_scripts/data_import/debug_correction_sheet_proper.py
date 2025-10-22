import pandas as pd
import os

# Path to your correction sheet
correction_file = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/Alias_Correction_Sheet.csv"

print("=== DEBUGGING CORRECTION SHEET ===")
print(f"File path: {correction_file}")
print(f"File exists: {os.path.exists(correction_file)}")

if os.path.exists(correction_file):
    # Read the CSV
    df = pd.read_csv(correction_file)
    print(f"\nTotal rows in CSV: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Show the actual data
    print("\n=== FULL CORRECTION SHEET CONTENTS ===")
    print(df.to_string(index=False))
    
    # Check what find_alias_matches.py would see
    print("\n=== ANALYSIS FOR find_alias_matches.py ===")
    
    # Check for Final_Proper_Name column
    if 'Final_Proper_Name' in df.columns:
        print(f"Final_Proper_Name column exists")
        
        # Check for empty/null values in Final_Proper_Name
        empty_mask = df['Final_Proper_Name'].isna() | (df['Final_Proper_Name'].astype(str).str.strip() == '') | (df['Final_Proper_Name'].astype(str) == 'nan')
        empty_rows = df[empty_mask]
        
        print(f"Rows with empty Final_Proper_Name: {len(empty_rows)}")
        if len(empty_rows) > 0:
            print("Empty rows:")
            print(empty_rows[['Unrecognized_Alias', 'Final_Proper_Name']].to_string(index=False))
        
        filled_rows = df[~empty_mask]
        print(f"Rows with filled Final_Proper_Name: {len(filled_rows)}")
        if len(filled_rows) > 0:
            print("Filled rows:")
            print(filled_rows[['Unrecognized_Alias', 'Final_Proper_Name']].to_string(index=False))
    else:
        print("Final_Proper_Name column does not exist!")
        
    # Check the actual values in Final_Proper_Name column
    print("\n=== DETAILED Final_Proper_Name VALUES ===")
    for idx, row in df.iterrows():
        alias = row.get('Unrecognized_Alias', 'N/A')
        final_name = row.get('Final_Proper_Name', 'N/A')
        print(f"Row {idx}: '{alias}' -> '{final_name}' (type: {type(final_name)}, repr: {repr(final_name)})")
else:
    print("Correction sheet file not found!")