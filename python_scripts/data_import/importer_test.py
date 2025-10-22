# importer_test.py - FINAL, VERIFIED VERSION

# === IMPORTS ===
import os
import pandas as pd
import re
from sqlalchemy import create_engine, text
import logging
from collections import defaultdict
from fuzzywuzzy import process as fuzzy_process
from datetime import datetime
from Google Search import search

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
    if not isinstance(text_input, str): return ""
    text = text_input.lower()
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def load_all_aliases():
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
        logger.info(f"Successfully loaded {len(abbrev_rules)} abbreviation rules.")
        return alias_rules, alias_df, abbrev_rules
    except Exception as e:
        logger.exception(f"FATAL: Could not load rules from the database.")
        return None, None, None

def standardize_team_name(raw_name, source_region, alias_rules, abbrev_rules):
    if not isinstance(raw_name, str) or not raw_name.strip(): return None 
    normalized_raw_name = clean_text_for_lookup(raw_name)
    expanded_name = abbrev_rules.get(source_region, {}).get(normalized_raw_name)
    if not expanded_name:
        expanded_name = abbrev_rules.get(GLOBAL_ALIAS_REGION, {}).get(normalized_raw_name, raw_name)
    name_to_check = clean_text_for_lookup(expanded_name)
    final_name = alias_rules.get(source_region, {}).get(name_to_check)
    if not final_name:
        final_name = alias_rules.get(GLOBAL_ALIAS_REGION, {}).get(name_to_check)
    return final_name

def validate_filename(filename):
    match = re.search(r'^(.+?)_(\d{4})_(\d{2})_(\d{2})', filename)
    if not match:
        logger.warning(f"Could not parse filename for date/region: {filename}")
        return None
    return {'newspaper_info': match.group(1), 'year': match.group(2), 'month': match.group(3), 'day': match.group(4)}

def get_newspaper_region(filename):
    file_info = validate_filename(filename)
    return file_info['newspaper_info'].replace('_', ' ').strip() if file_info else None

def extract_date_from_filename(filename):
    file_info = validate_filename(filename)
    if file_info:
        try:
            year, month, day = int(file_info['year']), int(file_info['month']), int(file_info['day'])
            season = year if month >= 8 else year - 1
            return f"{year:04d}-{month:02d}-{day:02d}", season
        except (ValueError, TypeError):
            logger.warning(f"Invalid date components found in filename: {filename}")
    return None, None

def parse_game_line(line_content):
    patterns = [ r'(.+?)\s+(\d+),\s*(.+?)\s+(\d+)', r'(.+?)\s+(\d+)\s+(.+?)\s+(\d+)(?:\s|$)']
    for pattern in patterns:
        match = re.search(pattern, line_content)
        if match:
            return match.group(1).strip(), match.group(2).strip(), match.group(3).strip(), match.group(4).strip()
    return None

def get_opponent_history_suggestions(opponents):
    if not opponents: return []
    logger.info(f"Finding opponents of opponents for context...")
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

def generate_suggestions(unrecognized_name, opponents, all_canonical_names, state_code):
    google_suggestions = []
    try:
        logger.info(f"Running Google Search for '{unrecognized_name}' in state '{state_code}'...")
        search_query = f'"{unrecognized_name}" high school football {state_code}'
        search_results = search(queries=[search_query])
        raw_words = set(re.split(r'\s|-|\.', unrecognized_name.lower()))
        potential_names = set()
        if search_results and search_results[0]:
            for result in search_results[0]:
                text_to_search = result.title + " " + result.snippet
                candidates = re.findall(r'([A-Za-z\s.-]+?\s\(\w{2}\))', text_to_search)
                for cand in candidates:
                    cand_clean = cand.strip()
                    if all(word in cand_clean.lower() for word in raw_words if word):
                        potential_names.add(cand_clean)
        google_suggestions = list(potential_names)
    except Exception as e:
        logger.error(f"Google Search failed: {e}")
    opponent_candidates = get_opponent_history_suggestions(opponents)
    opponent_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, opponent_candidates, limit=3)]
    general_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, all_canonical_names, limit=3)]
    combined_suggestions = []
    seen = set()
    for name in google_suggestions + opponent_matches + general_matches:
        if name not in seen:
            combined_suggestions.append(name)
            seen.add(name)
    return combined_suggestions[:3]

# === MAIN EXECUTION FUNCTION ===
def main():
    """Main ETL process with the full, upgraded suggestion engine."""
    logger.info("Starting Unified Score Importer with Google Search Suggestions...")
    alias_rules, alias_df, abbrev_rules = load_all_aliases()
    if alias_rules is None: return

    logger.info(f"Scanning for files in staging directory: {STAGING_DIRECTORY}")
    try:
        staged_files = [f for f in os.listdir(STAGING_DIRECTORY) if f.lower().endswith('.txt')]
    except FileNotFoundError:
        logger.error(f"FATAL: Staging directory not found."); return

    if not staged_files:
        logger.warning("No .txt files found in staging directory."); return

    all_raw_games = []
    for file_name in staged_files:
        logger.info(f"--- Pass 1: Reading raw data from: {file_name} ---")
        game_date, season = extract_date_from_filename(file_name)
        source_region = get_newspaper_region(file_name)
        if not all([game_date, season, source_region]): continue
        file_path = os.path.join(STAGING_DIRECTORY, file_name)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed = parse_game_line(line)
                if parsed:
                    all_raw_games.append({'Date': game_date, 'Season': season, 'Source': source_region, 'HomeRaw': parsed[0], 'HomeScore': parsed[1], 'VisitorRaw': parsed[2], 'VisitorScore': parsed[3]})
    
    logger.info(f"--- Pass 2: Standardizing {len(all_raw_games)} raw game records... ---")
    unrecognized_teams_with_opponents = defaultdict(lambda: defaultdict(set))
    games_to_import = []
    for game in all_raw_games:
        home_std = standardize_team_name(game['HomeRaw'], game['Source'], alias_rules, abbrev_rules)
        visitor_std = standardize_team_name(game['VisitorRaw'], game['Source'], alias_rules, abbrev_rules)
        if not home_std: unrecognized_teams_with_opponents[game['Source']][game['HomeRaw']].add(visitor_std or game['VisitorRaw'])
        if not visitor_std: unrecognized_teams_with_opponents[game['Source']][game['VisitorRaw']].add(home_std or game['HomeRaw'])
        if home_std and visitor_std:
            games_to_import.append({'Date': game['Date'], 'Season': game['Season'], 'Home': home_std, 'Visitor': visitor_std, 'Home_Score': game['HomeScore'], 'Visitor_Score': game['VisitorScore'], 'Source': game['Source']})

    if unrecognized_teams_with_opponents:
        logger.error("PROCESS STOPPED: Unrecognized teams found. Generating advanced correction sheet...")
        all_canonical_names = set(alias_df['Standardized_Name'].unique())
        correction_list = []
        for region, teams in unrecognized_teams_with_opponents.items():
            state_code = 'NY'
            try:
                sample_alias_key = next(iter(alias_rules[region]))
                sample_canonical = alias_rules[region][sample_alias_key]
                match = re.search(r'\((\w{2})\)', sample_canonical)
                if match: state_code = match.group(1)
            except (StopIteration, KeyError): pass
            for team_name, opponents in teams.items():
                suggestions = generate_suggestions(team_name, opponents, all_canonical_names, state_code)
                correction_list.append({
                    'Unrecognized_Alias': team_name, 'Newspaper_Region': region,
                    'Opponents_Played': ', '.join(sorted(list(opponents))),
                    'Suggested_Proper_Name_1': suggestions[0] if len(suggestions) > 0 else "",
                    'Suggested_Proper_Name_2': suggestions[1] if len(suggestions) > 1 else "",
                    'Suggested_Proper_Name_3': suggestions[2] if len(suggestions) > 2 else "",
                    'Final_Proper_Name': '', 'Alias_Scope': 'Regional'
                })
        correction_df = pd.DataFrame(correction_list).sort_values(by=['Newspaper_Region', 'Unrecognized_Alias'])
        correction_file_path = os.path.join(STAGING_DIRECTORY, 'Alias_Correction_Sheet.csv')
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
            logger.info(f"Writing {len(games_df)} records to staging table [HS_Scores_Import]...")
            # Using specific columns to avoid any extra ones from the DataFrame
            columns_to_insert = ['Date', 'Season', 'Home', 'Visitor', 'Home_Score', 'Visitor_Score', 'Source', 'Margin']
            games_df[columns_to_insert].to_sql('HS_Scores_Import', con=engine, if_exists='append', index=False)
            
            with engine.begin() as connection:
                # Using a safe, parameterized Stored Procedure is best practice
                result = connection.execute(text("EXEC dbo.MergeImportedScores;")) 
                logger.info(f"{result.rowcount} rows merged into HS_Scores.")
            logger.info("🎉 Database import process complete! 🎉")
        else:
            logger.info("No new games to import.")
    except Exception as e:
        logger.exception(f"FATAL: An error occurred during database load.")

# === SCRIPT ENTRY POINT ===
if __name__ == "__main__":
    main()