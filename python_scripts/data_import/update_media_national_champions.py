# update_media_national_champions.py
"""
Updates Media_National_Champions table using alias rules from all states.
Run this BEFORE running the consolidation workflow to avoid FK constraint issues.
"""
import pandas as pd
import pyodbc
import logging
import os
import sys
import glob

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
RULES_FOLDER = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/excel_files/State_Aliases_ProperNames"
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_alias_files():
    """Returns a list of all *_Alias_Rules.csv files in the rules folder."""
    pattern = os.path.join(RULES_FOLDER, "*_Alias_Rules.csv")
    files = glob.glob(pattern)
    return files

def extract_state_code_from_filename(file_path):
    """Extracts the state code from a filename like 'MD_Alias_Rules.csv' and returns '(MD)'."""
    filename = os.path.basename(file_path)
    state_abbr = filename.split('_')[0]
    return f"({state_abbr})"

def update_media_national_champions_for_state(state_code, file_path):
    """Updates Media_National_Champions table for a single state."""
    logging.info(f"Processing Media_National_Champions updates for state: {state_code}")
    
    try:
        # Load the alias rules
        df = pd.read_csv(file_path, encoding='latin1')
        required_columns = ['Alias_Name', 'Standardized_Name']
        
        # Only process rows where Standardized_Name is filled in
        df = df.dropna(subset=required_columns)
        
        # Convert to string to avoid .str accessor errors
        df['Standardized_Name'] = df['Standardized_Name'].astype(str)
        df['Alias_Name'] = df['Alias_Name'].astype(str)
        
        # Filter out empty standardized names and identical names
        df = df[df['Standardized_Name'].str.strip() != '']
        df = df[df['Alias_Name'] != df['Standardized_Name']]
        
        if df.empty:
            logging.info(f"  No updates needed for {state_code} (no name changes)")
            return True
        
        # Connect and update
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                rows_updated = 0
                
                for _, row in df.iterrows():
                    old_name = row['Alias_Name']
                    new_name = row['Standardized_Name']
                    
                    # Update query
                    update_query = """
                    UPDATE Media_National_Champions
                    SET Team_Name = ?
                    WHERE Team_Name = ?
                    """
                    
                    cursor.execute(update_query, new_name, old_name)
                    rows_affected = cursor.rowcount
                    
                    if rows_affected > 0:
                        logging.info(f"  '{old_name}' → '{new_name}' ({rows_affected} rows)")
                        rows_updated += rows_affected
                
                if rows_updated > 0:
                    logging.info(f"SUCCESS: Updated {rows_updated} total rows in Media_National_Champions for {state_code}")
                else:
                    logging.info(f"  No matching rows found in Media_National_Champions for {state_code}")
        
        return True
        
    except Exception:
        logging.exception(f"Error updating Media_National_Champions for {state_code}")
        return False

def process_all_states():
    """Process all state alias files."""
    alias_files = get_all_alias_files()
    
    if not alias_files:
        logging.warning(f"No alias files found in {RULES_FOLDER}")
        return
    
    logging.info(f"Found {len(alias_files)} alias files to process.")
    
    success_count = 0
    error_count = 0
    
    for file_path in sorted(alias_files):
        state_code = extract_state_code_from_filename(file_path)
        logging.info(f"\n{'='*60}")
        logging.info(f"Processing: {os.path.basename(file_path)} [{state_code}]")
        logging.info(f"{'='*60}")
        
        result = update_media_national_champions_for_state(state_code, file_path)
        
        if result:
            success_count += 1
        else:
            error_count += 1
    
    logging.info(f"\n{'='*60}")
    logging.info(f"BATCH PROCESSING COMPLETE")
    logging.info(f"{'='*60}")
    logging.info(f"Successfully processed: {success_count} states")
    logging.info(f"Errors: {error_count} states")

if __name__ == "__main__":
    if not os.path.exists(RULES_FOLDER):
        logging.error(f"Rules folder not found: {RULES_FOLDER}")
        sys.exit(1)
    
    print("This will update Media_National_Champions for all states.")
    confirm = input("Continue? (y/n): ").lower()
    if confirm != 'y':
        logging.info("Operation cancelled by user.")
        sys.exit(0)
    
    process_all_states()