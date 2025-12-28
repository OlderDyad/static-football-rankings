# consolidation_workflow.py (v3 - With GameCount Updates and Filtering)
import pandas as pd
import pyodbc
import logging
import os
import sys
from sqlalchemy import create_engine

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
RULES_FOLDER = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/excel_files/State_Aliases_ProperNames"
STAGING_TABLE_NAME = "ConsolidationRules_Staging"
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_state_code():
    """Prompts the user to enter a valid state code."""
    while True:
        state_abbr = input("Please enter the 2-letter state abbreviation (e.g., MD, MA): ").upper()
        if len(state_abbr) == 2 and state_abbr.isalpha():
            return f"({state_abbr})"
        else:
            print("Invalid input. Please enter a 2-letter abbreviation.")

def generate_and_update_correction_file(state_code, file_path):
    """Calls the SQL procedure to get the list of problems and updates the CSV file with current GameCounts."""
    logging.info(f"Generating diagnostic list for state {state_code}...")
    
    # Step 1: Load existing file if it exists
    existing_df = None
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path, encoding='latin1')
            logging.info(f"Loaded existing file with {len(existing_df)} rows from {file_path}")
        except Exception:
            logging.warning(f"Could not read existing file at {file_path}. A new file will be created.")

    # Step 2: Get current game counts from database
    current_counts = {}
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute("EXEC dbo.sp_CreateStateCleanupList @StateCode = ?", state_code)
                cursor.nextset() # Skip SOUNDEX results
                
                rows = cursor.fetchall()
                for row in rows:
                    current_counts[row.TeamName] = row.GameCount
                
                logging.info(f"Retrieved current game counts for {len(current_counts)} team names from database.")
    except Exception:
        logging.exception("Failed to run diagnostic procedure.")
        return False

    # Step 3: Process the data
    if existing_df is not None:
        # Update existing GameCount values
        existing_df['GameCount'] = existing_df['Alias_Name'].map(current_counts).fillna(0).astype(int)
        
        # Add any new names that aren't in the existing file
        existing_aliases = set(existing_df['Alias_Name'])
        new_aliases = set(current_counts.keys()) - existing_aliases
        
        if new_aliases:
            new_rows = [{'Alias_Name': alias, 'GameCount': current_counts[alias], 'Standardized_Name': ''} 
                       for alias in new_aliases]
            new_rows_df = pd.DataFrame(new_rows)
            existing_df = pd.concat([existing_df, new_rows_df], ignore_index=True)
            logging.info(f"Added {len(new_aliases)} new aliases to the file.")
        
        # Count how many have zero occurrences
        zero_count = len(existing_df[existing_df['GameCount'] == 0])
        active_count = len(existing_df[existing_df['GameCount'] > 0])
        
        if zero_count > 0:
            logging.info(f"Found {zero_count} aliases with GameCount = 0 (already replaced, kept for future imports).")
        
        # Sort: Active aliases first (by GameCount descending), then zero-count aliases at bottom
        existing_df = existing_df.sort_values(['GameCount'], ascending=[False])
        
        # Save the FULL file (including zero-count rows)
        existing_df.to_csv(file_path, index=False, encoding='latin1')
        logging.info(f"SUCCESS: Updated '{file_path}' with current GameCount values.")
        logging.info(f"Full file contains {len(existing_df)} total aliases:")
        logging.info(f"  - {active_count} active aliases (GameCount > 0)")
        logging.info(f"  - {zero_count} inactive aliases (GameCount = 0, ready for future imports)")
        
        # Create a filtered "working" file for easier review
        if active_count > 0:
            base_name = file_path.rsplit('.', 1)[0]
            working_file = f"{base_name}_ACTIVE.csv"
            active_df = existing_df[existing_df['GameCount'] > 0].copy()
            active_df.to_csv(working_file, index=False, encoding='latin1')
            logging.info(f"ALSO CREATED: '{working_file}' with only active aliases for easier review.")
        
    else:
        # Create new file from scratch
        new_rows = [{'Alias_Name': alias, 'GameCount': count, 'Standardized_Name': ''} 
                   for alias, count in current_counts.items()]
        new_df = pd.DataFrame(new_rows)
        new_df = new_df.sort_values('GameCount', ascending=False)
        new_df.to_csv(file_path, index=False, encoding='latin1')
        logging.info(f"SUCCESS: Created new file '{file_path}' with {len(new_df)} aliases.")
    
    logging.info("Please open the file, fill in the 'Standardized_Name' column for any names you want to consolidate, and save it.")
    return True

def run_consolidation_from_staging(state_code, file_path):
    """Uploads rules to a staging table and then executes the consolidation procedure."""
    logging.info(f"Starting consolidation for state: {state_code} using staging table method.")
    
    try:
        # Step 1: Upload CSV to a staging table
        df = pd.read_csv(file_path, encoding='latin1') 
        required_columns = ['Alias_Name', 'Standardized_Name']
        
        # Only process rows where Standardized_Name is filled in
        df.dropna(subset=required_columns, inplace=True)
        df = df[df['Standardized_Name'].str.strip() != '']
        
        # Prepare dataframe for upload
        df_to_upload = df[required_columns].rename(columns={'Alias_Name': 'OldName', 'Standardized_Name': 'NewName'})
        
        if df_to_upload.empty:
            logging.warning("No completed rules found in the correction file. Nothing to process.")
            return

        engine = create_engine(f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes')
        
        logging.info(f"Uploading {len(df_to_upload)} rules to staging table: {STAGING_TABLE_NAME}...")
        df_to_upload.to_sql(STAGING_TABLE_NAME, con=engine, if_exists='replace', index=False)
        logging.info("Upload to staging table complete.")

        # Step 2: Execute the stored procedure that uses the staging table
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                logging.info("Executing dbo.sp_ConsolidateNames_FromStaging...")
                cursor.execute("EXEC dbo.sp_ConsolidateNames_FromStaging @StateCode = ?", state_code)
                logging.info("SUCCESS: Consolidation from staging table is complete.")
                logging.info("TIP: Run option 1 again to refresh GameCount values and see which aliases remain.")

    except Exception:
        logging.exception("An error occurred during the consolidation process.")

if __name__ == "__main__":
    # Main Workflow Logic
    if not os.path.exists(RULES_FOLDER):
        os.makedirs(RULES_FOLDER)

    state_code = get_state_code()
    file_name = f"{state_code.strip('()')}_Alias_Rules.csv"
    correction_file_path = os.path.join(RULES_FOLDER, file_name)

    print("\nSelect an action:")
    print("1: Generate or Update the correction file for this state (refreshes GameCount, filters out unused aliases).")
    print("2: Run the consolidation using the completed correction file for this state.")
    
    while True:
        action = input("Enter your choice (1 or 2): ")
        if action in ['1', '2']:
            break
        else:
            print("Invalid choice.")

    if action == '1':
        generate_and_update_correction_file(state_code, correction_file_path)
    elif action == '2':
        if not os.path.exists(correction_file_path):
            logging.error(f"Correction file not found at {correction_file_path}. Please run option 1 first.")
        else:
            run_consolidation_from_staging(state_code, correction_file_path)