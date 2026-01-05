# generate_media_champions_json.py
"""
Generate Media National Champions JSON
Focus: Championship recognition details (not rating breakdowns)
UPDATED: Fixed link field names (hasTeamPage, teamPageUrl)
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

            # Execute stored procedure (FIXED: removed sp_ prefix)
            logging.info("Executing: Get_Media_National_Champions")
            cursor.execute("EXEC Get_Media_National_Champions")

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

                    # Handle boolean conversion (FIXED: using HasTeamPage)
                    if column in ['HasTeamPage', 'hasTeamPage']:
                        champion['hasTeamPage'] = bool(value) if value is not None else False
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

                # FIXED: Generate link HTML based on hasTeamPage and teamPageUrl

                if champion.get('hasTeamPage') and champion.get('TeamPageUrl'):
                    champion['teamPageUrl'] = champion['TeamPageUrl']
                    champion['teamLinkHtml'] = f'<a href="{champion["teamPageUrl"]}" class="team-link" title="View {champion["team"]} team page"><i class="fas fa-external-link-alt"></i></a>'
                else:
                    champion['teamPageUrl'] = ''
                    champion['teamLinkHtml'] = '<span class="no-page-icon" style="color:#ddd;" title="Page coming soon">&#9633;</span>'

                # Remove duplicate SQL column names
                champion.pop('TeamPageUrl', None)
                champion.pop('HasTeamPage', None)
                champion.pop('Source', None)
                champion.pop('Coach', None)
                champion.pop('Notes', None)
                champion.pop('State', None)
                champion.pop('Year', None)
                champion.pop('Team', None)

                # Clean up source display
                if champion.get('source_full') or champion.get('Source'):
                    champion['source'] = champion.get('source_full') or champion.get('Source') or 'N/A'
                elif champion.get('source_code'):
                    champion['source'] = champion['source_code']
                else:
                    champion['source'] = 'N/A'

                champions.append(champion)

            # Create output directory if needed
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            logging.info(f"Output directory: {os.path.dirname(OUTPUT_FILE)}")

            # Get top item (most recent champion for banner)
            topChampion = champions[0] if champions else None

            # Create JSON structure
            jsonData = {
                'topItem': topChampion,
                'items': champions,
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'media-national-champions',
                    'yearRange': 'all-time',
                    'totalItems': len(champions),
                    'description': 'Media National Champions (Historical Recognition)',
                    'source': 'Media_National_Champions'
                }
            }

            # Write JSON file
            logging.info(f"Writing JSON to: {OUTPUT_FILE}")
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(jsonData, f, indent=2, ensure_ascii=False)

            file_size = os.path.getsize(OUTPUT_FILE)
            logging.info(f"✓ Successfully wrote {len(champions)} champions")
            logging.info(f"  File size: {file_size:,} bytes")

            # Summary statistics
            logging.info("")
            logging.info("=" * 60)
            logging.info("SUMMARY")
            logging.info("=" * 60)

            total = len(champions)
            with_ratings = sum(1 for c in champions if c.get('combined') and c.get('combined') > 0)
            with_page = sum(1 for c in champions if c.get('hasTeamPage'))
            with_coach = sum(1 for c in champions if c.get('coach') or c.get('Coach'))

            logging.info(f"Total champions: {total}")
            logging.info(f"With ratings: {with_ratings} ({100*with_ratings//total if total > 0 else 0}%)")
            logging.info(f"With coach names: {with_coach} ({100*with_coach//total if total > 0 else 0}%)")
            logging.info(f"With team pages: {with_page}")

            # Year range
            if champions:
                years = [c.get('year') or c.get('Year', 0) for c in champions]
                logging.info(f"Earliest year: {min(years)}")
                logging.info(f"Latest year: {max(years)}")

            logging.info("=" * 60)
            logging.info("")

            # Show sample
            current_year = max([c.get('year') or c.get('Year', 0) for c in champions]) if champions else 2025
            logging.info(f"{current_year} Champions:")
            for c in champions:
                champ_year = c.get('year') or c.get('Year')
                if champ_year == current_year:
                    rating = f"{c['combined']:.3f}" if c.get('combined') else 'N/A'
                    coach = c.get('coach') or c.get('Coach') or 'Unknown'
                    has_page = "✓ Has Page" if c.get('hasTeamPage') else ""
                    team_name = c.get('team') or c.get('Team', 'Unknown')
                    record = c.get('record') or c.get('Record', 'N/A')
                    logging.info(f"  - {team_name}: {record} - Coach: {coach} (Rating: {rating}) {has_page}")

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