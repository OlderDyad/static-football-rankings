import pandas as pd
import re
import logging
from typing import Optional

# --- CONFIGURATION ---

# The input file name (from the CSV you just saved in SSMS)
INPUT_FILE_NAME = "Mappable_Scores_Input.csv" 
# The final output file name
OUTPUT_FILE_NAME = "Mappable_Scores_Final.csv" 
# --- END CONFIGURATION ---
JUNK_OPPONENTS = ['`', '0', 'o', 'O']

# Regex to find the state code suffix (XX) at the end of a string, preceded by a space
STATE_SUFFIX_PATTERN = re.compile(r'\s\(([A-Z]{2})\)$')
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_state_suffix(team_name: str) -> Optional[str]:
    """Extracts the state suffix (XX) or returns None."""
    if not team_name: 
        return None
    match = STATE_SUFFIX_PATTERN.search(team_name)
    return match.group(0) if match else None

def process_state_suffix_addition(row: pd.Series) -> pd.Series:
    """
    Conditionally adds the state suffix from one team to the other, 
    only if the target team is currently missing the suffix.
    """
    # Names are guaranteed to be strings by the main function's casting
    home_name = row['Home']
    visitor_name = row['Visitor']

    home_suffix = extract_state_suffix(home_name)
    visitor_suffix = extract_state_suffix(visitor_name)

    # --- Case 1: Visitor has the suffix, Home is missing it ---
    if visitor_suffix and not home_suffix:
        row['Home'] = home_name + visitor_suffix
        return row

    # --- Case 2: Home has the suffix, Visitor is missing it ---
    if home_suffix and not visitor_suffix:
         row['Visitor'] = visitor_name + home_suffix
         return row

    return row

def run_data_prep_workflow():
    logging.info(f"Starting data preparation workflow.")
    
    # 1. Load Data
    try:
        # Load the initial file that contains games with non-standard names
        # Use latin1 encoding as a defensive measure against non-UTF characters
        df = pd.read_csv(INPUT_FILE_NAME, encoding='latin1')
        logging.info(f"Loaded {len(df)} initial game records from {INPUT_FILE_NAME}.")
    except FileNotFoundError:
        logging.error(f"FATAL: Input file not found: {INPUT_FILE_NAME}. Please ensure this file exists in the script directory.")
        return
    except Exception as e:
        logging.error(f"FATAL: Failed to read input file due to error: {e}")
        return

    # 2. Clean Junk Names
    df_temp = df[~df['Home'].isin(JUNK_OPPONENTS) & ~df['Visitor'].isin(JUNK_OPPONENTS)].copy()
    logging.info(f"Filtered out {len(df) - len(df_temp)} junk game records.")

    # 3. Type Casting for Safety
    # Ensure team columns are explicitly strings before applying regex logic
    df_cleaned = df_temp.copy()
    df_cleaned['Home'] = df_cleaned['Home'].astype(str)
    df_cleaned['Visitor'] = df_cleaned['Visitor'].astype(str)
    
    # 4. Apply Suffix Addition Logic
    logging.info("Applying state suffix inference logic...")
    df_modified = df_cleaned.apply(process_state_suffix_addition, axis=1)

    # Calculate modifications for logging purposes
    modification_count = (
        (df_modified['Home'] != df_cleaned['Home']) |
        (df_modified['Visitor'] != df_cleaned['Visitor'])
    ).sum()
    
    # 5. Save Final File
    df_modified.to_csv(OUTPUT_FILE_NAME, index=False)
    logging.info(f"SUCCESS: {modification_count} team names were modified/augmented.")
    logging.info(f"Final prepared game data saved as: {OUTPUT_FILE_NAME}.")

if __name__ == "__main__":
    run_data_prep_workflow()