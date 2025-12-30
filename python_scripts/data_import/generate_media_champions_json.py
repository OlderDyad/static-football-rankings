# generate_media_champions_json.py
"""
Generate Media National Champions JSON with team page links
CORRECTED OUTPUT PATH
"""

import pyodbc
import json
import os
import logging
from datetime import datetime
from decimal import Decimal

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
# CORRECTED PATH - matches existing structure
OUTPUT_FILE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/data/media-national-champions/media-national-champions.json"
# --- END CONFIGURATION ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def generate_json():
    """Generate Media National Champions JSON from stored procedure"""
    
    logging.info("=" * 60)
    logging.info("GENERATING MEDIA NATIONAL CHAMPIONS JSON")
    logging.info("=" * 60)
    
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
    
    try:
        # Connect to database
        logging.info(f"Connecting to database: {DATABASE_NAME}")
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            # Execute stored procedure
            logging.info("Executing stored procedure: sp_Get_Media_National_Champions_JSON")
            cursor.execute("EXEC sp_Get_Media_National_Champions_JSON")
            
            # Get column names
            columns = [column[0] for column in cursor.description]
            logging.info(f"Retrieved {len(columns)} columns")
            
            # Fetch all rows
            rows = cursor.fetchall()
            logging.info(f"Retrieved {len(rows)} champions from database")
            
            # Convert to list of dictionaries
            champions = []
            for row in rows:
                champion = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    
                    # Handle boolean conversion
                    if column in ['undefeated', 'hasProgramPage']:
                        champion[column] = bool(value) if value is not None else False
                    # Handle None values
                    elif value is None:
                        champion[column] = None
                    # Handle Decimal types - convert to float
                    elif isinstance(value, Decimal):
                        champion[column] = float(value)
                    # Handle regular floats
                    elif isinstance(value, float):
                        champion[column] = round(value, 3)
                    else:
                        champion[column] = value
                
                # Generate link HTML based on hasProgramPage flag
                if champion.get('hasProgramPage') and champion.get('programPageUrl'):
                    # Team has a program page - show link icon
                    champion['teamLinkHtml'] = '<span class="no-page-icon" style="color:#ddd;" title="Page coming soon">&#9633;</span>'
                    # No program page yet - show placeholder
                    champion['teamLinkHtml'] = '<span class="no-page-icon" style="color:#ddd;" title="Page coming soon">&#9633</span>'
                
                champions.append(champion)
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            logging.info(f"Output directory: {os.path.dirname(OUTPUT_FILE)}")
            
            # Write JSON file
            logging.info(f"Writing JSON to: {OUTPUT_FILE}")
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(champions, f, indent=2, ensure_ascii=False)
            
            file_size = os.path.getsize(OUTPUT_FILE)
            logging.info(f"✓ Successfully wrote {len(champions)} champions")
            logging.info(f"  File size: {file_size:,} bytes")
            
            # Summary statistics
            logging.info("")
            logging.info("=" * 60)
            logging.info("SUMMARY")
            logging.info("=" * 60)
            
            total = len(champions)
            with_ratings = sum(1 for c in champions if c.get('combined') is not None)
            undefeated = sum(1 for c in champions if c.get('undefeated'))
            with_coach = sum(1 for c in champions if c.get('coach'))
            with_page = sum(1 for c in champions if c.get('hasProgramPage'))
            
            logging.info(f"Total champions: {total}")
            logging.info(f"With ratings: {with_ratings} ({100*with_ratings//total}%)")
            logging.info(f"With program pages: {with_page}")
            logging.info(f"Undefeated seasons: {undefeated}")
            logging.info(f"With coach data: {with_coach}")
            
            # Year range
            years = [c['year'] for c in champions]
            logging.info(f"Earliest year: {min(years)}")
            logging.info(f"Latest year: {max(years)}")
            
            logging.info("=" * 60)
            logging.info("")
            
            # Show sample
            logging.info("2025 Champions:")
            for c in champions:
                if c['year'] == 2025:
                    rating = f"{c['combined']:.3f}" if c.get('combined') else 'N/A'
                    has_page = "✓ Has Page" if c.get('hasProgramPage') else ""
                    logging.info(f"  - {c['team']}: {c['record']} (Rating: {rating}) {has_page}")
            
            logging.info("")
            logging.info("✓ JSON generation complete!")
            logging.info(f"✓ File location: {OUTPUT_FILE}")
            
            return True
            
    except Exception as e:
        logging.error(f"Error generating JSON: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = generate_json()
    exit(0 if success else 1)