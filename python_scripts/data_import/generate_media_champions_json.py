# generate_media_champions_json.py
"""
Generates JSON data for Media National Champions page
Calls sp_Get_Media_National_Champions_JSON stored procedure
Saves to docs/pages/public/data/media-national-champions.json
"""
import pyodbc
import json
import logging
import os
import sys

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
OUTPUT_FILE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/pages/public/data/media-national-champions.json"
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_json():
    """Generate JSON from stored procedure"""
    
    logging.info("="*60)
    logging.info("GENERATING MEDIA NATIONAL CHAMPIONS JSON")
    logging.info("="*60)
    
    try:
        # Connect to database
        logging.info(f"Connecting to database: {DATABASE_NAME}")
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                # Execute stored procedure
                logging.info("Executing stored procedure: sp_Get_Media_National_Champions_JSON")
                cursor.execute("EXEC sp_Get_Media_National_Champions_JSON")
                
                # Get column names
                columns = [column[0] for column in cursor.description]
                logging.info(f"Retrieved {len(columns)} columns")
                
                # Fetch all rows
                rows = cursor.fetchall()
                logging.info(f"Retrieved {len(rows)} champions from database")
                
                if len(rows) == 0:
                    logging.warning("No data returned from stored procedure!")
                    return False
                
                # Convert to list of dictionaries
                champions = []
                for row in rows:
                    champion = {}
                    for i, column in enumerate(columns):
                        value = row[i]
                        
                        # Convert undefeated to boolean
                        if column == 'undefeated':
                            value = bool(value) if value is not None else False
                        
                        # Handle None values for JSON
                        champion[column] = value
                    
                    champions.append(champion)
                
                # Ensure output directory exists
                output_dir = os.path.dirname(OUTPUT_FILE)
                if not os.path.exists(output_dir):
                    logging.info(f"Creating output directory: {output_dir}")
                    os.makedirs(output_dir, exist_ok=True)
                
                # Write JSON file
                logging.info(f"Writing JSON to: {OUTPUT_FILE}")
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(champions, f, indent=2, ensure_ascii=False, default=str)
                
                file_size = os.path.getsize(OUTPUT_FILE)
                logging.info(f"✓ Successfully wrote {len(champions)} champions")
                logging.info(f"  File size: {file_size:,} bytes")
                
                # Summary statistics
                with_ratings = sum(1 for c in champions if c.get('combined') is not None)
                undefeated = sum(1 for c in champions if c.get('undefeated'))
                with_coach = sum(1 for c in champions if c.get('coach') is not None)
                
                logging.info("")
                logging.info("="*60)
                logging.info("SUMMARY")
                logging.info("="*60)
                logging.info(f"Total champions: {len(champions)}")
                logging.info(f"With ratings: {with_ratings} ({with_ratings*100//len(champions)}%)")
                logging.info(f"Undefeated seasons: {undefeated}")
                logging.info(f"With coach data: {with_coach}")
                
                if len(champions) > 0:
                    logging.info(f"Earliest year: {champions[-1]['year']}")
                    logging.info(f"Latest year: {champions[0]['year']}")
                
                logging.info("="*60)
                
                # Show sample of 2025 champions
                champions_2025 = [c for c in champions if c.get('year') == 2025]
                if champions_2025:
                    logging.info("")
                    logging.info("2025 Champions:")
                    for c in champions_2025:
                        rating = f"{c['combined']:.3f}" if c.get('combined') else "N/A"
                        logging.info(f"  - {c['team']}: {c['record']} (Rating: {rating})")
                
                return True
                
    except pyodbc.Error as e:
        logging.error(f"Database error: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_json()
    
    if success:
        logging.info("")
        logging.info("✓ JSON generation complete!")
        sys.exit(0)
    else:
        logging.error("")
        logging.error("✗ JSON generation failed")
        sys.exit(1)