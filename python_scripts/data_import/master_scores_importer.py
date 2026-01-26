# master_scores_importer.py (v4 - Queue Integration)

# === IMPORTS ===
import os
import pandas as pd
import re
from sqlalchemy import create_engine, text
import logging
import uuid
from datetime import datetime
from fuzzywuzzy import process as fuzzy_process
from collections import defaultdict
import csv
import subprocess

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
GLOBAL_ALIAS_REGION = "*Global*"

# === Boilerplate Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

# === HELPER FUNCTIONS ===

def sanitize_raw_team_name(text_input):
    """
    Cleans raw team names to handle common data entry issues before any processing.
    """
    if not isinstance(text_input, str):
        return ""
    text = text_input.replace(',', '')
    text = re.sub(r'\.+$', '', text).strip()
    text = re.sub(r"[^a-zA-Z0-9\s\(\)&'\.-]", '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def sanitize_score(score_text):
    """
    Cleans the raw score string by removing any non-digit characters.
    This ensures values like "30," or '"21"' are correctly converted.
    """
    if not isinstance(score_text, str):
        return ""
    # Remove all characters that are not digits
    return re.sub(r'\D', '', score_text)

def clean_text_for_lookup(text_input):
    """
    Performs a simple normalization for dictionary lookups.
    """
    if not isinstance(text_input, str): return ""
    return text_input.lower().strip()

def load_all_aliases():
    logger.info("Loading alias and abbreviation rules from the database...")
    alias_query = text("SELECT Alias_Name, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Name_Alias")
    abbrev_query = text("SELECT Abbreviation, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Abbreviations")
    try:
        alias_df = pd.read_sql(alias_query, engine)
        alias_rules = defaultdict(dict)
        for _, row in alias_df.iterrows():
            alias_rules[str(row['Newspaper_Region']).strip()][clean_text_for_lookup(row['Alias_Name'])] = row['Standardized_Name']
        
        abbrev_df = pd.read_sql(abbrev_query, engine)
        abbrev_rules = defaultdict(dict)
        for _, row in abbrev_df.iterrows():
            abbrev_rules[str(row['Newspaper_Region']).strip()][clean_text_for_lookup(row['Abbreviation'])] = row['Standardized_Name']
            
        all_canonical_names = set(alias_df['Standardized_Name'].unique()) | set(abbrev_df['Standardized_Name'].unique())
        return alias_rules, all_canonical_names, abbrev_rules
    except Exception as e:
        logger.exception("FATAL: Could not load rules from the database.")
        return None, None, None

def standardize_team_name(raw_name, source_region, alias_rules, abbrev_rules, all_canonical_names):
    if not isinstance(raw_name, str) or not raw_name.strip(): return None
    if raw_name in all_canonical_names: return raw_name
    
    normalized_raw_name = clean_text_for_lookup(raw_name)
    expanded_name = abbrev_rules.get(source_region, {}).get(normalized_raw_name, raw_name)
    if expanded_name == raw_name:
        expanded_name = abbrev_rules.get(GLOBAL_ALIAS_REGION, {}).get(normalized_raw_name, raw_name)
        
    name_to_check = clean_text_for_lookup(expanded_name)
    if name_to_check in alias_rules.get(source_region, {}):
        return alias_rules[source_region][name_to_check]
    if name_to_check in alias_rules.get(GLOBAL_ALIAS_REGION, {}):
        return alias_rules[GLOBAL_ALIAS_REGION][name_to_check]
        
    return None

def get_opponent_history_suggestions(opponents, all_canonical_names):
    if not opponents: return []
    escaped_opponents = ["'" + str(opp).replace("'", "''") + "'" for opp in opponents if opp]
    if not escaped_opponents: return []
    opponent_list_str = ", ".join(escaped_opponents)
    
    query = text(f"SELECT DISTINCT TeamName FROM (SELECT Home AS TeamName FROM HS_Scores WHERE Visitor IN ({opponent_list_str}) UNION SELECT Visitor AS TeamName FROM HS_Scores WHERE Home IN ({opponent_list_str})) AS OppsOfOpps;")
    try:
        df = pd.read_sql(query, engine)
        clean_candidates = [name for name in df['TeamName'].tolist() if name in all_canonical_names]
        return clean_candidates
    except Exception as e:
        logger.error(f"Could not get opponent history due to an error: {e}")
        return []

def generate_suggestions(unrecognized_name, opponents, all_canonical_names):
    logger.info(f"Generating suggestions for '{unrecognized_name}'...")
    opponent_candidates = get_opponent_history_suggestions(opponents, all_canonical_names)
    opponent_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, opponent_candidates, limit=3)]
    general_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, all_canonical_names, limit=3)]
    combined_suggestions = list(dict.fromkeys(opponent_matches + general_matches))
    return combined_suggestions[:3]

def extract_date_and_season(filename):
    match = re.search(r'_(\d{4})_(\d{2})_(\d{2})', filename)
    if match:
        year, month, day = map(int, match.groups())
        season = year if month >= 8 else year - 1
        return datetime(year, month, day).date(), season
    return None, None

def get_newspaper_region(filename):
    match = re.search(r'^(.+?)_\d{4}', filename)
    return match.group(1).replace('_', ' ').strip() if match else "Unknown"

def add_to_batch_queue(batch_id, file_count, game_count, source_files):
    """Add batch to queue using the batch_queue_manager script."""
    try:
        # Build command to add batch to queue
        source_files_str = ','.join(source_files)
        cmd = [
            'python', 
            'batch_queue_manager.py', 
            'add', 
            batch_id, 
            str(file_count), 
            str(game_count), 
            source_files_str
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            logger.info(f"✅ Batch {batch_id} added to processing queue")
            return True
        else:
            logger.error(f"Failed to add batch to queue: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error adding batch to queue: {e}")
        return False

# === MAIN EXECUTION FUNCTION ===
def main():
    logger.info("--- Starting Data Ingestion with Queue Integration (v4) ---")
    
    batch_id = str(uuid.uuid4())
    logger.info(f"Generated new BatchID for this run: {batch_id}")

    alias_rules, all_canonical_names, abbrev_rules = load_all_aliases()
    if alias_rules is None: return

    staged_files = [f for f in os.listdir(STAGING_DIRECTORY) if f.lower().endswith('.csv') and 'new_alias_suggestions' not in f.lower()]
    if not staged_files:
        logger.warning("No .csv files found in staging directory."); return

    all_raw_games = []
    for file_name in staged_files:
        logger.info(f"Processing file: {file_name}")
        game_date, season = extract_date_and_season(file_name)
        source_region = get_newspaper_region(file_name)
        if not all([game_date, season, source_region]): continue
            
        file_path = os.path.join(STAGING_DIRECTORY, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for line_num, row in enumerate(reader, 1):
                if not row or len(row) < 7: continue
                
                home_team = sanitize_raw_team_name(row[0])
                visitor_team = sanitize_raw_team_name(row[2])
                
                # Sanitize score fields immediately after reading
                home_score = sanitize_score(row[1])
                visitor_score = sanitize_score(row[3])
                
                overtime_text, quality_status, notes = row[4], row[5], row[6]
                
                all_raw_games.append({
                    'BatchID': batch_id, 'SourceFile': file_name, 'SourceRegion': source_region,
                    'GameDate': game_date, 'Season': season, 
                    'HomeTeamRaw': home_team, 'VisitorTeamRaw': visitor_team, 
                    'HomeScore': home_score, 'VisitorScore': visitor_score, 'Overtime': overtime_text,
                    'quality_status': quality_status, 'processing_notes': notes,
                    'LineNumber': line_num, 'RawLine': ','.join(row)
                })

    if not all_raw_games: 
        logger.warning("No valid game lines were parsed.")
        return

    unrecognized_teams_with_opponents = defaultdict(lambda: defaultdict(lambda: {'opponents': set(), 'source_files': set()}))
    games_to_import = []

    for game in all_raw_games:
        if game['quality_status'] == 'needs_review': continue

        home_std = standardize_team_name(game['HomeTeamRaw'], game['SourceRegion'], alias_rules, abbrev_rules, all_canonical_names)
        visitor_std = standardize_team_name(game['VisitorTeamRaw'], game['SourceRegion'], alias_rules, abbrev_rules, all_canonical_names)
        
        if not home_std:
            info = unrecognized_teams_with_opponents[game['SourceRegion']][game['HomeTeamRaw']]
            info['opponents'].add(visitor_std or game['VisitorTeamRaw'])
            info['source_files'].add(game['SourceFile'])
        if not visitor_std:
            info = unrecognized_teams_with_opponents[game['SourceRegion']][game['VisitorTeamRaw']]
            info['opponents'].add(home_std or game['HomeTeamRaw'])
            info['source_files'].add(game['SourceFile'])
        
        if home_std and visitor_std:
            game['HomeTeamStd'] = home_std
            game['VisitorTeamStd'] = visitor_std
            games_to_import.append(game)

    if unrecognized_teams_with_opponents:
        logger.error("PROCESS STOPPED: Unrecognized teams found. Generating correction sheet...")
        correction_list = []
        for region, teams in unrecognized_teams_with_opponents.items():
            for team_name, data in teams.items():
                suggestions = generate_suggestions(team_name, data['opponents'], all_canonical_names)
                correction_list.append({
                    'Unrecognized_Alias': team_name, 
                    'Newspaper_Region': region,
                    'Source_Files': ', '.join(sorted(list(data['source_files']))),
                    'Opponents_Played': ', '.join(sorted(list(o for o in data['opponents'] if o))),
                    'Suggested_Proper_Name_1': suggestions[0] if len(suggestions) > 0 else "",
                    'Suggested_Proper_Name_2': suggestions[1] if len(suggestions) > 1 else "",
                    'Suggested_Proper_Name_3': suggestions[2] if len(suggestions) > 2 else "",
                    'Final_Proper_Name': '', 
                    'Alias_Scope': 'Regional', 
                    'Rule_Type': 'Alias'
                })
        correction_df = pd.DataFrame(correction_list)
        correction_df = correction_df[['Unrecognized_Alias', 'Newspaper_Region', 'Source_Files', 'Opponents_Played', 'Suggested_Proper_Name_1', 'Suggested_Proper_Name_2', 'Suggested_Proper_Name_3', 'Final_Proper_Name', 'Alias_Scope', 'Rule_Type']]
        correction_df = correction_df.sort_values(by=['Newspaper_Region', 'Unrecognized_Alias'])
        
        correction_file_path = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv')
        correction_df.to_csv(correction_file_path, index=False, encoding='utf-8-sig')
        logger.info(f"An 'New_Alias_Suggestions.csv' has been generated. Please fill it in and run 'apply_corrections.py'.")
        return

    try:
        games_df = pd.DataFrame(games_to_import)
        df_to_insert = pd.DataFrame({
            'BatchID': games_df['BatchID'],
            'SourceFile': games_df['SourceFile'],
            'SourceRegion': games_df['SourceRegion'],
            'GameDate': games_df['GameDate'],
            'Season': games_df['Season'],
            'HomeTeamRaw': games_df['HomeTeamStd'],
            'VisitorTeamRaw': games_df['VisitorTeamStd'],
            'HomeScore': pd.to_numeric(games_df['HomeScore'], errors='coerce').fillna(0).astype(int),
            'VisitorScore': pd.to_numeric(games_df['VisitorScore'], errors='coerce').fillna(0).astype(int),
            'Overtime': games_df['Overtime'],
            'quality_status': games_df['quality_status'],
            'processing_notes': games_df['processing_notes'],
            'LineNumber': games_df['LineNumber'],
            'RawLine': games_df['RawLine']
        })
        
        logger.info(f"Writing {len(df_to_insert)} standardized records to staging table [RawScores_Staging]...")
        df_to_insert.to_sql('RawScores_Staging', con=engine, if_exists='append', index=False)
        
        # Add batch to queue
        source_files = list(set(games_df['SourceFile'].tolist()))
        add_to_batch_queue(batch_id, len(source_files), len(df_to_insert), source_files)
        
        logger.info("🎉 Stage 1 Ingestion Complete! 🎉")
        logger.info(f"Batch loaded into RawScores_Staging with BatchID: {batch_id}")
        logger.info(f"✅ Batch added to processing queue - you can continue loading more batches")

        print("\n" + "="*80)
        print("✅ BATCH QUEUED FOR PROCESSING")
        print("="*80)
        print(f"BatchID: {batch_id}")
        print(f"Games: {len(df_to_insert)}")
        print(f"Files: {len(source_files)}")
        print("\nThis batch is now in the queue. You can:")
        print("1. Continue running this script to add more batches")
        print("2. Run 'python batch_queue_manager.py' to view queue status")
        print("3. Process all queued batches when your rating calc is complete")
        print("="*80 + "\n")

    except Exception as e:
        logger.exception("FATAL: An error occurred during database load to staging table.")
    
# === SCRIPT ENTRY POINT ===
if __name__ == "__main__":
    main()