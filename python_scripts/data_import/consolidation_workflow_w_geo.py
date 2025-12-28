# geocoding_consolidation_workflow.py
"""
Special workflow for updating team names that are missing latitude/longitude data.
This uses the (LL) state code to manage geocoding cleanup.
"""
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
GEOCODING_FILE = "LL_Alias_Rules.csv"
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_global_cleanup_file(file_path):
    """
    Generates a list of all team names where Latitude IS NULL (Global Geocoding List)
    with actual GameCount from HS_Scores table.
    """
    logging.info("Generating global geocoding cleanup list...")
    
    # Step 1: Load existing file if it exists
    existing_df = None
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path, encoding='latin1')
            logging.info(f"Loaded existing file with {len(existing_df)} rows from {file_path}")
        except Exception:
            logging.warning(f"Could not read existing file at {file_path}. A new file will be created.")
    
    # Step 2: Get current game counts from database for teams missing geocodes
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            # Query for teams missing latitude with their game counts
            query = """
            SELECT
                t.[Team_Name] AS Alias_Name,
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
            logging.info(f"Retrieved {len(df_problems)} teams missing geocodes from database.")
            
    except Exception:
        logging.exception("Failed to run global diagnostic query.")
        return False

    if df_problems.empty:
        logging.info("No missing geolocations found. Database is fully geocoded!")
        return True
    
    # Step 3: Process the data
    if existing_df is not None:
        # Update existing GameCount values
        existing_df['GameCount'] = existing_df['Alias_Name'].map(
            dict(zip(df_problems['Alias_Name'], df_problems['GameCount']))
        ).fillna(0).astype(int)
        
        # Add any new names that aren't in the existing file
        existing_aliases = set(existing_df['Alias_Name'])
        new_aliases = set(df_problems['Alias_Name']) - existing_aliases
        
        if new_aliases:
            new_rows = df_problems[df_problems['Alias_Name'].isin(new_aliases)].copy()
            new_rows['Standardized_Name'] = ''
            existing_df = pd.concat([existing_df, new_rows], ignore_index=True)
            logging.info(f"Added {len(new_aliases)} new teams to the file.")
        
        # Count active vs inactive
        zero_count = len(existing_df[existing_df['GameCount'] == 0])
        active_count = len(existing_df[existing_df['GameCount'] > 0])
        
        if zero_count > 0:
            logging.info(f"Found {zero_count} teams with GameCount = 0 (already geocoded, kept for reference).")
        
        # Sort by GameCount (descending)
        existing_df = existing_df.sort_values(['GameCount'], ascending=[False])
        
        # Save the FULL file
        existing_df.to_csv(file_path, index=False, encoding='latin1')
        logging.info(f"SUCCESS: Updated '{file_path}' with current GameCount values.")
        logging.info(f"Full file contains {len(existing_df)} total teams:")
        logging.info(f"  - {active_count} teams missing geocodes (GameCount > 0)")
        logging.info(f"  - {zero_count} teams already geocoded (GameCount = 0)")
        
        # Create filtered "active" file
        if active_count > 0:
            base_name = file_path.rsplit('.', 1)[0]
            working_file = f"{base_name}_ACTIVE.csv"
            active_df = existing_df[existing_df['GameCount'] > 0].copy()
            active_df.to_csv(working_file, index=False, encoding='latin1')
            logging.info(f"ALSO CREATED: '{working_file}' with only teams needing geocodes for easier review.")
    else:
        # Create new file from scratch
        df_problems['Standardized_Name'] = ''
        df_problems.to_csv(file_path, index=False, encoding='latin1')
        logging.info(f"SUCCESS: Created new file '{file_path}' with {len(df_problems)} teams missing geocodes.")
    
    logging.info("Please open the file, fill in the 'Standardized_Name' column for teams to consolidate, and save it.")
    return True

def run_consolidation_from_staging(file_path):
    """Uploads rules to staging table and executes the consolidation procedure for geocoding cleanup."""
    logging.info("Starting geocoding consolidation using staging table method.")
    
    try:
        # Step 1: Upload CSV to staging table
        df = pd.read_csv(file_path, encoding='latin1')
        required_columns = ['Alias_Name', 'Standardized_Name']
        
        # Convert to string to avoid .str accessor errors
        df['Standardized_Name'] = df['Standardized_Name'].astype(str)
        df['Alias_Name'] = df['Alias_Name'].astype(str)
        
        # Only process rows where Standardized_Name is filled in
        df = df.dropna(subset=required_columns)
        df = df[df['Standardized_Name'].str.strip() != '']
        
        # Prepare dataframe for upload
        df_to_upload = df[required_columns].rename(columns={'Alias_Name': 'OldName', 'Standardized_Name': 'NewName'})
        
        if df_to_upload.empty:
            logging.warning("No completed rules found in the correction file. Nothing to process.")
            return False

        engine = create_engine(f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes')
        
        logging.info(f"Uploading {len(df_to_upload)} rules to staging table: {STAGING_TABLE_NAME}...")
        df_to_upload.to_sql(STAGING_TABLE_NAME, con=engine, if_exists='replace', index=False)
        logging.info("Upload to staging table complete.")

        # Step 2: Execute the stored procedure (uses (LL) as state code)
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                logging.info("Executing dbo.sp_ConsolidateNames_FromStaging with state code (LL)...")
                cursor.execute("EXEC dbo.sp_ConsolidateNames_FromStaging @StateCode = ?", "(LL)")
                logging.info("SUCCESS: Geocoding consolidation complete.")
                logging.info("Note: This clears geocodes for old names - they will need to be re-geocoded.")
        
        return True

    except Exception:
        logging.exception("An error occurred during the geocoding consolidation process.")
        return False

if __name__ == "__main__":
    if not os.path.exists(RULES_FOLDER):
        os.makedirs(RULES_FOLDER)

    correction_file_path = os.path.join(RULES_FOLDER, GEOCODING_FILE)

    print("\n=== GEOCODING CONSOLIDATION WORKFLOW ===")
    print("This workflow manages team names that are missing latitude/longitude data.")
    print("\nSelect an action:")
    print("1: Generate or Update the geocoding correction file (LL_Alias_Rules.csv).")
    print("2: Run the consolidation using the completed correction file.")
    
    while True:
        action = input("Enter your choice (1 or 2): ")
        if action in ['1', '2']:
            break
        else:
            print("Invalid choice.")

    if action == '1':
        generate_global_cleanup_file(correction_file_path)
    elif action == '2':
        if not os.path.exists(correction_file_path):
            logging.error(f"Correction file not found at {correction_file_path}. Please run option 1 first.")
        else:
            run_consolidation_from_staging(correction_file_path)