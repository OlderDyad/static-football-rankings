#!/usr/bin/env python3
"""
LoneStar Raw Text Collector
============================

This script DOES NOT parse games. It simply:
1. Visits each team's season pages
2. Copies the raw schedule text
3. Saves to CSV for processing in Excel

Your existing Excel formulas will handle the actual parsing.

Output CSV columns:
- team_id
- team_name  
- season
- schedule_url
- raw_schedule_text (the entire schedule section as text)
"""

import time
import random
import logging
import pyodbc
import csv
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

OUTPUT_CSV = "lonestar_raw_schedules.csv"
BATCH_SIZE = 2000 # Teams to process per run
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
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_teams_to_process(cursor, limit: int):
    """Get teams from lonestar_teams table"""
    sql = """
        SELECT TOP (?) team_id, team_name, team_url
        FROM lonestar_teams
        WHERE team_id NOT IN (
            SELECT DISTINCT team_id 
            FROM lonestar_raw_schedules
        )
        ORDER BY team_id;
    """
    return cursor.execute(sql, limit).fetchall()

def save_raw_schedule(cursor, team_id: int, team_name: str, season: int, 
                      season_url: str, raw_text: str):
    """Save raw schedule text to database"""
    sql = """
        INSERT INTO lonestar_raw_schedules 
        (team_id, team_name, season, season_url, raw_schedule_text, scraped_date)
        VALUES (?, ?, ?, ?, ?, GETDATE());
    """
    cursor.execute(sql, team_id, team_name, season, season_url, raw_text)
    cursor.connection.commit()

def setup_raw_schedules_table(cursor):
    """Create table if not exists"""
    sql = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'lonestar_raw_schedules')
    BEGIN
        CREATE TABLE lonestar_raw_schedules (
            id INT IDENTITY(1,1) PRIMARY KEY,
            team_id INT NOT NULL,
            team_name NVARCHAR(255),
            season INT NOT NULL,
            season_url NVARCHAR(500),
            raw_schedule_text NVARCHAR(MAX),
            scraped_date DATETIME DEFAULT GETDATE(),
            INDEX idx_team_season (team_id, season)
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
    Just like copy/pasting from the browser
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
            if 'Vs Common Opponents' in line or 'Common Opponents' in line:
                break
            
            if in_schedule:
                schedule_lines.append(line)
        
        return '\n'.join(schedule_lines)
        
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return ""

def scrape_team_seasons(driver, team_id: int, team_name: str, team_url: str, cursor):
    """
    Visit team page and collect raw schedule text for each season
    """
    schedules_collected = 0
    
    try:
        # Visit team page
        logger.info(f"Visiting {team_name} (ID: {team_id})")
        driver.get(team_url)
        time.sleep(random.uniform(2, 4))
        
        # Find all season links
        season_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='action=schedule']")
        
        seasons_to_scrape = []
        for link in season_links:
            try:
                season_url = link.get_attribute('href')
                season_text = link.text.strip()
                
                # Extract year
                import re
                year_match = re.search(r'(\d{4})', season_text)
                if year_match:
                    year = int(year_match.group(1))
                    if EARLIEST_SEASON <= year <= LATEST_SEASON:
                        seasons_to_scrape.append((year, season_url))
            except:
                continue
        
        logger.info(f"  Found {len(seasons_to_scrape)} seasons to collect")
        
        # Collect raw text from each season
        for season, season_url in seasons_to_scrape:
            try:
                driver.get(season_url)
                time.sleep(random.uniform(1, 2))
                
                raw_text = extract_raw_schedule_text(driver)
                
                if raw_text and len(raw_text) > 20:
                    save_raw_schedule(cursor, team_id, team_name, season, season_url, raw_text)
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
# EXPORT TO CSV
# ============================================================================

def export_to_csv(cursor, output_file: str):
    """Export collected raw schedules to CSV for Excel processing"""
    sql = """
        SELECT team_id, team_name, season, season_url, raw_schedule_text
        FROM lonestar_raw_schedules
        ORDER BY team_id, season DESC;
    """
    
    rows = cursor.execute(sql).fetchall()
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['team_id', 'team_name', 'season', 'season_url', 'raw_schedule_text'])
        
        for row in rows:
            writer.writerow([
                row.team_id,
                row.team_name,
                row.season,
                row.season_url,
                row.raw_schedule_text
            ])
    
    logger.info(f"Exported {len(rows)} schedules to {output_file}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("="*60)
    logger.info("LoneStar Raw Schedule Collector")
    logger.info("="*60)
    
    connection = None
    driver = None
    
    try:
        # Database setup
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        setup_raw_schedules_table(cursor)
        
        # Get teams to process
        teams = get_teams_to_process(cursor, BATCH_SIZE)
        
        if not teams:
            logger.info("No teams left to process!")
            
            # Export what we have
            export_to_csv(cursor, OUTPUT_CSV)
            return
        
        logger.info(f"Processing {len(teams)} teams...")
        
        # Setup browser
        driver = setup_driver()
        
        # Track team ID range
        team_ids = [team.team_id for team in teams]
        min_team_id = min(team_ids)
        max_team_id = max(team_ids)
        
        # Process each team
        total_schedules = 0
        for i, team in enumerate(teams, 1):
            logger.info(f"\n[{i}/{len(teams)}] {team.team_name} (ID: {team.team_id})")
            
            schedules = scrape_team_seasons(
                driver, 
                team.team_id, 
                team.team_name, 
                team.team_url,
                cursor
            )
            total_schedules += schedules
            
            # Polite delay between teams
            if i < len(teams):
                time.sleep(random.uniform(3, 6))
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH COMPLETE!")
        logger.info(f"{'='*60}")
        logger.info(f"Teams processed: {len(teams)}")
        logger.info(f"Team ID range: {min_team_id} - {max_team_id}")
        logger.info(f"Schedules collected: {total_schedules}")
        logger.info(f"{'='*60}")
        
        # Get overall progress
        cursor.execute("SELECT COUNT(DISTINCT team_id) FROM lonestar_raw_schedules")
        total_teams_completed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM lonestar_teams")
        total_teams_discovered = cursor.fetchone()[0]
        
        logger.info(f"\n📊 OVERALL PROGRESS:")
        logger.info(f"Total teams completed: {total_teams_completed}/{total_teams_discovered}")
        logger.info(f"Remaining teams: {total_teams_discovered - total_teams_completed}")
        logger.info(f"Percent complete: {total_teams_completed * 100.0 / total_teams_discovered:.1f}%")
        
        logger.info(f"\n📄 NEXT STEPS:")
        logger.info(f"1. Note the Team ID range: {min_team_id} - {max_team_id}")
        logger.info(f"2. Export this batch to Excel using team ID range")
        logger.info(f"3. Apply formulas and import to SQL")
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