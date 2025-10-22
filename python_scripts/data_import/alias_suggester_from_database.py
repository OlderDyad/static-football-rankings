# alias_suggester_from_database.py

import pandas as pd
import re
from sqlalchemy import create_engine, text
import logging
from collections import defaultdict

# === CONFIGURATION ===
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
INPUT_FILE = "New_Alias_Suggestions.csv"
OUTPUT_FILE = "New_Alias_Suggestions_Enhanced.csv"

# Configurable parameters
START_SEASON = 1975
END_SEASON = 2004
TARGET_STATES = ['LA', 'TX', 'AR']  # Modify based on your newspaper region

# === Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

def parse_opponents_played(opponents_str):
    """
    Parse the comma-separated opponents string into a list.
    """
    if not isinstance(opponents_str, str) or not opponents_str.strip():
        return []
    return [opp.strip() for opp in opponents_str.split(',') if opp.strip()]

def get_candidates_by_opponent_matching(unrecognized_name, opponents_list, target_states, min_season, max_season):
    """
    Find candidate school names that:
    1. Contain the unrecognized name (fuzzy match)
    2. Are in the target states
    3. Have played against the opponents listed
    """
    if not opponents_list:
        logger.warning(f"No opponents provided for '{unrecognized_name}', skipping opponent-based matching")
        return []
    
    # Escape single quotes in opponents for SQL
    escaped_opponents = ["'" + str(opp).replace("'", "''") + "'" for opp in opponents_list if opp]
    if not escaped_opponents:
        return []
    
    opponent_list_str = ", ".join(escaped_opponents)
    
    # Build state filter
    state_conditions = " OR ".join([f"TeamName LIKE '%({state})'" for state in target_states])
    
    # SQL Query to find candidates
    query = text(f"""
    SELECT 
        TeamName,
        COUNT(DISTINCT OpponentName) AS MatchedOpponents,
        COUNT(*) AS TotalGames,
        MIN(Season) AS FirstSeason,
        MAX(Season) AS LastSeason
    FROM (
        SELECT Home AS TeamName, Visitor AS OpponentName, Season 
        FROM HS_Scores 
        WHERE Home LIKE '%{unrecognized_name}%'
            AND ({state_conditions.replace('TeamName', 'Home')})
            AND Visitor IN ({opponent_list_str})
            AND Season BETWEEN {min_season} AND {max_season}
        UNION ALL
        SELECT Visitor AS TeamName, Home AS OpponentName, Season 
        FROM HS_Scores 
        WHERE Visitor LIKE '%{unrecognized_name}%'
            AND ({state_conditions.replace('TeamName', 'Visitor')})
            AND Home IN ({opponent_list_str})
            AND Season BETWEEN {min_season} AND {max_season}
    ) AS Matches
    GROUP BY TeamName
    ORDER BY MatchedOpponents DESC, TotalGames DESC
    """)
    
    try:
        df = pd.read_sql(query, engine)
        candidates = df['TeamName'].tolist()
        logger.info(f"Found {len(candidates)} candidates for '{unrecognized_name}' based on opponent matching")
        return candidates[:3]  # Return top 3
    except Exception as e:
        logger.error(f"Error querying database for '{unrecognized_name}': {e}")
        return []

def get_candidates_by_partial_name_only(unrecognized_name, target_states, min_season, max_season):
    """
    Fallback: Find candidate school names based only on partial name match.
    Used when no opponents are available.
    """
    # Build state filter
    state_conditions = " OR ".join([f"TeamName LIKE '%({state})'" for state in target_states])
    
    query = text(f"""
    SELECT 
        TeamName,
        COUNT(*) AS TotalGames,
        MIN(Season) AS FirstSeason,
        MAX(Season) AS LastSeason,
        COUNT(DISTINCT OpponentName) AS UniqueOpponents
    FROM (
        SELECT Home AS TeamName, Visitor AS OpponentName, Season 
        FROM HS_Scores 
        WHERE Home LIKE '%{unrecognized_name}%'
            AND ({state_conditions.replace('TeamName', 'Home')})
            AND Season BETWEEN {min_season} AND {max_season}
        UNION ALL
        SELECT Visitor AS TeamName, Home AS OpponentName, Season 
        FROM HS_Scores 
        WHERE Visitor LIKE '%{unrecognized_name}%'
            AND ({state_conditions.replace('TeamName', 'Visitor')})
            AND Season BETWEEN {min_season} AND {max_season}
    ) AS AllGames
    GROUP BY TeamName
    ORDER BY TotalGames DESC
    """)
    
    try:
        df = pd.read_sql(query, engine)
        candidates = df['TeamName'].tolist()
        logger.info(f"Found {len(candidates)} candidates for '{unrecognized_name}' based on name matching only")
        return candidates[:3]  # Return top 3
    except Exception as e:
        logger.error(f"Error querying database for '{unrecognized_name}': {e}")
        return []

def enhance_suggestions(input_df, target_states, min_season, max_season):
    """
    Process each row in the input CSV and generate database-backed suggestions.
    """
    enhanced_rows = []
    
    for idx, row in input_df.iterrows():
        unrecognized_name = row['Unrecognized_Alias']
        opponents_str = row.get('Opponents_Played', '')
        
        logger.info(f"Processing [{idx+1}/{len(input_df)}]: {unrecognized_name}")
        
        # Parse opponents
        opponents_list = parse_opponents_played(opponents_str)
        
        # Get candidates
        if opponents_list:
            candidates = get_candidates_by_opponent_matching(
                unrecognized_name, 
                opponents_list, 
                target_states, 
                min_season, 
                max_season
            )
        else:
            candidates = get_candidates_by_partial_name_only(
                unrecognized_name, 
                target_states, 
                min_season, 
                max_season
            )
        
        # Fill in suggestions
        row['Suggested_Proper_Name_1'] = candidates[0] if len(candidates) > 0 else ""
        row['Suggested_Proper_Name_2'] = candidates[1] if len(candidates) > 1 else ""
        row['Suggested_Proper_Name_3'] = candidates[2] if len(candidates) > 2 else ""
        
        enhanced_rows.append(row)
    
    return pd.DataFrame(enhanced_rows)

def main():
    logger.info("=== Starting Database-Backed Alias Suggestion Enhancement ===")
    
    # Load input CSV
    input_path = f"{STAGING_DIRECTORY}/{INPUT_FILE}"
    try:
        input_df = pd.read_csv(input_path, encoding='utf-8-sig')
        logger.info(f"Loaded {len(input_df)} rows from {INPUT_FILE}")
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_path}")
        return
    
    # Process and enhance suggestions
    enhanced_df = enhance_suggestions(input_df, TARGET_STATES, START_SEASON, END_SEASON)
    
    # Save output
    output_path = f"{STAGING_DIRECTORY}/{OUTPUT_FILE}"
    enhanced_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    logger.info(f"Enhanced suggestions saved to: {output_path}")
    logger.info("=== Process Complete ===")

if __name__ == "__main__":
    main()