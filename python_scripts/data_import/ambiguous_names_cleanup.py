# simple_ambiguous_cleanup.py
"""
Simple script to find and delete specific ambiguous team names from HS_Scores.
"""
import pyodbc
import logging

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"

# Exact team names to search for and delete
EXACT_NAMES = [
    '#NAME?',
    'Unknown (TX)',
    'bye (TX)',
    'ye (TX)'
]
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_exact_matches():
    """Find games with exact team name matches."""
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("SEARCHING FOR EXACT MATCHES")
        print("="*80 + "\n")
        
        for team_name in EXACT_NAMES:
            query = """
            SELECT COUNT(*) AS GameCount
            FROM [dbo].[HS_Scores]
            WHERE [Home] = ? OR [Visitor] = ?;
            """
            
            cursor.execute(query, team_name, team_name)
            count = cursor.fetchone().GameCount
            
            if count > 0:
                print(f"  '{team_name}': {count} games found")
            else:
                print(f"  '{team_name}': 0 games (not found)")

def delete_exact_matches(dry_run=True):
    """Delete games with exact team name matches."""
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        total_deleted = 0
        
        for team_name in EXACT_NAMES:
            # Count first
            count_query = """
            SELECT COUNT(*) AS GameCount
            FROM [dbo].[HS_Scores]
            WHERE [Home] = ? OR [Visitor] = ?;
            """
            
            cursor.execute(count_query, team_name, team_name)
            count = cursor.fetchone().GameCount
            
            if count == 0:
                continue
            
            if dry_run:
                logging.info(f"DRY RUN: Would delete {count} games for '{team_name}'")
                total_deleted += count
            else:
                # Actually delete
                delete_query = """
                DELETE FROM [dbo].[HS_Scores]
                WHERE [Home] = ? OR [Visitor] = ?;
                """
                cursor.execute(delete_query, team_name, team_name)
                logging.info(f"DELETED: {count} games for '{team_name}'")
                total_deleted += count
        
        if not dry_run:
            conn.commit()
            logging.info(f"SUCCESS: Total games deleted: {total_deleted}")
        else:
            logging.info(f"DRY RUN TOTAL: Would delete {total_deleted} games")

if __name__ == "__main__":
    print("\n=== SIMPLE AMBIGUOUS NAME CLEANUP ===")
    print("\nSearching for these exact team names:")
    for name in EXACT_NAMES:
        print(f"  - '{name}'")
    
    print("\n")
    
    # First, find matches
    find_exact_matches()
    
    print("\n" + "="*80)
    choice = input("\nDo you want to DELETE these games? (dry/yes/no): ").lower()
    
    if choice == 'dry':
        delete_exact_matches(dry_run=True)
    elif choice == 'yes':
        confirm = input("\nARE YOU SURE? This will PERMANENTLY delete these games. Type 'DELETE' to confirm: ")
        if confirm == 'DELETE':
            delete_exact_matches(dry_run=False)
        else:
            print("Deletion cancelled.")
    else:
        print("No action taken.")