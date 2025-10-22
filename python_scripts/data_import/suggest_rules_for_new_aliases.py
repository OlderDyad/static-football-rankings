# suggest_rules_for_new_aliases.py

import os
import pandas as pd
from sqlalchemy import create_engine, text
import logging
from collections import defaultdict
from fuzzywuzzy import process as fuzzy_process

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
MIN_FREQUENCY = 10 # Set the threshold for what to analyze
# =================================================

# Boilerplate Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

# --- Helper functions (copied from master_importer.py for standalone use) ---

# In suggest_rules_for_new_aliases.py, replace the whole function with this block

def get_opponent_history_suggestions(opponents):
    """Finds all opponents of the given opponents to generate a candidate list."""
    if not opponents:
        return []
    
    logger.info(f"Finding opponents of opponents for candidate suggestions (Source Opponents: {list(opponents)})")
    
    # --- Start of New, Simpler Code Block ---
    # This block safely creates the list of names for the SQL query.
    
    sql_ready_opponents = []
    for opp in opponents:
        if opp: # Ensure opponent is not None or an empty string
            # Escape any single quotes inside the name itself (e.g., St. Mary's -> St. Mary''s)
            escaped_name = str(opp).replace("'", "''")
            
            # Wrap the name in the single quotes required for a SQL IN clause
            formatted_name = f"'{escaped_name}'"
            
            sql_ready_opponents.append(formatted_name)
    # --- End of New, Simpler Code Block ---

    if not sql_ready_opponents:
        return []

    opponent_list_str = ", ".join(sql_ready_opponents)
    
    query = text(f"""
        SELECT DISTINCT TeamName FROM (
            SELECT Home AS TeamName FROM HS_Scores WHERE Visitor IN ({opponent_list_str})
            UNION
            SELECT Visitor AS TeamName FROM HS_Scores WHERE Home IN ({opponent_list_str})
        ) AS OppsOfOpps;
    """)
    try:
        df = pd.read_sql(query, engine)
        candidates = df['TeamName'].tolist()
        logger.info(f"Found {len(candidates)} potential candidates from opponent history.")
        return candidates
    except Exception as e:
        logger.error(f"Could not query opponent history: {e}")
        return []

# In suggest_rules_for_new_aliases.py, replace this entire function

def generate_suggestions(unrecognized_name, opponents, all_canonical_names):
    """Combines multiple heuristics to generate the best suggestions."""
    
    # Heuristic 1: Get candidates from opponent history (most powerful)
    opponent_candidates = get_opponent_history_suggestions(opponents)
    
    # --- THIS IS THE NEW LINE THAT WAS MISSING ---
    # Perform a fuzzy match against the smaller, more relevant list of candidates from opponent history.
    opponent_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, opponent_candidates, limit=5)]
    # --- END OF FIX ---
    
    # Heuristic 2: Get general candidates from all known canonical names (good for typos)
    general_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, all_canonical_names, limit=5)]
    
    # Combine, prioritize opponent history matches, and get unique suggestions
    combined_suggestions = []
    seen = set()
    for name in opponent_matches + general_matches: # This line will now work correctly
        if name not in seen:
            combined_suggestions.append(name)
            seen.add(name)
            
    return combined_suggestions[:3] # Return the top 3 unique suggestions

# In suggest_rules_for_new_aliases.py, replace the entire main() function

def main():
    logger.info("--- Starting Suggestion Engine for New Alias Candidates ---")

    # Step 1: Get all existing canonical names to match against.
    try:
        all_canonical_names = set(pd.read_sql("SELECT DISTINCT Standardized_Name FROM dbo.HS_Team_Name_Alias", engine)['Standardized_Name'])
        logger.info(f"Loaded {len(all_canonical_names)} unique canonical names for matching.")
    except Exception as e:
        logger.error(f"Could not load canonical names: {e}")
        return

    # Step 2: Find all high-frequency "New Candidates" using a query similar to your stored procedure.
    find_new_candidates_query = text(f"""
        WITH RawNameFrequencies AS (
            SELECT TeamName, COUNT(*) as TotalFrequency
            FROM (
                SELECT p.Team1 AS TeamName FROM dbo.RawScoreData r CROSS APPLY dbo.parse_game_line(r.RawLineText) p
                UNION ALL
                SELECT p.Team2 AS TeamName FROM dbo.RawScoreData r CROSS APPLY dbo.parse_game_line(r.RawLineText) p
            ) AS AllNames
            GROUP BY TeamName
            HAVING COUNT(*) >= {MIN_FREQUENCY}
        )
        SELECT rnf.TeamName FROM RawNameFrequencies rnf
        LEFT JOIN dbo.HS_Team_Name_Alias tna ON rnf.TeamName = tna.Alias_Name
        GROUP BY rnf.TeamName
        HAVING COUNT(DISTINCT tna.Standardized_Name) = 0;
    """)
    
    logger.info("Finding high-frequency new candidates from raw data...")
    new_candidates_df = pd.read_sql(find_new_candidates_query, engine)
    new_candidates = new_candidates_df['TeamName'].tolist()
    
    if not new_candidates:
        logger.info("No new, high-frequency candidates found that need rules. Nothing to do.")
        return
        
    logger.info(f"Found {len(new_candidates)} new candidates to analyze. Now finding their opponents...")

    # Step 3: For each new candidate, find its opponents to generate context
    
    # --- Start of New, Corrected Code Block ---
    # This block safely creates the list of names for the SQL query.
    sql_ready_candidates = []
    for c in new_candidates:
        if c: # Ensure candidate is not None or empty
            escaped_name = str(c).replace("'", "''")
            formatted_name = f"'{escaped_name}'"
            sql_ready_candidates.append(formatted_name)
    
    if not sql_ready_candidates:
        logger.warning("No valid new candidates to process after cleaning.")
        return

    candidates_list_str = ",".join(sql_ready_candidates)
    # --- End of New, Corrected Code Block ---

    opponents_query = text(f"""
        SELECT TeamName, OpponentName FROM (
            SELECT Home AS TeamName, Visitor AS OpponentName FROM HS_Scores WHERE Home IN ({candidates_list_str})
            UNION ALL
            SELECT Visitor AS TeamName, Home AS OpponentName FROM HS_Scores WHERE Visitor IN ({candidates_list_str})
        ) AS GamePairs
    """)
    
    opponents_df = pd.read_sql(opponents_query, engine)
    opponents_map = opponents_df.groupby('TeamName')['OpponentName'].apply(set).to_dict()

    # Step 4: Generate the correction sheet with intelligent suggestions
    logger.info("Generating correction sheet with suggestions...")
    correction_list = []
    for team_name in new_candidates:
        opponents = opponents_map.get(team_name, set())
        suggestions = generate_suggestions(team_name, opponents, all_canonical_names)
        
        correction_list.append({
            'Unrecognized_Alias': team_name,
            'Newspaper_Region': '*Global*', # Defaulting to Global, change as needed
            'Opponents_Played': ', '.join(sorted(list(opponents))),
            'Suggested_Proper_Name_1': suggestions[0] if len(suggestions) > 0 else "",
            'Suggested_Proper_Name_2': suggestions[1] if len(suggestions) > 1 else "",
            'Suggested_Proper_Name_3': suggestions[2] if len(suggestions) > 2 else "",
            'Final_Proper_Name': '',
            'Alias_Scope': 'Global'
        })
    
    correction_df = pd.DataFrame(correction_list).sort_values(by=['Unrecognized_Alias'])
    correction_file_path = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv')
    correction_df.to_csv(correction_file_path, index=False)
    
    logger.info(f"SUCCESS: A 'New_Alias_Suggestions.csv' file has been generated in your staging directory.")
    logger.info("Please open it, review the suggestions, and use it to update your master Alias_Names_List.csv file.")

if __name__ == "__main__":
    main()