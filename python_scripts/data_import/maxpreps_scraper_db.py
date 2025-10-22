# maxpreps_scraper_db.py - FINAL VERSION

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import re
import random
import pyodbc
from datetime import datetime

# === CONFIGURATION ===
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
URL_PROCESS_LIMIT = 2000
WAIT_TIMEOUT = 15
BATCH_NAME = f"MaxPreps Scrape - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
DB_CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER_NAME};"
    f"DATABASE={DATABASE_NAME};"
    f"Trusted_Connection=yes;"
)

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- DRIVER AND SCRAPING FUNCTIONS ---
def setup_driver():
    """Sets up the Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

def handle_popups(driver, timeout=5):
    """Handles cookie consent pop-ups."""
    try:
        cookie_button = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
        logger.info("Cookie consent banner found. Clicking 'Accept'.")
        cookie_button.click()
        time.sleep(1)
    except TimeoutException:
        logger.info("No cookie consent banner found.")

def scrape_schedule_data_robust(driver, batch_id, primary_team_name):
    """Simplified function to collect raw data from a page."""
    games_data = []
    tables = driver.find_elements(By.TAG_NAME, 'table')
    if not tables:
        logger.warning("No schedule tables found on the page.")
        return []

    for table in tables:
        rows = table.find_elements(By.TAG_NAME, 'tr')[1:]
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) < 3: continue

            date = cells[0].text.strip()
            opponent_name_raw = cells[1].text.strip()
            result_text = cells[2].text.strip()
            
            opponent_url = ""
            try:
                opponent_url = cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href')
            except Exception:
                pass

            if not date or not opponent_name_raw: continue

            games_data.append({
                'primary_team_name': primary_team_name,
                'opponent_name_raw': opponent_name_raw,
                'result_text': result_text,
                'game_date': date,
                'opponent_maxpreps_url': opponent_url,
                'batch_id': batch_id
            })
    return games_data

# --- DATABASE FUNCTIONS ---
def setup_and_get_batch(cursor, batch_name):
    """Finds a running batch or creates a new one."""
    sql_find_running = "SELECT TOP 1 batch_id FROM scraping_batches WHERE status = 'running' ORDER BY created_date DESC;"
    running_batch = cursor.execute(sql_find_running).fetchone()
    if running_batch:
        logger.info(f"Resuming existing 'running' batch with ID: {running_batch[0]}")
        return running_batch[0]

    logger.info("No active batch found. Creating a new one.")
    sql_teams_to_scrape = "SELECT T.Team_ID FROM dbo.HS_Team_MaxPreps AS T;"
    teams = cursor.execute(sql_teams_to_scrape).fetchall()
    if not teams:
        logger.warning("No teams found to create a new batch.")
        return None

    insert_sql = "INSERT INTO scraping_batches (batch_name, created_date, total_teams, status) OUTPUT INSERTED.batch_id VALUES (?, GETDATE(), ?, 'running');"
    batch_id = cursor.execute(insert_sql, batch_name, len(teams)).fetchone()[0]
    
    status_entries = [(team.Team_ID, batch_id) for team in teams]
    sql_insert_status = "INSERT INTO dbo.team_scraping_status (team_id, batch_id) VALUES (?, ?);"
    cursor.executemany(sql_insert_status, status_entries)
    cursor.connection.commit()
    logger.info(f"Successfully created and populated batch {batch_id}.")
    return batch_id

def update_team_status(cursor, batch_id, team_id, status, games_found=0, error_message=None):
    """Updates the status of a scraped team."""
    sql = """
        UPDATE dbo.team_scraping_status
        SET status = ?, attempts = attempts + 1, last_attempt = GETDATE(), games_found = ?, error_message = ?
        WHERE team_id = ? AND batch_id = ?;
    """
    cursor.execute(sql, status, games_found, error_message, team_id, batch_id)
    cursor.connection.commit()

def save_raw_games_to_db(cursor, games_list):
    """Saves a list of raw game dictionaries to the database."""
    if not games_list: return

    game_tuples = [
        (g['primary_team_name'], g['opponent_name_raw'], g['result_text'], g['game_date'], g['opponent_maxpreps_url'], g['batch_id'])
        for g in games_list
    ]
    sql = """
        INSERT INTO dbo.games_raw (primary_team_name, opponent_name_raw, result_text, game_date, opponent_maxpreps_url, batch_id)
        VALUES (?, ?, ?, ?, ?, ?);
    """
    cursor.executemany(sql, game_tuples)
    cursor.connection.commit()

def get_urls_to_process(cursor, batch_id, limit):
    """
    Definitive version: Uses the correct mapping table and adds robust
    URL cleaning to handle inconsistent data.
    """
    logger.info(f"Fetching up to {limit} teams for batch {batch_id}.")
    
    sql = """
        SELECT TOP (?)
            S.team_id,
            M.URL AS MaxPrepsURL,
            M.ProperName
        FROM dbo.team_scraping_status AS S
        JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
        WHERE 
            S.batch_id = ? AND S.status IN ('pending', 'failed')
        ORDER BY 
            CASE WHEN S.status = 'failed' THEN 0 ELSE 1 END, S.team_id;
    """
    teams_to_process = cursor.execute(sql, limit, batch_id).fetchall()
    
    if not teams_to_process:
        logger.info("No more teams to process for this batch.")
        return []
        
    final_urls = []
    for team in teams_to_process:
        proper_name = team.ProperName if team.ProperName else "Unknown Team"

        # --- Definitive URL Cleaning Logic ---
        base_url = team.MaxPrepsURL.strip().rstrip('/')
        
        # Repeatedly strip any junk from the end to get to the true base URL
        while base_url.endswith('/football') or base_url.endswith('/schedule'):
            if base_url.endswith('/schedule'):
                base_url = base_url[:-len('/schedule')].rstrip('/')
            if base_url.endswith('/football'):
                base_url = base_url[:-len('/football')].rstrip('/')
        
        # Build the perfect URL every time
        schedule_url = f"{base_url}/football/schedule/"
        # --- End Logic ---
        
        final_urls.append((team.team_id, schedule_url, proper_name))
        
    return final_urls

# --- MAIN EXECUTION BLOCK ---
def main():
    logger.info("=== Starting Simplified DB-Driven MaxPreps Scraper ===")
    connection, batch_id = None, None
    try:
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        logger.info("Connected to database successfully.")
        
        batch_id = setup_and_get_batch(cursor, BATCH_NAME)
        if not batch_id: return

        urls_to_process = get_urls_to_process(cursor, batch_id, URL_PROCESS_LIMIT)
        if not urls_to_process:
            logger.info("No more teams to process for this batch. Marking as complete.")
            # Your logic to update batch status to 'completed' would go here.
            return

        logger.info(f"Starting to process {len(urls_to_process)} URLs for batch_id {batch_id}")
        driver = setup_driver()
        try:
            for i, (team_id, url, proper_name) in enumerate(urls_to_process, 1):
                logger.info(f"[{i}/{len(urls_to_process)}] Processing Team ID {team_id}: {url}")
                try:
                    driver.get(url)
                    handle_popups(driver)
                    games = scrape_schedule_data_robust(driver, batch_id, proper_name)
                    if games:
                        save_raw_games_to_db(cursor, games)
                        update_team_status(cursor, batch_id, team_id, 'completed', len(games))
                        logger.info(f"✓ Saved {len(games)} raw games for Team ID {team_id}")
                    else:
                        update_team_status(cursor, batch_id, team_id, 'completed', 0)
                        logger.warning(f"✗ No games found for Team ID {team_id}, but marking as complete.")
                except Exception as e:
                    error_msg = str(e).strip()[:1000]
                    update_team_status(cursor, batch_id, team_id, 'failed', error_message=error_msg)
                    logger.error(f"✗ Failed processing Team ID {team_id}: {error_msg}")
                
                if i < len(urls_to_process):
                    time.sleep(random.uniform(8, 15))
        finally:
            driver.quit()
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main process: {e}", exc_info=True)
    finally:
        if connection:
            connection.close()
            logger.info("Database connection closed.")
        if batch_id:
            print("\n" + "="*50)
            print("  SCRAPE COMPLETE. To finalize the data, run:")
            print(f"  EXEC dbo.FinalizeMaxPrepsData @BatchID = {batch_id};")
            print("="*50 + "\n")

if __name__ == "__main__":
    main()