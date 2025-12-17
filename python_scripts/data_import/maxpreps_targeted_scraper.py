"""
maxpreps_targeted_scraper.py
Scrapes individual teams or small batches using existing batch system.
Designed for adding new schools or re-scraping specific teams.
"""

import pyodbc
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=McKnights-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

HEADLESS_MODE = False  # Set to True for background scraping
WAIT_TIMEOUT = 15

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# SELENIUM SETUP
# ============================================================================

def setup_driver():
    """Initialize Chrome driver with options."""
    chrome_options = Options()
    if HEADLESS_MODE:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Let selenium-manager handle ChromeDriver automatically
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

def handle_cookie_banner(driver):
    """Dismiss cookie consent if present."""
    try:
        wait = WebDriverWait(driver, 5)
        cookie_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
        )
        cookie_button.click()
        time.sleep(1)
        logger.info("Cookie banner dismissed.")
    except TimeoutException:
        logger.info("No cookie banner found.")

# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def scrape_schedule_data(driver, batch_id, primary_team_name):
    """Scrape game data from MaxPreps schedule page."""
    games_data = []
    
    try:
        # Find all schedule tables
        tables = driver.find_elements(By.TAG_NAME, 'table')
        if not tables:
            logger.warning(f"No schedule tables found for {primary_team_name}")
            return []
        
        for table in tables:
            rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) < 3:
                    continue
                
                # Extract data from cells
                date = cells[0].text.strip()
                opponent_name_raw = cells[1].text.strip()
                result_text = cells[2].text.strip()
                
                # Get opponent URL if available
                opponent_url = ""
                try:
                    opponent_url = cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href')
                except NoSuchElementException:
                    pass
                
                # Skip invalid rows
                if not date or not opponent_name_raw:
                    continue
                
                games_data.append({
                    'primary_team_name': primary_team_name,
                    'opponent_name_raw': opponent_name_raw,
                    'result_text': result_text,
                    'game_date': date,
                    'opponent_maxpreps_url': opponent_url,
                    'batch_id': batch_id
                })
        
        logger.info(f"Found {len(games_data)} games for {primary_team_name}")
        return games_data
        
    except Exception as e:
        logger.error(f"Error scraping {primary_team_name}: {str(e)}")
        return []

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_batch_info(cursor, batch_id):
    """Get information about a specific batch."""
    sql = """
        SELECT 
            b.batch_id,
            b.batch_name,
            b.created_date,
            b.total_teams,
            b.status
        FROM scraping_batches b
        WHERE b.batch_id = ?
    """
    result = cursor.execute(sql, batch_id).fetchone()
    
    if not result:
        logger.error(f"Batch ID {batch_id} not found!")
        return None
    
    return {
        'batch_id': result[0],
        'batch_name': result[1],
        'created_date': result[2],
        'total_teams': result[3],
        'status': result[4]
    }

def get_teams_to_scrape(cursor, batch_id):
    """Get list of teams to scrape from batch."""
    sql = """
        SELECT 
            tss.team_id,
            t.Team_Name,
            mp.MaxPrepsURL
        FROM team_scraping_status tss
        INNER JOIN HS_Team_Names t ON tss.team_id = t.ID
        INNER JOIN HS_Team_MaxPreps mp ON t.ID = mp.Team_ID
        WHERE tss.batch_id = ?
          AND tss.status IN ('pending', 'failed')
        ORDER BY tss.team_id
    """
    teams = cursor.execute(sql, batch_id).fetchall()
    
    return [{
        'team_id': team[0],
        'team_name': team[1],
        'maxpreps_url': team[2]
    } for team in teams]

def clean_maxpreps_url(url):
    """Ensure URL is properly formatted for schedule page."""
    base_url = url.strip().rstrip('/')
    
    # Strip any existing /football or /schedule suffixes
    while base_url.endswith('/football') or base_url.endswith('/schedule'):
        if base_url.endswith('/schedule'):
            base_url = base_url[:-len('/schedule')].rstrip('/')
        if base_url.endswith('/football'):
            base_url = base_url[:-len('/football')].rstrip('/')
    
    # Build proper schedule URL
    return f"{base_url}/football/schedule/"

def update_team_status(cursor, batch_id, team_id, status, games_found=0, error_message=None):
    """Update scraping status for a team."""
    sql = """
        UPDATE team_scraping_status
        SET status = ?,
            attempts = attempts + 1,
            last_attempt = GETDATE(),
            games_found = ?,
            error_message = ?
        WHERE team_id = ? AND batch_id = ?
    """
    cursor.execute(sql, status, games_found, error_message, team_id, batch_id)
    cursor.connection.commit()

def save_games_to_db(cursor, games_list):
    """Save raw game data to games_raw table."""
    if not games_list:
        return
    
    game_tuples = [
        (
            g['primary_team_name'],
            g['opponent_name_raw'],
            g['result_text'],
            g['game_date'],
            g['opponent_maxpreps_url'],
            g['batch_id']
        )
        for g in games_list
    ]
    
    sql = """
        INSERT INTO games_raw (
            primary_team_name,
            opponent_name_raw,
            result_text,
            game_date,
            opponent_maxpreps_url,
            batch_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    cursor.executemany(sql, game_tuples)
    cursor.connection.commit()

def mark_batch_completed(cursor, batch_id):
    """Mark batch as completed."""
    sql = """
        UPDATE scraping_batches
        SET status = 'completed',
            completed_date = GETDATE()
        WHERE batch_id = ?
    """
    cursor.execute(sql, batch_id)
    cursor.connection.commit()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    logger.info("=" * 70)
    logger.info("TARGETED MAXPREPS SCRAPER")
    logger.info("=" * 70)
    
    # Get batch ID from user
    try:
        batch_id = int(input("\nEnter Batch ID to scrape: "))
    except ValueError:
        logger.error("Invalid batch ID. Must be a number.")
        return
    
    connection = None
    driver = None
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        logger.info("✅ Database connected")
        
        # Get batch info
        batch_info = get_batch_info(cursor, batch_id)
        if not batch_info:
            return
        
        logger.info(f"\nBatch Information:")
        logger.info(f"  Batch ID: {batch_info['batch_id']}")
        logger.info(f"  Name: {batch_info['batch_name']}")
        logger.info(f"  Total Teams: {batch_info['total_teams']}")
        logger.info(f"  Status: {batch_info['status']}")
        
        # Get teams to scrape
        teams = get_teams_to_scrape(cursor, batch_id)
        if not teams:
            logger.info("\n✅ No teams to scrape in this batch!")
            mark_batch_completed(cursor, batch_id)
            return
        
        logger.info(f"\n📋 Found {len(teams)} team(s) to scrape")
        
        # Set up Selenium driver
        logger.info("\nInitializing browser...")
        driver = setup_driver()
        logger.info("✅ Browser ready")
        
        # Process each team
        for idx, team in enumerate(teams, 1):
            team_id = team['team_id']
            team_name = team['team_name']
            url = clean_maxpreps_url(team['maxpreps_url'])
            
            logger.info(f"\n[{idx}/{len(teams)}] Processing: {team_name}")
            logger.info(f"  URL: {url}")
            
            try:
                # Navigate to schedule page
                driver.get(url)
                time.sleep(2)
                
                # Handle cookie banner on first page
                if idx == 1:
                    handle_cookie_banner(driver)
                
                # Scrape game data
                games = scrape_schedule_data(driver, batch_id, team_name)
                
                if games:
                    # Save to database
                    save_games_to_db(cursor, games)
                    update_team_status(cursor, batch_id, team_id, 'completed', len(games))
                    logger.info(f"  ✅ Saved {len(games)} games")
                else:
                    update_team_status(cursor, batch_id, team_id, 'completed', 0)
                    logger.info(f"  ⚠️ No games found")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"  ❌ Error: {error_msg}")
                update_team_status(cursor, batch_id, team_id, 'failed', 0, error_msg)
            
            # Small delay between teams
            time.sleep(1)
        
        # Mark batch as completed
        mark_batch_completed(cursor, batch_id)
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ SCRAPING COMPLETED")
        logger.info("=" * 70)
        logger.info(f"\nBatch ID: {batch_id}")
        logger.info(f"Teams Processed: {len(teams)}")
        logger.info("\nNext steps:")
        logger.info(f"  1. Run: EXEC FinalizeMaxPrepsData @BatchID = {batch_id};")
        logger.info(f"  2. Check for ambiguous opponents")
        logger.info(f"  3. Recalculate rankings")
        
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {str(e)}")
        raise
        
    finally:
        if driver:
            driver.quit()
            logger.info("\n🔒 Browser closed")
        if connection:
            connection.close()
            logger.info("🔒 Database connection closed")

if __name__ == "__main__":
    main()
