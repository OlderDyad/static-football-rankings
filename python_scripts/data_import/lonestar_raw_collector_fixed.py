#!/usr/bin/env python3
"""
LoneStar Raw Text Collector - FIXED VERSION
============================================

USAGE:
    python lonestar_raw_collector_fixed.py START_ID END_ID

EXAMPLE:
    python lonestar_raw_collector_fixed.py 1802 2301

This script:
1. Visits each team's season pages in the specified ID range
2. Copies the raw schedule text
3. Saves to HS_Scores_LoneStar_Staging table with BatchID

Key fixes:
- Respects command-line START_ID and END_ID arguments
- Only processes teams in specified range
- Skips placeholder teams with no data
- Saves directly to staging table for export workflow
"""

import sys
import time
import random
import logging
import pyodbc
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=McKnights-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

EARLIEST_SEASON = 1869
LATEST_SEASON = 2003

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# SELENIUM SETUP
# ============================================================================

def setup_driver():
    """Setup headless Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_next_batch_id(cursor):
    """Get next available BatchID"""
    cursor.execute("""
        SELECT ISNULL(MAX(BatchID), 0) + 1 
        FROM HS_Scores_LoneStar_Staging
    """)
    return cursor.fetchone()[0]

def get_teams_in_range(cursor, start_id: int, end_id: int):
    """
    Get teams in specified ID range that haven't been scraped yet
    
    Returns list of (team_id, team_name, team_url) tuples
    """
    # First, ensure all team IDs in range exist in lonestar_teams table
    # (They should from discovery, but just in case)
    teams_to_scrape = []
    
    for team_id in range(start_id, end_id + 1):
        # Check if already scraped
        cursor.execute("""
            SELECT COUNT(*) 
            FROM HS_Scores_LoneStar_Staging 
            WHERE team_id = ?
        """, team_id)
        
        count = cursor.fetchone()[0]
        if count > 0:
            logger.debug(f"Team {team_id} already scraped, skipping")
            continue
        
        # Check if team exists in lonestar_teams
        cursor.execute("""
            SELECT team_name, team_url 
            FROM lonestar_teams 
            WHERE team_id = ?
        """, team_id)
        
        row = cursor.fetchone()
        if row:
            team_name = row[0]
            team_url = row[1]
        else:
            # Team not discovered yet, create URL
            team_name = f"Team {team_id}"
            team_url = f"https://lonestarfootball.net/team.asp?T={team_id}"
        
        teams_to_scrape.append((team_id, team_name, team_url))
    
    logger.info(f"Found {len(teams_to_scrape)} teams to scrape in range {start_id}-{end_id}")
    return teams_to_scrape

def save_raw_schedule(cursor, batch_id: int, team_id: int, team_name: str, 
                      season: int, raw_text: str):
    """Save raw schedule text to staging table"""
    
    # The raw text will be processed by export_team_range_to_excel.py later
    # For now, store it with team/season info
    sql = """
        INSERT INTO HS_Scores_LoneStar_Staging
        (team_id, team_name, season, Schedule_Text, BatchID, Import_Date, Status)
        VALUES (?, ?, ?, ?, ?, GETDATE(), 'Pending');
    """
    
    try:
        cursor.execute(sql, team_id, team_name, season, raw_text, batch_id)
        cursor.connection.commit()
    except Exception as e:
        logger.error(f"Error saving schedule for team {team_id}, season {season}: {e}")

def setup_staging_table(cursor):
    """Create staging table if not exists"""
    sql = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'HS_Scores_LoneStar_Staging')
    BEGIN
        CREATE TABLE HS_Scores_LoneStar_Staging (
            Access_ID INT IDENTITY(1,1) PRIMARY KEY,
            team_id INT NOT NULL,
            team_name NVARCHAR(255),
            season INT NOT NULL,
            Schedule_Text NVARCHAR(MAX),
            BatchID INT,
            Import_Date DATETIME DEFAULT GETDATE(),
            Status NVARCHAR(50) DEFAULT 'Pending',
            INDEX idx_team_season (team_id, season),
            INDEX idx_batch (BatchID)
        );
    END
    """
    cursor.execute(sql)
    cursor.connection.commit()

# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def extract_raw_schedule_text(driver) -> str:
    """
    Extract the entire schedule section as raw text
    This preserves the format for parsing by export script
    """
    try:
        # Wait for page to load
        time.sleep(2)
        
        # Get all text from the body
        body = driver.find_element(By.TAG_NAME, "body")
        raw_text = body.text
        
        # Find the schedule section
        # It starts with "XXXX Schedule" and ends before "Vs Common Opponents"
        lines = raw_text.split('\n')
        schedule_lines = []
        in_schedule = False
        
        for line in lines:
            # Start capturing at "Schedule" header
            if 'Schedule' in line and any(char.isdigit() for char in line):
                in_schedule = True
                continue
            
            # Stop at "Vs Common Opponents" or similar
            if in_schedule and ('Common Opponent' in line or 
                               'Vs Common' in line or 
                               'Download' in line or
                               'Print' in line):
                break
            
            if in_schedule and line.strip():
                schedule_lines.append(line)
        
        return '\n'.join(schedule_lines)
        
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return ""

def scrape_team_seasons(driver, batch_id: int, team_id: int, 
                       team_name: str, team_url: str, cursor):
    """
    Visit team page and collect raw schedule text for each season
    """
    schedules_collected = 0
    
    try:
        # Visit team page
        logger.info(f"Visiting {team_name} (ID: {team_id})")
        driver.get(team_url)
        time.sleep(random.uniform(2, 4))
        
        # Check if page is valid (has content)
        try:
            page_source = driver.page_source
            if "not found" in page_source.lower() or len(page_source) < 500:
                logger.info(f"  Team {team_id} appears to be a placeholder (no data)")
                return 0
        except:
            pass
        
        # Find all season links
        season_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='action=schedule']")
        
        seasons_to_scrape = []
        for link in season_links:
            try:
                season_url = link.get_attribute('href')
                season_text = link.text.strip()
                
                # Extract year
                year_match = re.search(r'(\d{4})', season_text)
                if year_match:
                    year = int(year_match.group(1))
                    if EARLIEST_SEASON <= year <= LATEST_SEASON:
                        seasons_to_scrape.append((year, season_url))
            except:
                continue
        
        if not seasons_to_scrape:
            logger.info(f"  No seasons found for team {team_id}")
            return 0
        
        logger.info(f"  Found {len(seasons_to_scrape)} seasons to collect")
        
        # Collect raw text from each season
        for season, season_url in seasons_to_scrape:
            try:
                driver.get(season_url)
                time.sleep(random.uniform(1, 2))
                
                raw_text = extract_raw_schedule_text(driver)
                
                if raw_text and len(raw_text) > 20:
                    save_raw_schedule(cursor, batch_id, team_id, team_name, 
                                    season, raw_text)
                    schedules_collected += 1
                    logger.info(f"  ✓ Collected {season}: {len(raw_text)} chars")
                else:
                    logger.warning(f"  ✗ No text for {season}")
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                logger.warning(f"  Error with season {season}: {e}")
                continue
        
        return schedules_collected
        
    except Exception as e:
        logger.error(f"Error scraping team {team_id}: {e}")
        return schedules_collected

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Parse command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python lonestar_raw_collector_fixed.py START_ID END_ID")
        print("Example: python lonestar_raw_collector_fixed.py 1802 2301")
        sys.exit(1)
    
    try:
        start_id = int(sys.argv[1])
        end_id = int(sys.argv[2])
    except ValueError:
        print("Error: START_ID and END_ID must be integers")
        sys.exit(1)
    
    if start_id > end_id:
        print("Error: START_ID must be less than or equal to END_ID")
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("LoneStar Raw Schedule Collector - FIXED")
    logger.info("="*60)
    logger.info(f"Team ID Range: {start_id} - {end_id}")
    logger.info(f"Total teams to check: {end_id - start_id + 1}")
    logger.info("="*60)
    
    connection = None
    driver = None
    
    try:
        # Database setup
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        setup_staging_table(cursor)
        
        # Get batch ID
        batch_id = get_next_batch_id(cursor)
        logger.info(f"Using BatchID: {batch_id}")
        logger.info("")
        
        # Get teams to process in specified range
        teams = get_teams_in_range(cursor, start_id, end_id)
        
        if not teams:
            logger.info("No teams to scrape in this range (all already scraped)")
            return
        
        logger.info(f"Processing {len(teams)} teams...")
        logger.info("")
        
        # Setup browser
        driver = setup_driver()
        
        # Process each team
        total_schedules = 0
        teams_processed = 0
        
        for i, (team_id, team_name, team_url) in enumerate(teams, 1):
            logger.info(f"\n[{i}/{len(teams)}] Team {team_id}: {team_name}")
            
            schedules = scrape_team_seasons(
                driver, 
                batch_id,
                team_id, 
                team_name, 
                team_url,
                cursor
            )
            
            if schedules > 0:
                teams_processed += 1
                total_schedules += schedules
            
            # Polite delay between teams
            if i < len(teams):
                time.sleep(random.uniform(3, 6))
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH COMPLETE!")
        logger.info(f"{'='*60}")
        logger.info(f"Teams checked: {len(teams)}")
        logger.info(f"Teams with data: {teams_processed}")
        logger.info(f"Team ID range: {start_id} - {end_id}")
        logger.info(f"Schedules collected: {total_schedules}")
        logger.info(f"BatchID: {batch_id}")
        logger.info(f"{'='*60}")
        
        # Get overall progress
        cursor.execute("""
            SELECT COUNT(DISTINCT team_id) 
            FROM HS_Scores_LoneStar_Staging
        """)
        total_teams_completed = cursor.fetchone()[0]
        
        logger.info(f"\n📊 OVERALL PROGRESS:")
        logger.info(f"Total unique teams scraped: {total_teams_completed}")
        logger.info(f"Total schedules in staging: Checking...")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM HS_Scores_LoneStar_Staging
        """)
        total_schedules_db = cursor.fetchone()[0]
        logger.info(f"Total schedules in staging: {total_schedules_db}")
        
        logger.info(f"\n📄 NEXT STEPS:")
        logger.info(f"1. Export this batch to Excel:")
        logger.info(f"   python export_team_range_to_excel.py {start_id} {end_id}")
        logger.info(f"2. Clean in Excel (apply VLOOKUP formulas)")
        logger.info(f"3. Import to SQL:")
        logger.info(f"   python import_lonestar_universal.py \"[path_to_v1_file]\"")
        logger.info(f"4. Run scraper again for next batch")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    
    finally:
        if driver:
            driver.quit()
        if connection:
            connection.close()

if __name__ == "__main__":
    main()