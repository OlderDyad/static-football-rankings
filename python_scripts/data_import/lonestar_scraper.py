"""
LoneStarFootball.net Scraper for Texas High School Football
Designed to scrape pre-2004 season data in batches with progress tracking
"""

import time
import random
import re
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from urllib.parse import urljoin, parse_qs, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pyodbc
import pandas as pd

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
BASE_URL = "https://lonestarfootball.net/"
SEARCH_URL = "https://lonestarfootball.net/search.asp"

# Scraping limits
TEAMS_PER_BATCH = 50
EARLIEST_SEASON = 1869  # Start of your historical data
LATEST_SEASON = 2003    # Only scrape pre-2004
WAIT_TIMEOUT = 15
HEADLESS_MODE = True

# Database connection
DB_CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER_NAME};"
    f"DATABASE={DATABASE_NAME};"
    f"Trusted_Connection=yes;"
)

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lonestar_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def setup_database_tables(cursor):
    """Create necessary tables if they don't exist"""
    
    # Table to track teams discovered
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'lonestar_teams')
        CREATE TABLE lonestar_teams (
            team_id INT PRIMARY KEY,
            team_name NVARCHAR(255),
            team_url NVARCHAR(500),
            classification NVARCHAR(50),
            district NVARCHAR(50),
            earliest_season INT,
            latest_season INT,
            discovered_date DATETIME DEFAULT GETDATE(),
            status NVARCHAR(50) DEFAULT 'pending',
            last_scraped DATETIME
        );
    """)
    
    # Table to track batches
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'lonestar_batches')
        CREATE TABLE lonestar_batches (
            batch_id INT IDENTITY(1,1) PRIMARY KEY,
            batch_name NVARCHAR(255),
            created_date DATETIME DEFAULT GETDATE(),
            completed_date DATETIME,
            total_teams INT,
            status NVARCHAR(50) DEFAULT 'running'
        );
    """)
    
    # Table to track team scraping progress
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'lonestar_scraping_status')
        CREATE TABLE lonestar_scraping_status (
            team_id INT,
            batch_id INT,
            status NVARCHAR(50) DEFAULT 'pending',
            attempts INT DEFAULT 0,
            last_attempt DATETIME,
            seasons_found INT DEFAULT 0,
            games_found INT DEFAULT 0,
            error_message NVARCHAR(MAX),
            PRIMARY KEY (team_id, batch_id),
            FOREIGN KEY (team_id) REFERENCES lonestar_teams(team_id),
            FOREIGN KEY (batch_id) REFERENCES lonestar_batches(batch_id)
        );
    """)
    
    # Raw games table (before standardization)
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'lonestar_games_raw')
        CREATE TABLE lonestar_games_raw (
            raw_id INT IDENTITY(1,1) PRIMARY KEY,
            batch_id INT,
            team_id INT,
            season INT,
            week NVARCHAR(50),
            game_date NVARCHAR(50),
            opponent_name_raw NVARCHAR(255),
            opponent_url NVARCHAR(500),
            opponent_team_id INT,
            home_away NVARCHAR(10),
            team_score INT,
            opponent_score INT,
            result_text NVARCHAR(255),
            scraped_date DATETIME DEFAULT GETDATE()
        );
    """)
    
    cursor.connection.commit()
    logger.info("Database tables verified/created")

def setup_and_get_batch(cursor, batch_name: str) -> Optional[int]:
    """Find running batch or create new one"""
    
    # Check for running batch
    cursor.execute("""
        SELECT TOP 1 batch_id 
        FROM lonestar_batches 
        WHERE status = 'running' 
        ORDER BY created_date DESC;
    """)
    
    running_batch = cursor.fetchone()
    if running_batch:
        logger.info(f"Resuming batch {running_batch[0]}")
        return running_batch[0]
    
    # Create new batch
    cursor.execute("""
        INSERT INTO lonestar_batches (batch_name, total_teams, status)
        OUTPUT INSERTED.batch_id
        VALUES (?, 0, 'running');
    """, batch_name)
    
    batch_id = cursor.fetchone()[0]
    cursor.connection.commit()
    logger.info(f"Created new batch {batch_id}")
    return batch_id

def get_teams_to_scrape(cursor, batch_id: int, limit: int) -> List[Tuple]:
    """Get next batch of teams to scrape"""
    
    cursor.execute(f"""
        SELECT TOP ({limit})
            t.team_id,
            t.team_name,
            t.team_url
        FROM lonestar_teams t
        LEFT JOIN lonestar_scraping_status s 
            ON t.team_id = s.team_id AND s.batch_id = ?
        WHERE s.status IS NULL 
           OR s.status IN ('pending', 'failed')
        ORDER BY 
            CASE WHEN s.status = 'failed' THEN 0 ELSE 1 END,
            t.team_id;
    """, batch_id)
    
    return cursor.fetchall()

def update_team_status(cursor, batch_id: int, team_id: int, 
                      status: str, seasons_found: int = 0, 
                      games_found: int = 0, error_msg: str = None):
    """Update scraping status for a team"""
    
    cursor.execute("""
        MERGE lonestar_scraping_status AS target
        USING (SELECT ? AS team_id, ? AS batch_id) AS source
        ON target.team_id = source.team_id AND target.batch_id = source.batch_id
        WHEN MATCHED THEN
            UPDATE SET 
                status = ?,
                attempts = attempts + 1,
                last_attempt = GETDATE(),
                seasons_found = ?,
                games_found = ?,
                error_message = ?
        WHEN NOT MATCHED THEN
            INSERT (team_id, batch_id, status, attempts, last_attempt, 
                    seasons_found, games_found, error_message)
            VALUES (?, ?, ?, 1, GETDATE(), ?, ?, ?);
    """, team_id, batch_id, status, seasons_found, games_found, error_msg,
         team_id, batch_id, status, seasons_found, games_found, error_msg)
    
    cursor.connection.commit()

def save_raw_games(cursor, games: List[Dict]):
    """Save scraped games to raw table"""
    
    if not games:
        return
    
    game_tuples = [
        (g['batch_id'], g['team_id'], g['season'], g['week'], 
         g['game_date'], g['opponent_name_raw'], g['opponent_url'],
         g['opponent_team_id'], g['home_away'], g['team_score'],
         g['opponent_score'], g['result_text'])
        for g in games
    ]
    
    cursor.executemany("""
        INSERT INTO lonestar_games_raw 
        (batch_id, team_id, season, week, game_date, opponent_name_raw,
         opponent_url, opponent_team_id, home_away, team_score, 
         opponent_score, result_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, game_tuples)
    
    cursor.connection.commit()

# ============================================================================
# SELENIUM SETUP
# ============================================================================

def setup_driver() -> webdriver.Chrome:
    """Configure and return Chrome WebDriver"""
    
    chrome_options = Options()
    
    if HEADLESS_MODE:
        chrome_options.add_argument("--headless")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    
    return driver

# ============================================================================
# PHASE 1: TEAM DISCOVERY
# ============================================================================

def discover_teams_sequential(driver, cursor, start_id: int = 1, end_id: int = 10000) -> int:
    """
    Alternative discovery: Scan sequential team IDs
    Faster but may miss some teams or find invalid IDs
    """
    
    logger.info(f"Starting sequential ID scan from {start_id} to {end_id}...")
    
    teams_found = 0
    checked = 0
    
    try:
        for team_id in range(start_id, end_id + 1):
            checked += 1
            
            try:
                team_url = f"https://lonestarfootball.net/team.asp?T={team_id}"
                driver.get(team_url)
                time.sleep(random.uniform(0.5, 1.5))
                
                # Check if page is valid (has team content)
                try:
                    # Look for indicators this is a real team page
                    team_indicators = driver.find_elements(By.CSS_SELECTOR, "h1, h2, .team-name, table")
                    
                    if not team_indicators:
                        continue  # Not a valid team page
                    
                    # Try to get team name
                    try:
                        team_name_element = driver.find_element(By.CSS_SELECTOR, "h1, h2")
                        team_name = team_name_element.text.strip()
                    except:
                        team_name = f"Team {team_id}"
                    
                    # Valid team found - add to database
                    cursor.execute("""
                        MERGE lonestar_teams AS target
                        USING (SELECT ? AS team_id) AS source
                        ON target.team_id = source.team_id
                        WHEN NOT MATCHED THEN
                            INSERT (team_id, team_name, team_url)
                            VALUES (?, ?, ?);
                    """, team_id, team_id, team_name, team_url)
                    
                    teams_found += 1
                    
                    if teams_found % 50 == 0:
                        cursor.connection.commit()
                        logger.info(f"Progress: {teams_found} teams found (checked {checked} IDs)")
                    
                except:
                    continue  # Page exists but doesn't look like a team
                
            except Exception as e:
                logger.debug(f"ID {team_id} not valid: {e}")
                continue
        
        cursor.connection.commit()
        logger.info(f"Sequential scan complete: {teams_found} teams found (checked {checked} IDs)")
        return teams_found
        
    except Exception as e:
        logger.error(f"Error during sequential scan: {e}", exc_info=True)
        return teams_found

def discover_all_teams(driver, cursor) -> int:
    """
    Phase 1: Discover all teams by crawling from known team or sequential ID scan
    Returns count of teams discovered
    """
    
    logger.info("Starting team discovery...")
    logger.info("Strategy: Crawl opponent links from known teams")
    
    teams_discovered = 0
    teams_to_visit = set()
    visited_teams = set()
    
    # Start with Highland Park (known team from your example)
    seed_teams = [
        (4027, "https://lonestarfootball.net/team.asp?T=4027", "Highland Park"),
        (1884, "https://lonestarfootball.net/team.asp?T=1884", "Rockwall-Heath"),
    ]
    
    # Add seed teams to database and queue
    for team_id, team_url, team_name in seed_teams:
        try:
            cursor.execute("""
                MERGE lonestar_teams AS target
                USING (SELECT ? AS team_id) AS source
                ON target.team_id = source.team_id
                WHEN NOT MATCHED THEN
                    INSERT (team_id, team_name, team_url)
                    VALUES (?, ?, ?);
            """, team_id, team_id, team_name, team_url)
            teams_to_visit.add(team_id)
            teams_discovered += 1
        except Exception as e:
            logger.warning(f"Error adding seed team {team_name}: {e}")
    
    cursor.connection.commit()
    logger.info(f"Added {len(seed_teams)} seed teams")
    
    try:
        # Crawl process: visit teams and find their opponents
        max_teams = 2000  # Safety limit
        
        while teams_to_visit and teams_discovered < max_teams:
            team_id = teams_to_visit.pop()
            
            if team_id in visited_teams:
                continue
            
            visited_teams.add(team_id)
            
            try:
                # Visit team page
                team_url = f"https://lonestarfootball.net/team.asp?T={team_id}"
                logger.info(f"Crawling team ID {team_id} ({teams_discovered} discovered, {len(teams_to_visit)} in queue)...")
                
                driver.get(team_url)
                time.sleep(random.uniform(1, 2))
                
                # Get team name from page
                try:
                    team_name_element = driver.find_element(By.CSS_SELECTOR, "h1, h2, .team-name")
                    page_team_name = team_name_element.text.strip()
                except:
                    page_team_name = f"Team {team_id}"
                
                # Find all opponent links on this page
                # Look for links to other team pages
                opponent_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='team.asp?T=']")
                
                new_teams_found = 0
                for link in opponent_links:
                    try:
                        opponent_url = link.get_attribute('href')
                        opponent_name = link.text.strip()
                        
                        if not opponent_url:
                            continue
                        
                        # Extract team ID
                        parsed = urlparse(opponent_url)
                        query_params = parse_qs(parsed.query)
                        opponent_id = int(query_params.get('T', [0])[0])
                        
                        if opponent_id == 0 or opponent_id in visited_teams:
                            continue
                        
                        # Add to database
                        cursor.execute("""
                            MERGE lonestar_teams AS target
                            USING (SELECT ? AS team_id) AS source
                            ON target.team_id = source.team_id
                            WHEN NOT MATCHED THEN
                                INSERT (team_id, team_name, team_url)
                                VALUES (?, ?, ?);
                        """, opponent_id, opponent_id, opponent_name or f"Team {opponent_id}", opponent_url)
                        
                        teams_to_visit.add(opponent_id)
                        teams_discovered += 1
                        new_teams_found += 1
                        
                    except Exception as e:
                        logger.debug(f"Error processing opponent link: {e}")
                        continue
                
                if new_teams_found > 0:
                    logger.info(f"  Found {new_teams_found} new teams from {page_team_name}")
                
                # Commit periodically
                if teams_discovered % 50 == 0:
                    cursor.connection.commit()
                    logger.info(f"Progress: {teams_discovered} teams discovered, {len(teams_to_visit)} in queue")
                
                # Polite delay
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.warning(f"Error crawling team {team_id}: {e}")
                continue
        
        cursor.connection.commit()
        logger.info(f"Team discovery complete: {teams_discovered} teams found")
        return teams_discovered
        
    except Exception as e:
        logger.error(f"Error during team discovery: {e}", exc_info=True)
        return teams_discovered

# ============================================================================
# PHASE 2: SCHEDULE SCRAPING
# ============================================================================

def extract_team_id_from_url(url: str) -> Optional[int]:
    """Extract team ID from LoneStar URL"""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        return int(query_params.get('T', [0])[0])
    except:
        return None

def scrape_team_seasons(driver, team_id: int, team_url: str, 
                       batch_id: int) -> List[Dict]:
    """
    Scrape all pre-2004 seasons for a given team
    Returns list of game dictionaries
    """
    
    all_games = []
    
    try:
        # Visit team page
        driver.get(team_url)
        time.sleep(random.uniform(2, 4))
        
        # Find all season links (looking for years 1869-2003)
        season_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='action=schedule']")
        
        seasons_to_scrape = []
        for link in season_links:
            try:
                season_url = link.get_attribute('href')
                season_text = link.text.strip()
                
                # Extract year from link text
                year_match = re.search(r'(\d{4})', season_text)
                if year_match:
                    year = int(year_match.group(1))
                    if EARLIEST_SEASON <= year <= LATEST_SEASON:
                        seasons_to_scrape.append((year, season_url))
            except:
                continue
        
        logger.info(f"Found {len(seasons_to_scrape)} seasons to scrape for team {team_id}")
        
        # Scrape each season
        for season, season_url in seasons_to_scrape:
            try:
                season_games = scrape_season_schedule(
                    driver, team_id, season, season_url, batch_id
                )
                all_games.extend(season_games)
                time.sleep(random.uniform(1, 3))  # Polite delay
                
            except Exception as e:
                logger.warning(f"Error scraping season {season} for team {team_id}: {e}")
                continue
        
        return all_games
        
    except Exception as e:
        logger.error(f"Error scraping team {team_id}: {e}")
        return []

def scrape_season_schedule(driver, team_id: int, season: int, 
                           season_url: str, batch_id: int) -> List[Dict]:
    """
    Scrape a single season's schedule
    Returns list of game dictionaries
    
    FIXED VERSION - matches actual LoneStar HTML structure
    Column structure: Week | Date | Opponent | Result
    """
    
    games = []
    
    try:
        driver.get(season_url)
        time.sleep(2)
        
        # Look for ALL tables - we'll filter by content
        tables = driver.find_elements(By.TAG_NAME, "table")
        
        schedule_rows = []
        
        # Find the schedule table (contains game data)
        for table in tables:
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            # Check if this looks like a schedule table
            # Schedule tables have rows with 4+ columns containing dates/scores
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                # Schedule rows have 4+ cells with specific content
                if len(cells) >= 4:
                    # Check if any cell contains a date pattern (mm/dd/yyyy)
                    has_date = False
                    for cell in cells:
                        text = cell.text.strip()
                        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):
                            has_date = True
                            break
                    
                    if has_date:
                        schedule_rows.append(row)
        
        logger.debug(f"Found {len(schedule_rows)} potential game rows")
        
        # Parse each schedule row
        for row in schedule_rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if len(cells) < 4:
                    continue
                
                # COLUMN STRUCTURE (based on Highland Park screenshot):
                # 0: Week (e.g., "1", "2", "District 1")
                # 1: Date (e.g., "09/05/2003")
                # 2: Opponent (e.g., "@Plano" or "Dallas Jesuit")
                # 3: Result (e.g., "W 52-49" or "L 21-28")
                
                week = cells[0].text.strip()
                game_date = cells[1].text.strip()
                
                # Opponent (may have @ prefix for away games)
                opponent_cell = cells[2]
                opponent_text = opponent_cell.text.strip()
                
                # Try to get opponent link
                opponent_link = opponent_cell.find_elements(By.TAG_NAME, "a")
                if opponent_link:
                    opponent_url = opponent_link[0].get_attribute('href')
                    opponent_team_id = extract_team_id_from_url(opponent_url)
                else:
                    opponent_url = ""
                    opponent_team_id = None
                
                # Determine home/away from @ symbol
                if opponent_text.startswith('@'):
                    home_away = "Away"
                    opponent_name = opponent_text[1:].strip()  # Remove @
                else:
                    home_away = "Home"
                    opponent_name = opponent_text
                
                # Result parsing
                result_text = cells[3].text.strip()
                
                # Skip if no score yet (future game or blank)
                if not result_text or result_text in ['', '-', 'TBD']:
                    continue
                
                # Parse score - handle formats:
                # "W 52-49", "L 21-28", "52-49", "W52-49", "L52-49"
                score_match = re.search(r'(\d+)\s*-\s*(\d+)', result_text)
                if not score_match:
                    logger.debug(f"Could not parse score from: {result_text}")
                    continue
                
                score1 = int(score_match.group(1))
                score2 = int(score_match.group(2))
                
                # Determine which score is team's score
                # If result starts with W, first score is team's
                # If result starts with L, second score is team's
                if result_text.upper().startswith('W'):
                    team_score = score1
                    opponent_score = score2
                elif result_text.upper().startswith('L'):
                    team_score = score2
                    opponent_score = score1
                else:
                    # No W/L prefix - assume first score is team's if higher
                    if score1 > score2:
                        team_score = score1
                        opponent_score = score2
                    else:
                        team_score = score2
                        opponent_score = score1
                
                # Create game dictionary
                game = {
                    'batch_id': batch_id,
                    'team_id': team_id,
                    'season': season,
                    'week': week,
                    'game_date': game_date,
                    'opponent_name_raw': opponent_name,
                    'opponent_url': opponent_url,
                    'opponent_team_id': opponent_team_id,
                    'home_away': home_away,
                    'team_score': team_score,
                    'opponent_score': opponent_score,
                    'result_text': result_text
                }
                
                games.append(game)
                
            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue
        
        logger.info(f"Scraped {len(games)} games for season {season}, team {team_id}")
        return games
        
    except Exception as e:
        logger.error(f"Error scraping season {season}: {e}")
        return []

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_team_discovery():
    """Run Phase 1: Discover all teams"""
    
    connection = None
    driver = None
    
    try:
        # Database setup
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        setup_database_tables(cursor)
        
        # Selenium setup
        driver = setup_driver()
        
        # Discover teams
        count = discover_all_teams(driver, cursor)
        
        logger.info(f"Discovery complete: {count} teams added to database")
        
    except Exception as e:
        logger.error(f"Error in team discovery: {e}", exc_info=True)
    
    finally:
        if driver:
            driver.quit()
        if connection:
            connection.close()

def run_batch_scraping(batch_size: int = TEAMS_PER_BATCH):
    """Run Phase 2: Scrape team schedules in batches"""
    
    connection = None
    driver = None
    
    try:
        # Database setup
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        setup_database_tables(cursor)
        
        # Get or create batch
        batch_name = f"LoneStar Batch - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        batch_id = setup_and_get_batch(cursor, batch_name)
        
        if not batch_id:
            logger.error("Could not create/find batch")
            return
        
        # Get teams to scrape
        teams = get_teams_to_scrape(cursor, batch_id, batch_size)
        
        if not teams:
            logger.info("No teams to scrape in this batch")
            return
        
        logger.info(f"Starting batch {batch_id}: {len(teams)} teams to process")
        
        # Selenium setup
        driver = setup_driver()
        
        # Process each team
        for i, (team_id, team_name, team_url) in enumerate(teams, 1):
            logger.info(f"[{i}/{len(teams)}] Processing: {team_name} (ID: {team_id})")
            
            try:
                # Scrape all seasons for this team
                games = scrape_team_seasons(driver, team_id, team_url, batch_id)
                
                # Save games to database
                if games:
                    save_raw_games(cursor, games)
                    logger.info(f"✓ Saved {len(games)} games for {team_name}")
                
                # Update status
                seasons_found = len(set(g['season'] for g in games))
                update_team_status(
                    cursor, batch_id, team_id, 'completed',
                    seasons_found=seasons_found,
                    games_found=len(games)
                )
                
            except Exception as e:
                error_msg = str(e)[:1000]
                logger.error(f"✗ Failed processing {team_name}: {error_msg}")
                update_team_status(
                    cursor, batch_id, team_id, 'failed',
                    error_msg=error_msg
                )
            
            # Polite delay between teams
            if i < len(teams):
                time.sleep(random.uniform(5, 10))
        
        logger.info(f"Batch {batch_id} complete")
        
        print("\n" + "="*60)
        print("  BATCH SCRAPING COMPLETE")
        print(f"  Batch ID: {batch_id}")
        print("  Next: Run SQL finalization procedure")
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Error in batch scraping: {e}", exc_info=True)
    
    finally:
        if driver:
            driver.quit()
        if connection:
            connection.close()

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main entry point with menu"""
    
    print("\n" + "="*60)
    print("  LoneStarFootball.net Scraper")
    print("  Texas High School Football (Pre-2004)")
    print("="*60)
    print("\nDiscovery Options:")
    print("  1. Crawl from seed teams (recommended, thorough)")
    print("  2. Sequential ID scan (faster but may miss teams)")
    print("\nScraping Options:")
    print("  3. Scrape team schedules (Phase 2)")
    print("\nFull Process:")
    print("  4. Discovery + Scraping")
    print("\nChoice: ", end="")
    
    choice = input().strip()
    
    if choice == "1":
        logger.info("Starting crawl-based team discovery...")
        run_team_discovery()
    
    elif choice == "2":
        print("\nSequential scan range:")
        print("  Enter start ID (default 1): ", end="")
        start = input().strip()
        start_id = int(start) if start else 1
        
        print("  Enter end ID (default 10000): ", end="")
        end = input().strip()
        end_id = int(end) if end else 10000
        
        logger.info(f"Starting sequential scan from {start_id} to {end_id}...")
        run_sequential_discovery(start_id, end_id)
    
    elif choice == "3":
        print("\nHow many teams per batch? (default 50): ", end="")
        batch_input = input().strip()
        batch_size = int(batch_input) if batch_input else TEAMS_PER_BATCH
        
        logger.info(f"Starting batch scraping ({batch_size} teams)...")
        run_batch_scraping(batch_size)
    
    elif choice == "4":
        print("\nFull process: Discovery method?")
        print("  1. Crawl (slower, more complete)")
        print("  2. Sequential (faster)")
        print("Choice: ", end="")
        discovery_choice = input().strip()
        
        if discovery_choice == "1":
            logger.info("Running crawl discovery + scraping...")
            run_team_discovery()
        else:
            logger.info("Running sequential discovery + scraping...")
            run_sequential_discovery(1, 10000)
        
        print("\nDiscovery complete. Start scraping? (y/n): ", end="")
        if input().strip().lower() == 'y':
            run_batch_scraping()
    
    else:
        print("Invalid choice. Exiting.")

def run_sequential_discovery(start_id: int = 1, end_id: int = 10000):
    """Run sequential ID scanning"""
    
    connection = None
    driver = None
    
    try:
        # Database setup
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        setup_database_tables(cursor)
        
        # Selenium setup
        driver = setup_driver()
        
        # Sequential scan
        count = discover_teams_sequential(driver, cursor, start_id, end_id)
        
        logger.info(f"Sequential discovery complete: {count} teams added to database")
        
    except Exception as e:
        logger.error(f"Error in sequential discovery: {e}", exc_info=True)
    
    finally:
        if driver:
            driver.quit()
        if connection:
            connection.close()

if __name__ == "__main__":
    main()