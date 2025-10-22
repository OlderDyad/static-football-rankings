# consolidation_workflow.py (Interactive Version)
import pandas as pd
import pyodbc
import logging
import os
import sys

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
# This is the dedicated folder for your state-specific correction files
RULES_FOLDER = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/excel_files/State_Aliases_ProperNames"
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
            existing_aliases = set(df_existing['Alias_Name'])
            logging.info(f"Loaded {len(existing_aliases)} existing aliases from {file_path}")
        except Exception:
            logging.warning(f"Could not read existing file at {file_path}. A new file will be created.")

    new_problem_names = []
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                # This executes the new, combined diagnostic procedure
                cursor.execute("EXEC dbo.sp_CreateStateCleanupList @StateCode = ?", state_code)
                
                # The first result set is SOUNDEX, we can just skip it for the file
                cursor.nextset() 
                
                # The second result set is the one we want for our file
                rows = cursor.fetchall()
                for row in rows:
                    if row.TeamName not in existing_aliases:
                        new_problem_names.append(row.TeamName)
    except Exception as e:
        logging.exception("Failed to run diagnostic procedure.")
        return False

    if new_problem_names:
        logging.info(f"Found {len(new_problem_names)} new problematic names to add to the correction file.")
        new_rows_df = pd.DataFrame({
            'Alias_Name': new_problem_names,
            'Standardized_Name': ''  # Leave blank for user to fill in
        })
        
        # Append to existing file or create a new one
        new_rows_df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        logging.info(f"SUCCESS: The file '{file_path}' has been created/updated.")
        logging.info("Please open the file, fill in the 'Standardized_Name' column, and save it.")
    else:
        logging.info("No new problematic names found. Your correction file is up to date.")
    
    return True

def run_consolidation(state_code, file_path):
    """Reads the completed correction file and runs the consolidation procedures."""
    logging.info(f"Starting consolidation for state: {state_code} from file: {file_path}")
    
    try:
        df = pd.read_csv(file_path)
        df.dropna(subset=['Alias_Name', 'Standardized_Name'], inplace=True)
        # Filter out rows where Standardized_Name is still blank
        df = df[df['Standardized_Name'].str.strip() != '']
        
        records_to_process = [tuple(x) for x in df[['Alias_Name', 'Standardized_Name']].to_numpy()]
        
        if not records_to_process:
            logging.warning("No completed rules found in the correction file. Nothing to process.")
            return

        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                logging.info(f"Executing main consolidation with {len(records_to_process)} rules...")
                cursor.execute("EXEC dbo.sp_ConsolidateTeamNames @CorrectionList = ?, @StateCode = ?", records_to_process, state_code)
                
                logging.info("Finalizing canonical names...")
                cursor.execute("EXEC dbo.sp_FinalizeCanonicalNames @CorrectionList = ?", [records_to_process])
                
                conn.commit()
                logging.info("SUCCESS: Consolidation complete. All changes have been committed.")

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
            run_consolidation(state_code, correction_file_path)



