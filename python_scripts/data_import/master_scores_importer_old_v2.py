# master_scores_importer.py - FINAL VERSION with EXPLICIT REGIONAL LOGIC

# === IMPORTS ===
import os
import pandas as pd
import re
from sqlalchemy import create_engine, text
import logging
from collections import defaultdict
from fuzzywuzzy import process as fuzzy_process
from datetime import datetime

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
GLOBAL_ALIAS_REGION = "*Global*"
# =================================================

# === Boilerplate Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)
# === End Setup ===


# === HELPER FUNCTIONS ===

def clean_text_for_lookup(text_input):
    """Normalizes text for consistent dictionary key lookups."""
    if not isinstance(text_input, str): return ""
    text = text_input.lower()
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def load_all_aliases():
    """Loads BOTH the main alias rules and the new abbreviation rules from the database."""
    logger.info("Loading alias and abbreviation rules from the database...")
    alias_query = text("SELECT Alias_Name, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Name_Alias")
    abbrev_query = text("SELECT Abbreviation, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Abbreviations")
    try:
        alias_df = pd.read_sql(alias_query, engine)
        alias_rules = defaultdict(dict)
        for _, row in alias_df.iterrows():
            region = str(row['Newspaper_Region']).strip()
            alias_rules[region][clean_text_for_lookup(row['Alias_Name'])] = row['Standardized_Name']
        logger.info(f"Successfully loaded rules for {len(alias_rules)} main alias regions.")
        
        abbrev_df = pd.read_sql(abbrev_query, engine)
        abbrev_rules = defaultdict(dict)
        for _, row in abbrev_df.iterrows():
            region = str(row['Newspaper_Region']).strip()
            abbrev_rules[region][clean_text_for_lookup(row['Abbreviation'])] = row['Standardized_Name']
        logger.info(f"Successfully loaded {len(abbrev_df)} abbreviation rules.")
        
        all_canonical_names = set(alias_df['Standardized_Name'].unique()) | set(abbrev_df['Standardized_Name'].unique())
        
        return alias_rules, all_canonical_names, abbrev_rules
    except Exception as e:
        logger.exception(f"FATAL: Could not load rules from the database.")
        return None, None, None

def standardize_team_name(raw_name, source_region, alias_rules, abbrev_rules, all_canonical_names):
    """
    Standardizes a name using a multi-step, prioritized process with strict regional logic.
    *** THIS IS THE FINAL, CORRECTED VERSION ***
    """
    if not isinstance(raw_name, str) or not raw_name.strip(): 
        return None 
    
    # Step 0: Check if the raw name is ALREADY a valid canonical name.
    if raw_name in all_canonical_names:
        return raw_name

    normalized_raw_name = clean_text_for_lookup(raw_name)
    
    # Step 1: Abbreviation Lookup (Regional then Global)
    # Check for a specific regional abbreviation first
    expanded_name = raw_name
    if source_region in abbrev_rules and normalized_raw_name in abbrev_rules[source_region]:
        expanded_name = abbrev_rules[source_region][normalized_raw_name]
    # If not found, check for a global abbreviation
    elif GLOBAL_ALIAS_REGION in abbrev_rules and normalized_raw_name in abbrev_rules[GLOBAL_ALIAS_REGION]:
        expanded_name = abbrev_rules[GLOBAL_ALIAS_REGION][normalized_raw_name]

    name_to_check = clean_text_for_lookup(expanded_name)
    
    # Step 2: Main Alias Lookup with EXPLICIT, STRICT logic
    # First, check the specific source region.
    if source_region in alias_rules and name_to_check in alias_rules[source_region]:
        final_name = alias_rules[source_region][name_to_check]
        return final_name
        
    # If not found, check ONLY the *Global* region.
    if GLOBAL_ALIAS_REGION in alias_rules and name_to_check in alias_rules[GLOBAL_ALIAS_REGION]:
        final_name = alias_rules[GLOBAL_ALIAS_REGION][name_to_check]
        return final_name
        
    # If no specific regional or global alias is found, it is definitively unrecognized.
    return None

def validate_filename(filename):
    """Validate OCR filename format to extract metadata."""
    match = re.search(r'^(.+?)_(\d{4})_(\d{2})_(\d{2})', filename)
    if not match:
        return None
    return {'newspaper_info': match.group(1), 'year': match.group(2), 'month': match.group(3), 'day': match.group(4)}

def get_newspaper_region(filename):
    """Extracts newspaper region from filename."""
    file_info = validate_filename(filename)
    return file_info['newspaper_info'].replace('_', ' ').strip() if file_info else None

def extract_date_from_filename(filename):
    """Extract game date and season from filename."""
    file_info = validate_filename(filename)
    if file_info:
        try:
            year, month, day = int(file_info['year']), int(file_info['month']), int(file_info['day'])
            season = year if month >= 8 else year - 1
            return f"{year:04d}-{month:02d}-{day:02d}", season
        except (ValueError, TypeError):
            return None, None
    return None, None

def parse_game_line(line_content):
    """Parses a single game line from OCR text."""
    patterns = [ r'(.+?)\s+(\d+),\s*(.+?)\s+(\d+)', r'(.+?)\s+(\d+)\s+(.+?)\s+(\d+)(?:\s|$)']
    for pattern in patterns:
        match = re.search(pattern, line_content)
        if match:
            return match.group(1).strip(), match.group(2).strip(), match.group(3).strip(), match.group(4).strip()
    return None

def read_file_with_fallback_encoding(path):
    lines = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Could not read file {os.path.basename(path)} with fallback. Error: {e}")
    except Exception as e:
        logger.error(f"Could not read file {os.path.basename(path)}. Error: {e}")
    return lines

def get_opponent_history_suggestions(opponents):
    if not opponents: return []
    sql_ready_opponents = []
    for opp in opponents:
        if opp:
            escaped_name = str(opp).replace("'", "''")
            formatted_name = f"'{escaped_name}'"
            sql_ready_opponents.append(formatted_name)
    if not sql_ready_opponents: return []
    query = text(f"SELECT DISTINCT TeamName FROM (SELECT Home AS TeamName FROM HS_Scores WHERE Visitor IN ({', '.join(sql_ready_opponents)}) UNION SELECT Visitor AS TeamName FROM HS_Scores WHERE Home IN ({', '.join(sql_ready_opponents)})) AS OppsOfOpps;")
    try:
        df = pd.read_sql(query, engine)
        return df['TeamName'].tolist()
    except Exception: return []

def generate_suggestions(unrecognized_name, opponents, all_canonical_names):
    opponent_candidates = get_opponent_history_suggestions(opponents)
    opponent_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, opponent_candidates, limit=3)]
    general_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, all_canonical_names, limit=3)]
    combined_suggestions = []
    seen = set()
    for name in opponent_matches + general_matches:
        if name not in seen:
            combined_suggestions.append(name)
            seen.add(name)
    return combined_suggestions[:3]

# === MAIN EXECUTION FUNCTION ===
def main():
    logger.info("Starting Unified Score Importer...")
    
    correction_file_path = os.path.join(STAGING_DIRECTORY, 'Alias_Correction_Sheet.csv')
    if os.path.exists(correction_file_path):
        os.remove(correction_file_path)

    alias_rules, all_canonical_names, abbrev_rules = load_all_aliases()
    if alias_rules is None: return

    try:
        staged_files = [f for f in os.listdir(STAGING_DIRECTORY) if f.lower().endswith('.txt')]
    except FileNotFoundError:
        logger.error(f"FATAL: Staging directory not found at {STAGING_DIRECTORY}"); return

    if not staged_files:
        logger.warning("No .txt files found in staging directory."); return

    all_raw_games = []
    for file_name in staged_files:
        file_path = os.path.join(STAGING_DIRECTORY, file_name)
        game_date, season = extract_date_from_filename(file_name)
        source_region = get_newspaper_region(file_name)
        if not all([game_date, season, source_region]): 
            logger.warning(f"Skipping file with invalid name format: {file_name}")
            continue
        
        lines = read_file_with_fallback_encoding(file_path)
        for line in lines:
            parsed = parse_game_line(line)
            if parsed:
                all_raw_games.append({'Date': game_date, 'Season': season, 'Source': source_region, 'HomeRaw': parsed[0], 'HomeScore': parsed[1], 'VisitorRaw': parsed[2], 'VisitorScore': parsed[3]})
    
    unrecognized_teams_with_opponents = defaultdict(lambda: defaultdict(set))
    games_to_import = []
    for game in all_raw_games:
        home_std = standardize_team_name(game['HomeRaw'], game['Source'], alias_rules, abbrev_rules, all_canonical_names)
        visitor_std = standardize_team_name(game['VisitorRaw'], game['Source'], alias_rules, abbrev_rules, all_canonical_names)
        if not home_std: unrecognized_teams_with_opponents[game['Source']][game['HomeRaw']].add(visitor_std or game['VisitorRaw'])
        if not visitor_std: unrecognized_teams_with_opponents[game['Source']][game['VisitorRaw']].add(home_std or game['HomeRaw'])
        if home_std and visitor_std:
            games_to_import.append({'Date': game['Date'], 'Season': game['Season'], 'Home': home_std, 'Visitor': visitor_std, 'Home_Score': game['HomeScore'], 'Visitor_Score': game['VisitorScore'], 'Source': game['Source']})

    if unrecognized_teams_with_opponents:
        logger.error("PROCESS STOPPED: Unrecognized teams found. Generating correction sheet...")
        correction_list = []
        for region, teams in unrecognized_teams_with_opponents.items():
            for team_name, opponents in teams.items():
                suggestions = generate_suggestions(team_name, opponents, all_canonical_names)
                correction_list.append({
                    'Unrecognized_Alias': team_name, 'Newspaper_Region': region,
                    'Opponents_Played': ', '.join(sorted(list(opponents))),
                    'Suggested_Proper_Name_1': suggestions[0] if len(suggestions) > 0 else "",
                    'Suggested_Proper_Name_2': suggestions[1] if len(suggestions) > 1 else "",
                    'Suggested_Proper_Name_3': suggestions[2] if len(suggestions) > 2 else "",
                    'Final_Proper_Name': '', 'Alias_Scope': 'Regional'
                })
        correction_df = pd.DataFrame(correction_list).sort_values(by=['Newspaper_Region', 'Unrecognized_Alias'])
        correction_df.to_csv(correction_file_path, index=False)
        logger.info(f"An 'Alias_Correction_Sheet.csv' has been generated. Please fill it in and run 'apply_corrections.py'.")
        return

    logger.info(f"All {len(games_to_import)} games standardized successfully. Writing to database.")
    games_df = pd.DataFrame(games_to_import)
    games_df['Margin'] = pd.to_numeric(games_df['Home_Score'], errors='coerce') - pd.to_numeric(games_df['Visitor_Score'], errors='coerce')
    games_df.dropna(subset=['Margin'], inplace=True)
    if not games_df.empty:
        games_df['Margin'] = games_df['Margin'].astype(int)
    
    try:
        if not games_df.empty:
            games_df.to_sql('HS_Scores_Import', con=engine, if_exists='append', index=False)
            with engine.begin() as connection:
                transfer_query = text("""
                    INSERT INTO dbo.HS_Scores ([ID], [Date], [Season], [Home], [Home_Score], [Visitor], [Visitor_Score], [Margin], [Source], [Date_Added])
                    SELECT NEWID(), [Date], [Season], [Home], [Home_Score], [Visitor], [Visitor_Score], [Margin], [Source], GETDATE()
                    FROM dbo.HS_Scores_Import;
                """)
                result = connection.execute(transfer_query)
                logger.info(f"{result.rowcount} rows moved to HS_Scores.")

                connection.execute(text("DELETE FROM dbo.HS_Scores_Import;"))
            logger.info("🎉 Database import process complete! 🎉")
        else:
            logger.info("No new games to import.")
    except Exception as e:
        logger.exception(f"FATAL: An error occurred during database load.")

# === SCRIPT ENTRY POINT ===
if __name__ == "__main__":
    main()

            