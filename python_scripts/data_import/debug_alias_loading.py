# debug_alias_loading.py

import re
import pandas as pd
from sqlalchemy import create_engine, text
from collections import defaultdict

# --- Configuration (Copied from your main script) ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)
# --- End Configuration ---

def clean_text_for_lookup(text_input):
    """The robust version of the cleaning function."""
    if not isinstance(text_input, str):
        return ""
    text = text_input.lower()
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def load_all_aliases_for_debug():
    """Loads all aliases for debugging."""
    print("--- Loading all alias rules from the database... ---")
    query = text("SELECT Alias_Name, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Name_Alias")
    try:
        alias_df = pd.read_sql(query, engine)
        alias_dict = defaultdict(dict)
        for _, row in alias_df.iterrows():
            region = str(row['Newspaper_Region']).strip()
            normalized_alias = clean_text_for_lookup(row['Alias_Name'])
            alias_dict[region][normalized_alias] = row['Standardized_Name']
        print(f"--- Successfully loaded rules for {len(alias_dict)} newspaper regions. ---")
        return alias_dict
    except Exception as e:
        print(f"--- FATAL: Could not load aliases. Error: {e} ---")
        return None

# --- Main Diagnostic Test ---
if __name__ == "__main__":
    print("--- Starting Alias Loading and Lookup Diagnostic ---")
    
    alias_rules = load_all_aliases_for_debug()

    if alias_rules:
        # --- Define what we are searching for ---
        region_to_check = 'Newsday Suffolk Edition'
        alias_to_check = 'CS HARBOR'
        normalized_key_to_find = clean_text_for_lookup(alias_to_check)

        print(f"\n[1] Checking for region: '{region_to_check}'")
        
        # Check if the region exists in the loaded rules
        if region_to_check in alias_rules:
            print(f"[SUCCESS] The region '{region_to_check}' was found as a key in the alias dictionary.")
            
            # Get the specific sub-dictionary for this region
            suffolk_aliases = alias_rules[region_to_check]
            
            print(f"\n[2] Checking for normalized alias key: '{normalized_key_to_find}' within this region's rules...")
            
            # Check if the normalized key exists in the region's sub-dictionary
            if normalized_key_to_find in suffolk_aliases:
                print(f"[SUCCESS] The key '{normalized_key_to_find}' was found!")
                print(f"    - It maps to: '{suffolk_aliases[normalized_key_to_find]}'")
            else:
                print(f"[FAILURE] The key '{normalized_key_to_find}' was NOT found in the dictionary for this region.")
                print("\n    This confirms the lookup failure is happening during key creation or comparison.")
                print("    Let's look at a sample of the actual keys that WERE created for this region:")
                
                sample_keys = list(suffolk_aliases.keys())
                found_similar = False
                for i, key in enumerate(sample_keys[:50]): # Print first 50 keys
                    print(f"      - Sample Key #{i+1}: |{key}|")
                    if 'cs' in key and 'harbor' in key:
                        found_similar = True

                if not found_similar:
                    print("\n    Note: No keys containing both 'cs' and 'harbor' were found in the sample.")

        else:
            print(f"[FAILURE] The region key '{region_to_check}' does NOT exist in the loaded alias dictionary.")
            print("    This would be the cause of the problem.")