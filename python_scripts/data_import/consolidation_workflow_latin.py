# consolidation_workflow_latin.py (v4 - With NaN Safety Guards)
import pandas as pd
import pyodbc
import logging
import os
import sys
import glob
from sqlalchemy import create_engine

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
RULES_FOLDER = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/excel_files/State_Aliases_ProperNames"
STAGING_TABLE_NAME = "ConsolidationRules_Staging"
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_state_code():
    """Prompts the user to enter a valid state code, or 'US' to process every state."""
    while True:
        state_abbr = input("Please enter the 2-letter state abbreviation (e.g., MD, MA) or 'US' for all states: ").upper()
        if state_abbr == "US":
            return "US"
        if len(state_abbr) == 2 and state_abbr.isalpha():
            return f"({state_abbr})"
        else:
            print("Invalid input. Please enter a 2-letter abbreviation or 'US'.")

def get_all_alias_files():
    """Returns every *_Alias_Rules.csv file in the rules folder (skips *_ACTIVE.csv working copies)."""
    pattern = os.path.join(RULES_FOLDER, "*_Alias_Rules.csv")
    return sorted(glob.glob(pattern))

def extract_state_code_from_filename(file_path):
    """Extracts the state code from a filename like 'MD_Alias_Rules.csv' and returns '(MD)'."""
    filename = os.path.basename(file_path)
    state_abbr = filename.split('_')[0]
    return f"({state_abbr})"

def generate_and_update_correction_file(state_code, file_path):
    """Calls the SQL procedure to get the list of problems and updates the CSV file with current GameCounts."""
    logging.info(f"Generating diagnostic list for state {state_code}...")
    
    # Step 1: Load existing file if it exists
    existing_df = None
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path, encoding='utf-8-sig')
            logging.info(f"Loaded existing file with {len(existing_df)} rows from {file_path}")
        except Exception:
            try:
                existing_df = pd.read_csv(file_path, encoding='latin1')
                logging.info(f"Loaded existing file (latin1 encoding) with {len(existing_df)} rows from {file_path}")
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
        
        # Save with UTF-8 BOM encoding to properly handle latin/special characters
        existing_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        logging.info(f"SUCCESS: Updated '{file_path}' with current GameCount values.")
        logging.info(f"Full file contains {len(existing_df)} total aliases:")
        logging.info(f"  - {active_count} active aliases (GameCount > 0)")
        logging.info(f"  - {zero_count} inactive aliases (GameCount = 0, ready for future imports)")
        
        # Create a filtered "working" file for easier review
        if active_count > 0:
            base_name = file_path.rsplit('.', 1)[0]
            working_file = f"{base_name}_ACTIVE.csv"
            active_df = existing_df[existing_df['GameCount'] > 0].copy()
            active_df.to_csv(working_file, index=False, encoding='utf-8-sig')
            logging.info(f"ALSO CREATED: '{working_file}' with only active aliases for easier review.")
        
    else:
        # Create new file from scratch
        new_rows = [{'Alias_Name': alias, 'GameCount': count, 'Standardized_Name': ''} 
                   for alias, count in current_counts.items()]
        new_df = pd.DataFrame(new_rows)
        new_df = new_df.sort_values('GameCount', ascending=False)
        new_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        logging.info(f"SUCCESS: Created new file '{file_path}' with {len(new_df)} aliases.")
    
    logging.info("Please open the file, fill in the 'Standardized_Name' column for any names you want to consolidate, and save it.")
    return True

def validate_rules(df_to_upload):
    """
    Validates consolidation rules before uploading to staging table.
    Returns True if all rules are valid, False if any issues found.
    
    This guard prevents the literal string 'nan' (which pandas dropna() does NOT catch)
    from being written to the database as a team name.
    """
    issues_found = False

    # Guard 1: Reject literal 'nan' strings — pandas dropna() misses these
    nan_rows = df_to_upload[df_to_upload['NewName'].str.strip().str.lower() == 'nan']
    if not nan_rows.empty:
        logging.error(f"VALIDATION FAILED: {len(nan_rows)} row(s) have the literal string 'nan' as NewName.")
        logging.error("This typically means the CSV has encoding issues or a cell was left as 'nan' by mistake.")
        for _, row in nan_rows.iterrows():
            logging.error(f"  OldName='{row['OldName']}' -> NewName='{row['NewName']}'")
        issues_found = True

    # Guard 2: Reject empty or whitespace-only NewName
    empty_rows = df_to_upload[df_to_upload['NewName'].str.strip() == '']
    if not empty_rows.empty:
        logging.error(f"VALIDATION FAILED: {len(empty_rows)} row(s) have an empty NewName.")
        for _, row in empty_rows.iterrows():
            logging.error(f"  OldName='{row['OldName']}' -> NewName='{row['NewName']}'")
        issues_found = True

    # Guard 3: Reject OldName == NewName (no-op rules that waste processing)
    same_rows = df_to_upload[df_to_upload['OldName'].str.strip() == df_to_upload['NewName'].str.strip()]
    if not same_rows.empty:
        logging.warning(f"WARNING: {len(same_rows)} row(s) have identical OldName and NewName (no-op rules).")
        for _, row in same_rows.iterrows():
            logging.warning(f"  '{row['OldName']}' -> '{row['NewName']}' (no change)")

    if issues_found:
        logging.error("ABORTED: Fix the CSV file and re-run. Nothing was uploaded to the database.")
        return False

    logging.info(f"Validation passed: {len(df_to_upload)} rules are clean and ready to upload.")
    return True

def run_consolidation_from_staging(state_code, file_path, reason=None):
    """Uploads rules to a staging table and then executes the consolidation procedure.

    `reason` is passed through to dbo.sp_ConsolidateNames_FromStaging's optional
    @Reason parameter (added in V8, 2026-09-12), which logs it to
    dbo.HS_Consolidation_Log alongside each rule's before/after names and row
    counts. None/blank is fine -- @Reason defaults to NULL in the procedure,
    same as before this parameter existed -- but supplying one here is now the
    normal way to record *why* a given consolidation run happened, instead of
    that context only ever living in whoever's memory ran it."""
    logging.info(f"Starting consolidation for state: {state_code} using staging table method.")
    
    try:
        # Step 1: Upload CSV to a staging table
        # Try UTF-8 first (handles latin/special characters properly), fall back to latin1
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(file_path, encoding='latin1')
            logging.warning("File read with latin1 encoding. Consider re-saving as UTF-8 for better special character support.")

        required_columns = ['Alias_Name', 'Standardized_Name']
        
        # Only process rows where Standardized_Name is filled in
        df.dropna(subset=required_columns, inplace=True)
        df = df[df['Standardized_Name'].str.strip() != '']
        
        # Prepare dataframe for upload
        df_to_upload = df[required_columns].rename(columns={'Alias_Name': 'OldName', 'Standardized_Name': 'NewName'})
        
        if df_to_upload.empty:
            logging.warning("No completed rules found in the correction file. Nothing to process.")
            return

        # ============================================================
        # SAFETY VALIDATION — catches literal 'nan' and other bad values
        # that bypass pandas dropna() and would corrupt the database.
        # Must pass before anything is uploaded to staging.
        # ============================================================
        if not validate_rules(df_to_upload):
            return
        # ============================================================

        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        engine = create_engine(f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes')
        
        logging.info(f"Uploading {len(df_to_upload)} rules to staging table: {STAGING_TABLE_NAME}...")
        # 2026-09-15: root cause was pandas 2.3.3 + SQLAlchemy 1.4.46 in this
        # venv -- confirmed via an isolated sqlite-only repro that this broke
        # to_sql() against ANY SQLAlchemy connectable, not just this script's
        # mssql/pyodbc engine (my first attempted fix, wrapping in
        # engine.begin(), didn't help -- pandas wasn't recognizing SQLAlchemy
        # objects at all, regardless of Engine vs Connection). Real fix was
        # upgrading SQLAlchemy to 2.0.53 in this venv (the version pandas 2.x
        # is actually built/tested against), so the original bare-engine
        # pattern works again and needs no script-level workaround.
        df_to_upload.to_sql(STAGING_TABLE_NAME, con=engine, if_exists='replace', index=False)
        logging.info("Upload to staging table complete.")

        # Step 2: Execute the stored procedure that uses the staging table
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                logging.info("Executing dbo.sp_ConsolidateNames_FromStaging...")
                cursor.execute("EXEC dbo.sp_ConsolidateNames_FromStaging @StateCode = ?, @Reason = ?", state_code, reason)
                logging.info("SUCCESS: Consolidation from staging table is complete.")
                if reason:
                    logging.info(f"Reason logged to dbo.HS_Consolidation_Log: {reason}")
                else:
                    logging.info("No reason supplied -- dbo.HS_Consolidation_Log rows for this run will have Reason = NULL.")
                logging.info("TIP: Run option 1 again to refresh GameCount values and see which aliases remain.")

        # ============================================================
        # POST-RUN VERIFICATION — confirms no 'nan' values exist in
        # HS_Scores after the procedure runs.
        # ============================================================
        logging.info("Running post-consolidation safety check...")
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM HS_Scores
                    WHERE Home = 'nan' OR Visitor = 'nan'
                """)
                nan_count = cursor.fetchone()[0]
                if nan_count > 0:
                    logging.error(f"POST-RUN WARNING: {nan_count} rows with 'nan' detected in HS_Scores!")
                    logging.error("Immediate action required — review ConsolidationRules_Staging for bad NewName values.")
                else:
                    logging.info("POST-RUN CHECK PASSED: No 'nan' values found in HS_Scores.")
        # ============================================================

    except Exception:
        logging.exception("An error occurred during the consolidation process.")

def run_all_states_generate():
    """Runs option 1 (generate/update correction file) against every state's alias file."""
    alias_files = get_all_alias_files()
    if not alias_files:
        logging.warning(f"No alias files found in {RULES_FOLDER}")
        return
    logging.info(f"Found {len(alias_files)} state alias files. Refreshing GameCount for each...")
    for file_path in alias_files:
        state_code = extract_state_code_from_filename(file_path)
        logging.info(f"\n{'='*60}\nGenerating: {os.path.basename(file_path)} [{state_code}]\n{'='*60}")
        generate_and_update_correction_file(state_code, file_path)

def run_all_states_consolidation(reason=None):
    """Runs option 2 (consolidate from staging) against every state's alias file.

    Reuses run_consolidation_from_staging() as-is for each state, one state at a
    time -- including its NaN-safety validation guard and its post-run check --
    so 'US' gets exactly the same safety behavior as running a single state by
    hand, just looped."""
    alias_files = get_all_alias_files()
    if not alias_files:
        logging.warning(f"No alias files found in {RULES_FOLDER}")
        return

    logging.info(f"Found {len(alias_files)} state alias files to consolidate.")
    success_count = 0
    error_count = 0
    for file_path in alias_files:
        state_code = extract_state_code_from_filename(file_path)
        logging.info(f"\n{'='*60}\nProcessing: {os.path.basename(file_path)} [{state_code}]\n{'='*60}")
        try:
            run_consolidation_from_staging(state_code, file_path, reason=reason)
            success_count += 1
        except Exception:
            logging.exception(f"Failed processing {state_code}")
            error_count += 1

    logging.info(f"\n{'='*60}\nBATCH (US) PROCESSING COMPLETE\n{'='*60}")
    logging.info(f"States processed without a raised exception: {success_count}")
    logging.info(f"States with an unhandled error: {error_count}")
    logging.info("Note: a state can appear 'processed' above and still have logged its own")
    logging.info("VALIDATION FAILED / ABORTED message if that state's file had bad rows --")
    logging.info("scroll up for any per-state ABORTED lines rather than trusting this count alone.")

if __name__ == "__main__":
    # Main Workflow Logic
    if not os.path.exists(RULES_FOLDER):
        os.makedirs(RULES_FOLDER)

    state_code = get_state_code()

    if state_code == "US":
        print("\n'US' selected - will process every *_Alias_Rules.csv file in the rules folder.")
        print("\nSelect an action:")
        print("1: Generate or Update the correction file for every state (refreshes GameCount, filters out unused aliases).")
        print("2: Run the consolidation using each state's completed correction file.")

        while True:
            action = input("Enter your choice (1 or 2): ")
            if action in ['1', '2']:
                break
            else:
                print("Invalid choice.")

        if action == '1':
            run_all_states_generate()
        elif action == '2':
            reason = input("Reason for this consolidation run, applied to every state (optional, press Enter to skip): ").strip()
            run_all_states_consolidation(reason=reason if reason else None)
    else:
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
                reason = input("Reason for this consolidation run (optional, press Enter to skip): ").strip()
                run_consolidation_from_staging(state_code, correction_file_path, reason=reason or None)
