# apply_corrections.py - v3.0
# IMPROVEMENTS:
# 1. Now reads from the correct 'New_Alias_Suggestions.csv' file.
# 2. Connects directly to the DB to apply aliases automatically.

import os
import pandas as pd
import logging
from sqlalchemy import create_engine, text

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
# CORRECTED FILENAME
SUGGESTION_CSV = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv') 
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
GLOBAL_ALIAS_REGION = "*Global*"
# =================================================

# --- Boilerplate Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)
# === End Setup ===

def main():
    logger.info(f"Reading completed correction sheet from: {SUGGESTION_CSV}")

    try:
        df = pd.read_csv(SUGGESTION_CSV, encoding='utf-8-sig')
    except FileNotFoundError:
        logger.error(f"FATAL: Suggestion sheet not found at {SUGGESTION_CSV}")
        return

    # Filter for rows where a final decision has been made
    df.dropna(subset=['Final_Proper_Name'], inplace=True)
    df = df[df['Final_Proper_Name'].str.strip() != '']
    
    if df.empty:
        logger.warning("No rows with a 'Final_Proper_Name' found. Nothing to do.")
        return

    logger.info(f"Found {len(df)} completed aliases to apply to the database.")
    
    try:
        with engine.begin() as connection:
            logger.info("Successfully connected to the database to apply new rules.")
            for _, row in df.iterrows():
                alias_name = str(row.get('Unrecognized_Alias', '')).replace("'", "''")
                proper_name = str(row.get('Final_Proper_Name', '')).replace("'", "''")
                scope = str(row.get('Alias_Scope', 'Regional'))
                region = str(row.get('Newspaper_Region', '')).replace("'", "''")
                rule_type = str(row.get('Rule_Type', 'Alias')).strip().lower()

                if not alias_name or not proper_name: continue
                
                target_region = GLOBAL_ALIAS_REGION if scope.lower() == 'global' else region
                
                # Generate and execute SQL based on the rule type
                if rule_type == 'abbreviation':
                    logger.info(f"Applying ABBREVIATION rule: '{alias_name}' -> '{proper_name}' for region '{target_region}'")
                    sql_query = text(f"MERGE INTO dbo.HS_Team_Abbreviations AS T USING (SELECT '{alias_name}' AS A, '{proper_name}' AS S, '{target_region}' AS R) AS S ON T.Abbreviation = S.A AND T.Newspaper_Region = S.R WHEN NOT MATCHED THEN INSERT (Abbreviation, Standardized_Name, Newspaper_Region) VALUES (S.A, S.S, S.R);")
                else: # Default to creating a standard alias
                    logger.info(f"Applying ALIAS rule: '{alias_name}' -> '{proper_name}' for region '{target_region}'")
                    sql_query = text(f"EXEC sp_AddTeamAlias @AliasName = '{alias_name}', @StandardizedName = '{proper_name}', @NewspaperRegion = '{target_region}';")
                
                connection.execute(sql_query)

        logger.info(f"✅ Successfully applied {len(df)} new rules to the database.")
        logger.info("You can now re-run 'master_scores_importer.py' to complete the import.")

    except Exception as e:
        logger.exception(f"FATAL: An error occurred while applying corrections to the database: {e}")

if __name__ == "__main__":
    main()