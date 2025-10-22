# excel_to_sql_import.py
# Import MaxPreps URLs from Excel to SQL Server database

import pandas as pd
import pyodbc
import re
from urllib.parse import urlparse
import logging
from sqlalchemy import create_engine

# Configuration
EXCEL_FILE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/excel_files/MaxPreps_Export.xlsx"
SHEET_NAME = "active"  # Now that you've moved everything to active tab

# SQL Server connection configuration
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'

# For pyodbc connection string
CONNECTION_STRING = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_team_info_from_url(url):
    """Extract team information from MaxPreps URL"""
    try:
        # URL format: https://www.maxpreps.com/tx/abbott/abbott-panthers/football/schedule/
        parts = url.rstrip('/').split('/')
        
        if len(parts) >= 5:
            state_code = parts[3].upper()  # 'tx' -> 'TX'
            city = parts[4].replace('-', ' ').title()  # 'abbott' -> 'Abbott'
            
            if len(parts) >= 6:
                school_mascot = parts[5]  # 'abbott-panthers'
                # Try to extract mascot from the school-mascot format
                if '-' in school_mascot:
                    school_parts = school_mascot.split('-')
                    school_name = school_parts[0].title()
                    mascot = ' '.join(school_parts[1:]).title()
                else:
                    school_name = school_mascot.title()
                    mascot = ""
            else:
                school_name = city
                mascot = ""
            
            return {
                'state_code': state_code,
                'city': city,
                'school_name': school_name,
                'mascot': mascot
            }
    except Exception as e:
        logger.warning(f"Could not parse URL {url}: {e}")
    
    return {
        'state_code': '',
        'city': '',
        'school_name': '',
        'mascot': ''
    }

def create_canonical_name(city, school_name, mascot, state_code):
    """Create a standardized canonical name"""
    # Handle cases where school_name might be the same as city
    if school_name.lower() == city.lower():
        if mascot:
            return f"{city} {mascot} ({state_code})"
        else:
            return f"{city} ({state_code})"
    else:
        if mascot:
            return f"{school_name} {mascot} ({state_code})"
        else:
            return f"{school_name} ({state_code})"

def import_excel_to_sql():
    """Main import function"""
    try:
        # Read Excel file and check available sheets
        logger.info(f"Reading Excel file: {EXCEL_FILE}")
        
        # First, let's see what sheets are available
        excel_file = pd.ExcelFile(EXCEL_FILE)
        available_sheets = excel_file.sheet_names
        logger.info(f"Available sheets: {available_sheets}")
        
        # Try to find the right sheet
        sheet_to_use = None
        if SHEET_NAME in available_sheets:
            sheet_to_use = SHEET_NAME
        elif 'Active' in available_sheets:
            sheet_to_use = 'Active'
        elif len(available_sheets) == 1:
            sheet_to_use = available_sheets[0]
            logger.info(f"Using the only available sheet: {sheet_to_use}")
        else:
            # Let user choose
            logger.info("Please specify which sheet to use from the available options:")
            for i, sheet in enumerate(available_sheets):
                logger.info(f"  {i}: {sheet}")
            return
        
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_to_use)
        logger.info(f"Successfully read sheet '{sheet_to_use}' with {len(df)} rows")
        
        # Display column information
        logger.info(f"Columns in Excel: {df.columns.tolist()}")
        logger.info("Sample data:")
        print(df.head())
        
        # Ensure we have the URL column (adjust column name if needed)
        url_column = None
        possible_url_columns = ['URL', 'url', 'MaxPreps_URL', 'Link', 'link']
        for col in possible_url_columns:
            if col in df.columns:
                url_column = col
                break
        
        if not url_column:
            logger.error("Could not find URL column in Excel file")
            return
        
        logger.info(f"Using URL column: {url_column}")
        
        # Connect to SQL Server
        logger.info("Connecting to SQL Server...")
        conn = pyodbc.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Clear existing data (optional - remove if you want to append)
        logger.info("Clearing existing teams data...")
        cursor.execute("DELETE FROM teams")
        conn.commit()
        
        # Process each URL
        successful_imports = 0
        failed_imports = 0
        
        for index, row in df.iterrows():
            try:
                url = row[url_column]
                if pd.isna(url) or not url.strip():
                    logger.warning(f"Row {index}: Empty URL, skipping")
                    failed_imports += 1
                    continue
                
                # Extract team information from URL
                team_info = extract_team_info_from_url(url)
                
                # Create canonical name
                canonical_name = create_canonical_name(
                    team_info['city'],
                    team_info['school_name'],
                    team_info['mascot'],
                    team_info['state_code']
                )
                
                # Insert into database
                insert_query = """
                INSERT INTO teams (canonical_name, maxpreps_url, state_code, city, school_name, mascot)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(insert_query, (
                    canonical_name,
                    url,
                    team_info['state_code'],
                    team_info['city'],
                    team_info['school_name'],
                    team_info['mascot']
                ))
                
                successful_imports += 1
                
                if successful_imports % 100 == 0:
                    logger.info(f"Imported {successful_imports} teams...")
                    conn.commit()  # Commit periodically
                
            except Exception as e:
                logger.error(f"Error processing row {index}: {e}")
                failed_imports += 1
                continue
        
        # Final commit
        conn.commit()
        
        # Summary
        logger.info(f"Import completed:")
        logger.info(f"  Successful imports: {successful_imports}")
        logger.info(f"  Failed imports: {failed_imports}")
        
        # Verify import
        cursor.execute("SELECT COUNT(*) FROM teams")
        count = cursor.fetchone()[0]
        logger.info(f"Total teams in database: {count}")
        
        # Show sample of imported data
        cursor.execute("SELECT TOP 10 canonical_name, maxpreps_url, state_code FROM teams")
        sample_data = cursor.fetchall()
        logger.info("Sample imported data:")
        for row in sample_data:
            logger.info(f"  {row[0]} - {row[1]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Import failed: {e}")

def verify_import():
    """Verify the import was successful"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) as total_teams FROM teams")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT state_code) as states FROM teams WHERE state_code IS NOT NULL")
        states = cursor.fetchone()[0]
        
        cursor.execute("SELECT state_code, COUNT(*) as count FROM teams GROUP BY state_code ORDER BY count DESC")
        state_counts = cursor.fetchall()
        
        print(f"\n=== IMPORT VERIFICATION ===")
        print(f"Total teams imported: {total}")
        print(f"Number of states: {states}")
        print(f"\nTop states by team count:")
        for state, count in state_counts[:10]:
            print(f"  {state}: {count} teams")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")

if __name__ == "__main__":
    print("Starting MaxPreps URL import to SQL Server...")
    print(f"Excel file: {EXCEL_FILE}")
    print(f"Sheet: {SHEET_NAME}")
    print(f"Database: {DATABASE_NAME} on {SERVER_NAME}")
    
    # Perform import
    import_excel_to_sql()
    
    # Verify results
    verify_import()
    
    print("Import process completed!")