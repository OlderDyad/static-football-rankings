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
        # FIX: Added encoding='latin1' to handle manual file edits.
        df = pd.read_csv(file_path, encoding='latin1') 
        required_columns = ['Alias_Name', 'Standardized_Name']
        df.dropna(subset=required_columns, inplace=True)
        df = df[df['Standardized_Name'].str.strip() != '']
        
        # Prepare dataframe for upload
        df_to_upload = df[required_columns].rename(columns={'Alias_Name': 'OldName', 'Standardized_Name': 'NewName'})
        
        if df_to_upload.empty:
            logging.warning("No completed rules found in the correction file. Nothing to process.")
            return

        engine = create_engine(f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL Server&trusted_connection=yes')
        
        logging.info(f"Uploading {len(df_to_upload)} rules to staging table: {STAGING_TABLE_NAME}...")
        df_to_upload.to_sql(STAGING_TABLE_NAME, con=engine, if_exists='replace', index=False)
        logging.info("Upload to staging table complete.")

        # Step 2: Execute the stored procedure that uses the staging table
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                logging.info("Executing dbo.sp_ConsolidateNames_FromStaging...")
                # Note: This executes the name change AND clears the geocodes for the old names.
                cursor.execute("EXEC dbo.sp_ConsolidateNames_FromStaging @StateCode = ?", state_code) 
                logging.info("SUCCESS: Consolidation from staging table is complete.")

    except Exception:
        logging.exception("An error occurred during the consolidation process.")

        # Step 2: Execute the stored procedure that uses the staging table
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                logging.info("Executing dbo.sp_ConsolidateNames_FromStaging...")
                cursor.execute("EXEC dbo.sp_ConsolidateNames_FromStaging @StateCode = ?", state_code)
                logging.info("SUCCESS: Consolidation from staging table is complete.")

    except Exception:
        logging.exception("An error occurred during the consolidation process.")

# --- ADDED: Dual-purpose function (handles global list without SP) ---
def generate_global_cleanup_file(file_path):
    """
    Generates a list of all names where Latitude IS NULL (Global Geocoding List)
    with a true GameCount.
    """
    logging.info("Generating global geocoding cleanup list...")
    
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            
            # The corrected query using [ID], [Home], and [Visitor]
            query = """
            SELECT
                t.[Team_Name],
                COUNT(s.[ID]) AS GameCount
            FROM
                [dbo].[HS_Team_Names] t
            LEFT JOIN
                [dbo].[HS_Scores] s ON t.[Team_Name] = s.[Home] OR t.[Team_Name] = s.[Visitor]
            WHERE
                t.Latitude IS NULL
            GROUP BY
                t.[Team_Name]
            ORDER BY
                GameCount DESC;
            """
            
            df_problems = pd.read_sql(query, conn)
            
    except Exception:
        logging.exception("Failed to run global diagnostic query.")
        return False

    if not df_problems.empty:
        # Check if the dataframe contains the GameCount column before renaming
        if 'GameCount' not in df_problems.columns:
             logging.error("Query failed to return 'GameCount' column. Check SQL column names.")
             return False
             
        df_problems.rename(columns={'Team_Name': 'Alias_Name'}, inplace=True)
        df_problems['Standardized_Name'] = ''
        
        # Save the new list
        # Note: The original file creation logic is preserved here.
        df_problems.to_csv(file_path, index=False)
        logging.info(f"SUCCESS: The global file '{file_path}' has been created with {len(df_problems)} problematic names.")
        logging.info("Please open the file, fill in the 'Standardized_Name' column, and save it.")
    else:
        logging.info("No missing geolocations found. Database is fully geocoded!")
    
    return True

if __name__ == "__main__":
    # Main Workflow Logic
    # ... (code for RULES_FOLDER check remains unchanged) ...

    print("\nSelect an action:")
    print("1: Generate/Update correction file for a specific STATE (uses SP).")
    print("2: Run consolidation for a specific STATE (uses staging table).")
    print("3: Generate GLOBAL correction file (Missing Latitudes).")
    
    while True:
        action = input("Enter your choice (1, 2, or 3): ")
        if action in ['1', '2', '3']:
            break
        else:
            print("Invalid choice.")
    
    # --- GET CODE/DEFINE PATH BASED ON ACTION ---
    if action in ['1', '2']:
        state_code_display = get_state_code() # Prompts for state code (e.g., "(TX)")
        file_name = f"{state_code_display.strip('()')}_Alias_Rules.csv"
    elif action == '3':
        # --- AUTOMATICALLY SET STATE CODE FOR GLOBAL GEOLOCATION ---
        state_code_display = "(LL)" # Sets the code to (LL)
        file_name = "LL_Alias_Rules.csv" # Forces the filename to LL_Alias_Rules.csv

    correction_file_path = os.path.join(RULES_FOLDER, file_name)

    # --- EXECUTE ACTIONS ---
    if action == '1':
        # Executes the original state-specific stored procedure (SP) logic
        generate_and_update_correction_file(state_code_display, correction_file_path)
    
    elif action == '2':
        # Executes the original state-specific consolidation logic
        if not os.path.exists(correction_file_path):
            logging.error(f"Correction file not found at {correction_file_path}. Please run option 1 or 3 first.")
        else:
            run_consolidation_from_staging(state_code_display, correction_file_path)
    
    elif action == '3':
        # Executes the new global geocoding cleanup logic
        generate_global_cleanup_file(correction_file_path)