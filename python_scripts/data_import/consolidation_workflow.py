# consolidation_workflow.py (v2 - Staging Table Method)
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
    """Calls the SQL procedure to get the list of problems and updates the CSV file."""
    logging.info(f"Generating diagnostic list for state {state_code}...")
    
    existing_aliases = set()
    if os.path.exists(file_path):
        try:
            df_existing = pd.read_csv(file_path)
            if 'Alias_Name' in df_existing.columns:
                existing_aliases = set(df_existing['Alias_Name'])
                logging.info(f"Loaded {len(existing_aliases)} existing aliases from {file_path}")
        except Exception:
            logging.warning(f"Could not read existing file at {file_path}. A new file will be created.")

    new_problem_rows = []
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute("EXEC dbo.sp_CreateStateCleanupList @StateCode = ?", state_code)
                cursor.nextset() # Skip SOUNDEX results
                
                rows = cursor.fetchall()
                for row in rows:
                    if row.TeamName not in existing_aliases:
                        # Append the name and the game count
                        new_problem_rows.append({'Alias_Name': row.TeamName, 'GameCount': row.GameCount, 'Standardized_Name': ''})
    except Exception:
        logging.exception("Failed to run diagnostic procedure.")
        return False

    if new_problem_rows:
        logging.info(f"Found {len(new_problem_rows)} new problematic names to add to the correction file.")
        new_rows_df = pd.DataFrame(new_problem_rows)
        
        # Append to existing file or create a new one with the correct 3 columns
        new_rows_df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        logging.info(f"SUCCESS: The file '{file_path}' has been created/updated with a 'GameCount' column.")
        logging.info("Please open the file, fill in the 'Standardized_Name' column, and save it.")
    else:
        logging.info("No new problematic names found. Your correction file is up to date.")
    
    return True

def run_consolidation_from_staging(state_code, file_path):
    """Uploads rules to a staging table and then executes the consolidation procedure."""
    logging.info(f"Starting consolidation for state: {state_code} using staging table method.")
    
    try:
        # Step 1: Upload CSV to a staging table
        df = pd.read_csv(file_path)
        required_columns = ['Alias_Name', 'Standardized_Name']
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
    print("1: Generate or Update the correction file for this state.")
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