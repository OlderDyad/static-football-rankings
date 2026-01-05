# generate_media_champions_json.py
"""
Generate Media National Champions JSON
CLEAN VERSION - Handles all SQL column name conversions properly
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
OUTPUT_FILE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/data/media-national-champions/media-national-champions.json"

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
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            logging.info("Executing: Get_Media_National_Champions")
            cursor.execute("EXEC Get_Media_National_Champions")
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            logging.info(f"Retrieved {len(rows)} champions")

            champions = []
            for row in rows:
                # Build dictionary with lowercase keys
                champion = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    key = col.lower()  # All keys lowercase
                    
                    # Handle special conversions
                    if isinstance(value, Decimal):
                        champion[key] = float(value)
                    elif isinstance(value, float):
                        champion[key] = round(value, 3)
                    else:
                        champion[key] = value
                
                # Create proper boolean and string fields
                champion['hasTeamPage'] = bool(champion.get('hasteampage', 0))
                champion['teamPageUrl'] = champion.get('teampageurl', '') or ''
                
                # Build link HTML
                if champion['hasTeamPage'] and champion['teamPageUrl']:
                    champion['teamLinkHtml'] = f'<a href="{champion["teamPageUrl"]}" class="team-link"><i class="fas fa-external-link-alt"></i></a>'
                else:
                    champion['teamLinkHtml'] = '<span class="no-page-icon" style="color:#ddd;">&#9633;</span>'
                
                # Clean up source display
                champion['source'] = champion.get('source', '') or champion.get('source_full', '') or 'N/A'
                
                # Remove internal/duplicate fields
                for key in ['hasteampage', 'teampageurl', 'source_code', 'source_full']:
                    champion.pop(key, None)
                
                champions.append(champion)

            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

            jsonData = {
                'topItem': champions[0] if champions else None,
                'items': champions,
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'media-national-champions',
                    'totalItems': len(champions),
                    'description': 'Media National Champions'
                }
            }

            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(jsonData, f, indent=2, ensure_ascii=False)

            logging.info(f"✓ Wrote {len(champions)} champions")
            logging.info(f"✓ With team pages: {sum(1 for c in champions if c['hasTeamPage'])}")
            logging.info("✓ Complete!")

            return True

    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = generate_json()
    exit(0 if success else 1)