# === IMPORTS ===
import os
import pandas as pd
import re
from sqlalchemy import create_engine, text
import numpy as np
from datetime import datetime
import csv
from pathlib import Path # Not explicitly used, but good for path manipulations if needed later
import logging
# === END IMPORTS ===

# === LOGGING CONFIGURATION ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# === END LOGGING CONFIGURATION ===

# === DATABASE CONNECTION PARAMETERS ===
server = 'McKnights-PC\\SQLEXPRESS01'
database = 'hs_football_database'
driver = 'ODBC Driver 17 for SQL Server'
connection_string = f'mssql+pyodbc://{server}/{database}?driver={driver}&trusted_connection=yes'
engine = create_engine(connection_string)
# === END DATABASE CONNECTION PARAMETERS ===

# === GLOBAL CONFIGURATION ===
current_state = 'NY'
ocr_files_path = 'J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged'
output_path = ocr_files_path
# === END GLOBAL CONFIGURATION ===

# === HELPER FUNCTION: clean_text ===
def clean_text(text_input):
    """Clean and normalize text for comparison"""
    if pd.isna(text_input):
        return ''
    cleaned = re.sub(r'[^\w\s]', '', str(text_input).lower())
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
# === END HELPER FUNCTION: clean_text ===

# === HELPER FUNCTION: validate_filename ===
def validate_filename(filename):
    """Validate OCR filename format - flexible version"""
    # This pattern handles both formats
    pattern = r'^(.+?)_(\d{4})_(\d{2})_(\d{2})_(?:Page_)?\d+\.txt$'
    match = re.match(pattern, filename)
    
    if not match:
        logger.warning(f"Invalid filename format: {filename}")
        return {
            'newspaper_info': filename.replace('.txt', ''),
            'year': None, 'month': None, 'day': None
        }
    
    return {
        'newspaper_info': match.group(1),
        'year': match.group(2),
        'month': match.group(3),
        'day': match.group(4)
    }
# === END HELPER FUNCTION: validate_filename ===

# === HELPER FUNCTION: get_newspaper_region ===
def get_newspaper_region(filename):
    """Extract newspaper region from filename"""
    file_info = validate_filename(filename)
    newspaper_info = file_info['newspaper_info']
    newspaper_region = newspaper_info.replace('_', ' ').strip()
    return newspaper_region
# === END HELPER FUNCTION: get_newspaper_region ===

# === HELPER FUNCTION: load_aliases_by_state ===
def load_aliases_by_state(state_param='NY'):
    """Load aliases filtered by state. Returns an empty DataFrame on error."""
    query_string = text("""
    SELECT Alias_Name, Standardized_Name, Newspaper_Region,
           Newspaper_City, Newspaper_State
    FROM dbo.HS_Team_Name_Alias
    WHERE Newspaper_State = :state_val AND Newspaper_Region IS NOT NULL
    """)
    
    try:
        df = pd.read_sql(query_string, engine, params={'state_val': state_param})
        if df is None:
            logger.warning(f"pd.read_sql returned None for state: {state_param}. Returning empty DataFrame.")
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.error(f"Error executing SQL query in load_aliases_by_state for state '{state_param}': {e}")
        return pd.DataFrame()
# === END HELPER FUNCTION: load_aliases_by_state ===

# === HELPER FUNCTION: debug_aliases ===
def debug_aliases(newspaper_aliases_dict, target_region='Newsday Nassau Edition'):
    """Debug function to check loaded aliases for a specific region."""
    print(f"\n--- Debugging Aliases for Region: '{target_region}' ---")
    stripped_target_region = target_region.strip()
    region_to_check = None

    if target_region in newspaper_aliases_dict:
        region_to_check = target_region
    elif stripped_target_region in newspaper_aliases_dict:
        region_to_check = stripped_target_region
        print(f"(Note: Found aliases using stripped region name: '{stripped_target_region}')")

    if region_to_check:
        aliases_for_region = newspaper_aliases_dict[region_to_check]
        print(f"Total aliases loaded for this region ('{region_to_check}'): {len(aliases_for_region)}")
        
        test_raw_aliases = [ # List of raw team names you are testing
            'Carte Place', 
            'Dalton School', 
            'E Hampton/Br/Pier.', 
            "Greenport/S'hold",
            'Whitmarr'
        ]
        
        found_count = 0
        for raw_alias in test_raw_aliases:
            normalized_alias_key = clean_text(raw_alias) 
            if normalized_alias_key in aliases_for_region:
                print(f"  ✅ Found normalized: '{normalized_alias_key}' (from '{raw_alias}') → '{aliases_for_region[normalized_alias_key]}'")
                found_count += 1
            else:
                print(f"  ❌ Missing normalized alias: '{normalized_alias_key}' (from '{raw_alias}')")
                if aliases_for_region:
                    sample_keys = list(aliases_for_region.keys())[:5] # Show some sample keys from the loaded aliases
                    print(f"     Sample loaded normalized keys for '{region_to_check}': {sample_keys}...")
        print(f"Found {found_count} out of {len(test_raw_aliases)} specific test aliases for region '{region_to_check}'.")
    else:
        print(f"❌ Region '{target_region}' (or '{stripped_target_region}') not found in the main newspaper_aliases dictionary.")
        available_keys = list(newspaper_aliases_dict.keys())
        if available_keys:
             print(f"   Available regions are (first 10): {available_keys[:10]}")
        else:
            print("   No regions available in newspaper_aliases dictionary.")
    print("--- End Debugging Aliases ---")
# === END HELPER FUNCTION: debug_aliases ===

# === HELPER FUNCTION: extract_date_from_filename ===
def extract_date_from_filename(filename):
    """Extract game date and season from filename"""
    file_info = validate_filename(filename)
    
    if file_info['year'] and file_info['month'] and file_info['day']:
        try:
            year = int(file_info['year'])
            month = int(file_info['month'])
            day = int(file_info['day'])
            game_date_obj = datetime(year, month, day)
            game_date_str = game_date_obj.strftime("%Y-%m-%d")
            season = year if month >= 7 else year - 1
            return game_date_str, season
        except ValueError:
            logger.warning(f"Invalid date components in filename: {filename} (y:{year},m:{month},d:{day})")
            return None, None
    else:
        logger.warning(f"Could not extract complete date from filename: {filename}")
        return None, None
# === END HELPER FUNCTION: extract_date_from_filename ===

# === HELPER FUNCTION: parse_game_line ===
def parse_game_line(line_content): # Renamed parameter
    """Parse a single game line from OCR text"""
    patterns = [
        r'(.+?)\s+vs\.?\s+(.+?),?\s+(\d+)[-–]\s*(\d+)',
        r'(.+?)\s+(\d+),\s*(.+?)\s+(\d+)',
        r'(.+?)\s+(\d+)\s+(.+?)\s+(\d+)(?:\s|$)',
        r'(.+?)\s+(\d+)[\s,;]+(.+?)\s+(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, line_content)
        if match:
            return match.groups()
    return None
# === END HELPER FUNCTION: parse_game_line ===

# === CORE PROCESSING FUNCTION: process_ocr_files ===
def process_ocr_files():
    """Process OCR files and extract game scores"""
    logger.info("STAGE 1: OCR PROCESSING START")
    
    # --- Start of Alias Loading and Preparation ---
    try:
        alias_df = load_aliases_by_state(current_state) 
        
        logger.info(f"Loaded {len(alias_df)} total alias entries from database for state: {current_state}")
        if not alias_df.empty:
            logger.debug("Sample of raw alias data:\n%s", alias_df.head(3))
        elif alias_df.empty and current_state: 
             logger.warning(f"No aliases found in database for state: {current_state}. Team name standardization may be incomplete.")

        newspaper_aliases = {}
        region_info_map = {}
        
        if not alias_df.empty:
            for _, row in alias_df.iterrows():
                try:
                    region = str(row['Newspaper_Region']).strip() 
                    city = row['Newspaper_City']
                    state_from_db = row['Newspaper_State'] 
                    
                    region_info_map[region] = {'city': city, 'state': state_from_db}
                    
                    if region not in newspaper_aliases:
                        newspaper_aliases[region] = {}
                    
                    normalized_db_alias = clean_text(row['Alias_Name'])
                    newspaper_aliases[region][normalized_db_alias] = row['Standardized_Name']
                except KeyError as ke:
                    logger.error(f"Missing expected column in alias_df: {ke}. Row data: {row}")
                    continue 

        for region, aliases in newspaper_aliases.items():
            info = region_info_map.get(region, {})
            logger.info(f"Prepared {len(aliases)} aliases for region: {region} ({info.get('city', 'N/A')}, {info.get('state', 'N/A')})")

        # --- DEBUG_ALIASES CALL IS ACTIVE HERE ---
        if newspaper_aliases: 
            debug_aliases(newspaper_aliases, target_region='Newsday Nassau Edition')
        else:
            logger.warning("newspaper_aliases dictionary is empty, skipping debug_aliases call.")

    except Exception as e:
        logger.exception(f"Critical error during alias setup: {e}") 
        return False, f"Failed during alias setup: {str(e)}"
    # --- End of Alias Loading and Preparation ---

    # --- Start of OCR File Listing and Processing ---
    try:
        ocr_files = [f for f in os.listdir(ocr_files_path) if f.endswith('.txt')]
    except FileNotFoundError:
        logger.error(f"OCR files directory not found: {ocr_files_path}")
        return False, f"OCR directory not found: {ocr_files_path}"
    except Exception as e:
        logger.error(f"Error listing OCR files in {ocr_files_path}: {e}")
        return False, f"Error listing OCR files: {str(e)}"

    if not ocr_files:
        logger.warning(f"No OCR files found in: {ocr_files_path}")
        return False, "No OCR files found in the specified directory"
    
    logger.info(f"Found {len(ocr_files)} OCR files to process in {ocr_files_path}")
    
    all_games = []
    unrecognized_teams_collector = {} 
    
    for ocr_file in ocr_files:
        logger.info(f"Processing OCR file: {ocr_file}")
        game_date, season = extract_date_from_filename(ocr_file)
        if not game_date:
            logger.warning(f"Skipping file with invalid/missing date: {ocr_file}")
            continue
        
        logger.info(f"Extracted date: {game_date}, Season: {season} from {ocr_file}")
        
        current_newspaper_region = get_newspaper_region(ocr_file) 
        logger.info(f"Determined newspaper region: '{current_newspaper_region}' for {ocr_file}")
        
        region_specific_aliases = newspaper_aliases.get(current_newspaper_region, {})

        if not region_specific_aliases:
            logger.warning(f"No aliases available for newspaper region: '{current_newspaper_region}' (from file {ocr_file}).")
            if current_newspaper_region not in newspaper_aliases and newspaper_aliases:
                 logger.debug(f"Region key '{current_newspaper_region}' not found. Available alias regions (first 10): {list(newspaper_aliases.keys())[:10]}")
            
        file_path = os.path.join(ocr_files_path, ocr_file)
        games_extracted_from_file = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line_content in enumerate(f, 1): 
                    line_content = line_content.strip()
                    if not line_content:
                        continue
                    
                    game_parts = parse_game_line(line_content)
                    if not game_parts:
                        continue
                    
                    if len(game_parts) == 4:
                        team1_raw, score1_str, team2_raw, score2_str = game_parts
                    else:
                        logger.warning(f"Unexpected game_parts length: {len(game_parts)} from line: '{line_content}' in {ocr_file}")
                        continue
                    
                    team1_raw = team1_raw.strip()
                    team2_raw = team2_raw.strip()
                    
                    team1_normalized = clean_text(team1_raw)
                    team2_normalized = clean_text(team2_raw)
                    
                    team1_standardized = region_specific_aliases.get(team1_normalized)
                    team2_standardized = region_specific_aliases.get(team2_normalized)
                    
                    source_identifier = ocr_file.replace('_', ' ')

                    if not team1_standardized:
                        logger.debug(f"Unrecognized team (raw): '{team1_raw}' (normalized: '{team1_normalized}') in region '{current_newspaper_region}' from file {ocr_file}")
                        if current_newspaper_region not in unrecognized_teams_collector:
                             unrecognized_teams_collector[current_newspaper_region] = set()
                        unrecognized_teams_collector[current_newspaper_region].add(team1_raw) 

                    if not team2_standardized:
                        logger.debug(f"Unrecognized team (raw): '{team2_raw}' (normalized: '{team2_normalized}') in region '{current_newspaper_region}' from file {ocr_file}")
                        if current_newspaper_region not in unrecognized_teams_collector:
                             unrecognized_teams_collector[current_newspaper_region] = set()
                        unrecognized_teams_collector[current_newspaper_region].add(team2_raw)

                    try:
                        home_score = int(score1_str)
                        visitor_score = int(score2_str)
                    except ValueError:
                        logger.warning(f"Invalid score in line: '{line_content}' in {ocr_file}. Scores: '{score1_str}', '{score2_str}'")
                        continue
                        
                    game_data = {
                        'Date': game_date, 'Season': season,
                        'Home': team1_standardized or team1_raw, 
                        'Visitor': team2_standardized or team2_raw, 
                        'Home_Score': home_score,
                        'Visitor_Score': visitor_score,
                        'Source': source_identifier
                    }
                    all_games.append(game_data)
                    games_extracted_from_file += 1
        except Exception as e:
            logger.exception(f"Error processing file content for {ocr_file}: {e}")
            continue 

        logger.info(f"Extracted {games_extracted_from_file} games from {ocr_file}")
    
    if unrecognized_teams_collector:
        logger.warning("===== UNRECOGNIZED TEAM NAMES FOUND =====")
        total_unrecognized_count = 0
        unrecognized_list_for_csv = []
        sql_template_list = []

        for region, teams_set in unrecognized_teams_collector.items():
            unique_teams_list = sorted(list(teams_set))
            total_unrecognized_count += len(unique_teams_list)
            logger.warning(f"Unrecognized teams in region '{region}':")
            for team_name in unique_teams_list:
                logger.warning(f"- {team_name}")
                unrecognized_list_for_csv.append({
                    'Newspaper_Region': region,
                    'Unrecognized_Team': team_name,
                    'Suggested_Standardized_Name': '', 'Notes': ''
                })
                
# Use stored procedure for smarter alias insertion
                safe_team_name = team_name.replace("'", "''")
                safe_region = region.replace("'", "''")

                sql_template_list.append(
                    f"EXEC sp_AddTeamAlias "
                    f"'{safe_team_name}', "
                    f"'-- ADD STANDARDIZED NAME HERE --', "
                    f"'{safe_region}';"
                )
        
# (This is inside the process_ocr_files function)
# ... (previous code, including the loop 'for ocr_file in ocr_files:')
    # The 'for ocr_file in ocr_files:' loop finishes here.
    # Now, the code to handle results after all files are processed begins.
    # These next major blocks (if, if, try) should be at the same indent level.

    # --- Handling Unrecognized Teams (after processing all files) ---
    if unrecognized_teams_collector:
        logger.warning("===== UNRECOGNIZED TEAM NAMES FOUND =====")
        total_unrecognized_count = 0
        unrecognized_list_for_csv = []
        sql_template_list = []

        for region, teams_set in unrecognized_teams_collector.items(): # Loop for each region with unrecognized teams
            unique_teams_list = sorted(list(teams_set))
            total_unrecognized_count += len(unique_teams_list)
            logger.warning(f"Unrecognized teams in region '{region}':")
            for team_name in unique_teams_list: # Loop for each team in that region
                logger.warning(f"- {team_name}")
                unrecognized_list_for_csv.append({
                    'Newspaper_Region': region,
                    'Unrecognized_Team': team_name,
                    'Suggested_Standardized_Name': '', 'Notes': ''
                })
                
                # Use stored procedure for smarter alias insertion
                safe_team_name = team_name.replace("'", "''")
                safe_region = region.replace("'", "''") # Assuming 'region' here is the string key

                sql_template_list.append(
                    f"EXEC sp_AddTeamAlias "
                    f"'{safe_team_name}', "
                    f"'-- ADD STANDARDIZED NAME HERE --', "
                    f"'{safe_region}';"  # Removed city and state, assuming sp_AddTeamAlias handles it
                )
        # This 'if' is for saving the unrecognized_teams.csv
        if unrecognized_list_for_csv:
            unrecognized_df = pd.DataFrame(unrecognized_list_for_csv)
            unrecognized_file_path = os.path.join(output_path, 'unrecognized_teams.csv')
            try:
                unrecognized_df.to_csv(unrecognized_file_path, index=False)
                logger.info(f"Unrecognized teams saved to: {unrecognized_file_path}")
            except Exception as e:
                logger.error(f"Failed to save unrecognized_teams.csv: {e}")

        # This 'if' is for saving the add_missing_teams.sql
        if sql_template_list:
            sql_file_path = os.path.join(output_path, 'add_missing_teams.sql')
            try:
                with open(sql_file_path, 'w') as f:
                    f.write('\n'.join(sql_template_list))
                logger.info(f"SQL template for adding missing teams saved to: {sql_file_path}")
                logger.info("📝 Note: SQL template now uses sp_AddTeamAlias stored procedure.")
                logger.info("   This will automatically determine the correct city and state for each newspaper region.")
            except Exception as e:
                logger.error(f"Failed to save add_missing_teams.sql: {e}")
        
        logger.error(f"PROCESS STOPPED: {total_unrecognized_count} unique unrecognized team names found.")
        logger.info("Please take the following actions:")
        logger.info("1. Review unrecognized_teams.csv.")
        logger.info("2. Edit add_missing_teams.sql.")
        logger.info("3. Execute the SQL script.")
        logger.info("4. Run this script again.")
        return False, f"{total_unrecognized_count} unrecognized team names found"
    
    # --- Finalizing and Saving Games if No Unrecognized Teams Were Found OR if logic allows proceeding ---
    # This 'if not all_games:' block is at the SAME indentation level as the 'if unrecognized_teams_collector:' above.
    # It checks if any games were extracted at all.
    if not all_games:
        logger.warning("No valid games extracted from any OCR files.")
        return False, "No valid games extracted from OCR files"

    # This 'try' block is also at the SAME indentation level.
    # It processes the games if there were no unrecognized teams (or if you decide to proceed anyway).
    try:
        games_df = pd.DataFrame(all_games)
        
        # === ADD MARGIN CALCULATION HERE ===
        if 'Home_Score' in games_df.columns and 'Visitor_Score' in games_df.columns:
            games_df['Home_Score'] = pd.to_numeric(games_df['Home_Score'], errors='coerce')
            games_df['Visitor_Score'] = pd.to_numeric(games_df['Visitor_Score'], errors='coerce')
            
            games_df['Margin'] = games_df['Home_Score'] - games_df['Visitor_Score']
            
            logger.info("Calculated 'Margin' column for games_df.")
        else:
            logger.error("Home_Score or Visitor_Score column missing from extracted games, cannot calculate Margin.")
            games_df['Margin'] = pd.NA 
        # === END MARGIN CALCULATION ===

        output_file_path = os.path.join(output_path, 'cleaned_scores.csv')
        games_df.to_csv(output_file_path, index=False) 
        logger.info(f"Process completed. {len(games_df)} games saved to {output_file_path} (now includes Margin)")
        return True, len(games_df)
    except Exception as e:
        logger.exception(f"Error creating DataFrame, calculating Margin, or saving cleaned_scores.csv: {e}")
        return False, "Error in final processing or saving cleaned scores CSV"

# === END CORE PROCESSING FUNCTION: process_ocr_files === # Make sure this comment is outside the function if it's a marker

# === CORE PROCESSING FUNCTION: import_to_database ===
def import_to_database():
    """Import cleaned CSV data to database"""
    logger.info("STAGE 2: DATABASE IMPORT START")
    
    csv_file_path = os.path.join(output_path, 'cleaned_scores.csv')
    if not os.path.exists(csv_file_path):
        logger.error("No cleaned_scores.csv file found. Run Stage 1 first.")
        return False, "No cleaned CSV file found."
    
    logger.info(f"Loading CSV file: {csv_file_path}")
    try:
        df_to_import = pd.read_csv(csv_file_path)
    except Exception as e:
        logger.exception(f"Error reading cleaned_scores.csv: {e}")
        return False, "Error reading cleaned_scores.csv"

    if df_to_import.empty:
        logger.warning("cleaned_scores.csv is empty. Nothing to import.")
        return True, "No data to import (CSV was empty)."

    logger.info(f"Initial row count for import: {len(df_to_import)}")
    logger.debug("Sample of data being imported:\n%s", df_to_import.head())
    
    logger.info("Performing database insert...")
    try:
        # Step 1: Import to staging table with smaller chunks
        df_to_import.to_sql(
            name='HS_Scores_Import', 
            con=engine,
            if_exists='append',
            index=False,
            method='multi', 
            chunksize=100  # Reduced from 1000 to 100
        )
        logger.info(f"Staging table import successful. {len(df_to_import)} rows imported.")
        
        # Step 2: Move from staging to main table
        logger.info("Moving data from staging to main table...")
        transfer_query = text("""
            INSERT INTO [dbo].[HS_Scores] (
                [ID], [Date], [Season], [Home], [Home_Score], 
                [Visitor], [Visitor_Score], [Margin], -- Added Margin
                [Source], [Date_Added]
            )
            SELECT 
                NEWID(), [Date], [Season], [Home], [Home_Score], 
                [Visitor], [Visitor_Score], [Margin], -- Added Margin
                [Source], GETDATE()
            FROM [dbo].[HS_Scores_Import]
            -- Optional: Add a WHERE clause if you only want to insert rows that don't already exist
            -- based on some key, but your current logic appends.
        """)
        
        with engine.begin() as connection:
            result = connection.execute(transfer_query)
            rows_moved = result.rowcount
        logger.info(f"Successfully moved {rows_moved} rows to main table.")
        
        # Step 3: Clear staging table
        clear_query = text("DELETE FROM [dbo].[HS_Scores_Import]")
        with engine.begin() as connection:
            connection.execute(clear_query)
        logger.info("Staging table cleared.")
        
        return True, f"{rows_moved} games imported to main database successfully"
        
    except Exception as e:
        logger.exception(f"Database import failed: {e}")
        return False, f"Database import failed: {str(e)}"
# === END CORE PROCESSING FUNCTION: import_to_database ===

# === MAIN EXECUTION FUNCTION ===
def main():
    """Main execution function"""
    logger.info("================================================================================")
    logger.info("🏈 High School Football OCR and Import Pipeline START")
    logger.info("================================================================================")
    
    success_stage1, message_stage1 = process_ocr_files()
    
    if not success_stage1:
        logger.error(f"⛔ Stage 1 (OCR Processing) failed: {message_stage1}")
        logger.info("Pipeline stopped.")
        return
    
    logger.info(f"✅ Stage 1 (OCR Processing) completed: {message_stage1} games processed into CSV.")
    
    success_stage2, message_stage2 = import_to_database()
    
    if success_stage2:
        logger.info(f"🎉 PROCESS COMPLETE! {message_stage2}")
    else:
        logger.error(f"⛔ Stage 2 (Database Import) failed: {message_stage2}")
# === END MAIN EXECUTION FUNCTION ===

# === SCRIPT ENTRY POINT ===
if __name__ == "__main__":
    main()
# === END SCRIPT ENTRY POINT ===