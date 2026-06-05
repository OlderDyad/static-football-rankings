# maxpreps_scraper_db_seasonal.py
# Based on: maxpreps_scraper_db.py - FINAL VERSION
#
# CHANGES vs the current production scraper (all additive / backward-compatible):
#   1. SEASON-AWARE URLs. A batch can carry a season slug (e.g. "22-23").
#      When present, schedule URLs become   .../football/22-23/schedule/
#      When NULL (current season), behavior is byte-for-byte the old script:
#                                            .../football/schedule/
#   2. The slug + year are read PER BATCH from dbo.scraping_batches, so the
#      same script handles the current season and ANY past season with zero
#      code edits between runs. (A --season 22-23 CLI override exists as a
#      fallback if the batch row has no slug set.)
#   3. games_raw is tagged with season_year so finalization never has to guess
#      the year from a page that may not display one.
#
# PREREQUISITE (run once, see prev_season_reimport_pilot_MO_2022.sql):
#   ALTER TABLE dbo.scraping_batches ADD season_slug VARCHAR(10) NULL, season_year INT NULL;
#   ALTER TABLE dbo.games_raw       ADD season_year INT NULL;

import argparse
import logging
import random
import re
import time
from datetime import datetime

import pyodbc
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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


def slug_to_year(slug):
    """'22-23' -> 2022. Returns None for an unparsable/empty slug."""
    if not slug:
        return None
    m = re.match(r'^(\d{2})-(\d{2})$', slug.strip())
    if not m:
        logger.warning(f"Season slug '{slug}' is not in YY-YY form; ignoring.")
        return None
    return 2000 + int(m.group(1))


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
        cookie_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
        logger.info("Cookie consent banner found. Clicking 'Accept'.")
        cookie_button.click()
        time.sleep(1)
    except TimeoutException:
        logger.info("No cookie consent banner found.")


def scrape_schedule_data_robust(driver, batch_id, primary_team_name, season_year=None):
    """Simplified function to collect raw data from a page.
    season_year is stamped onto every row so finalization can set Season
    explicitly instead of inferring it from page text."""
    games_data = []
    tables = driver.find_elements(By.TAG_NAME, 'table')
    if not tables:
        logger.warning("No schedule tables found on the page.")
        return []

    for table in tables:
        rows = table.find_elements(By.TAG_NAME, 'tr')[1:]
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) < 3:
                continue

            date = cells[0].text.strip()
            opponent_name_raw = cells[1].text.strip()
            result_text = cells[2].text.strip()

            opponent_url = ""
            try:
                opponent_url = cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href')
            except Exception:
                pass

            if not date or not opponent_name_raw:
                continue

            games_data.append({
                'primary_team_name': primary_team_name,
                'opponent_name_raw': opponent_name_raw,
                'result_text': result_text,
                'game_date': date,
                'opponent_maxpreps_url': opponent_url,
                'batch_id': batch_id,
                'season_year': season_year,
            })
    return games_data


# --- DATABASE FUNCTIONS ---
def setup_and_get_batch(cursor, batch_name, cli_season_slug=None):
    """Finds a running batch or creates a new one.
    Returns (batch_id, season_slug, season_year)."""
    sql_find_running = (
        "SELECT TOP 1 batch_id, season_slug, season_year "
        "FROM scraping_batches WHERE status = 'running' ORDER BY created_date DESC;"
    )
    running = cursor.execute(sql_find_running).fetchone()
    if running:
        batch_id = running.batch_id
        slug = running.season_slug
        year = running.season_year
        # CLI override only fills in a slug the batch row doesn't already have.
        if slug is None and cli_season_slug:
            slug = cli_season_slug
            year = slug_to_year(slug)
        logger.info(
            f"Resuming existing 'running' batch with ID: {batch_id} "
            f"(season={slug or 'current'})."
        )
        return batch_id, slug, year

    logger.info("No active batch found. Creating a new one (current season).")
    sql_teams_to_scrape = "SELECT T.Team_ID FROM dbo.HS_Team_MaxPreps AS T;"
    teams = cursor.execute(sql_teams_to_scrape).fetchall()
    if not teams:
        logger.warning("No teams found to create a new batch.")
        return None, None, None

    slug = cli_season_slug
    year = slug_to_year(slug)
    insert_sql = (
        "INSERT INTO scraping_batches (batch_name, created_date, total_teams, status, season_slug, season_year) "
        "OUTPUT INSERTED.batch_id VALUES (?, GETDATE(), ?, 'running', ?, ?);"
    )
    batch_id = cursor.execute(insert_sql, batch_name, len(teams), slug, year).fetchone()[0]

    status_entries = [(team.Team_ID, batch_id) for team in teams]
    sql_insert_status = "INSERT INTO dbo.team_scraping_status (team_id, batch_id) VALUES (?, ?);"
    cursor.executemany(sql_insert_status, status_entries)
    cursor.connection.commit()
    logger.info(f"Successfully created and populated batch {batch_id} (season={slug or 'current'}).")
    return batch_id, slug, year


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
    if not games_list:
        return

    game_tuples = [
        (g['primary_team_name'], g['opponent_name_raw'], g['result_text'],
         g['game_date'], g['opponent_maxpreps_url'], g['batch_id'], g['season_year'])
        for g in games_list
    ]
    sql = """
        INSERT INTO dbo.games_raw (primary_team_name, opponent_name_raw, result_text, game_date, opponent_maxpreps_url, batch_id, season_year)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    cursor.executemany(sql, game_tuples)
    cursor.connection.commit()


def get_urls_to_process(cursor, batch_id, limit, season_slug=None):
    """Uses the correct mapping table and adds robust URL cleaning.
    When season_slug is set, the schedule URL targets that historical season."""
    logger.info(f"Fetching up to {limit} teams for batch {batch_id} (season={season_slug or 'current'}).")

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

        # Repeatedly strip junk to get to the true base URL. Also strips a
        # trailing season slug (e.g. /22-23) so a base URL that already carries
        # one is normalized before we re-apply the requested season.
        while (base_url.endswith('/football')
               or base_url.endswith('/schedule')
               or re.search(r'/\d{2}-\d{2}$', base_url)):
            if base_url.endswith('/schedule'):
                base_url = base_url[:-len('/schedule')].rstrip('/')
            if re.search(r'/\d{2}-\d{2}$', base_url):
                base_url = re.sub(r'/\d{2}-\d{2}$', '', base_url).rstrip('/')
            if base_url.endswith('/football'):
                base_url = base_url[:-len('/football')].rstrip('/')

        # Build the URL: insert the season slug for historical seasons.
        if season_slug:
            schedule_url = f"{base_url}/football/{season_slug}/schedule/"
        else:
            schedule_url = f"{base_url}/football/schedule/"
        # --- End Logic ---

        final_urls.append((team.team_id, schedule_url, proper_name))

    return final_urls


# --- MAIN EXECUTION BLOCK ---
def main():
    parser = argparse.ArgumentParser(description="DB-driven MaxPreps scraper (season-aware).")
    parser.add_argument(
        "--season", default=None,
        help="Season slug fallback, e.g. 22-23. Only used if a resumed batch has no slug set. "
             "Prefer setting season_slug on the scraping_batches row instead.")
    args = parser.parse_args()

    logger.info("=== Starting Season-Aware DB-Driven MaxPreps Scraper ===")
    connection, batch_id = None, None
    try:
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        logger.info("Connected to database successfully.")

        batch_id, season_slug, season_year = setup_and_get_batch(cursor, BATCH_NAME, args.season)
        if not batch_id:
            return

        urls_to_process = get_urls_to_process(cursor, batch_id, URL_PROCESS_LIMIT, season_slug)
        if not urls_to_process:
            logger.info("No more teams to process for this batch. Marking as complete.")
            # Your logic to update batch status to 'completed' would go here.
            return

        logger.info(
            f"Starting to process {len(urls_to_process)} URLs for batch_id {batch_id} "
            f"(season={season_slug or 'current'}, year={season_year})"
        )
        driver = setup_driver()
        try:
            for i, (team_id, url, proper_name) in enumerate(urls_to_process, 1):
                logger.info(f"[{i}/{len(urls_to_process)}] Processing Team ID {team_id}: {url}")
                try:
                    driver.get(url)
                    handle_popups(driver)
                    games = scrape_schedule_data_robust(driver, batch_id, proper_name, season_year)
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
            print("\n" + "=" * 50)
            print("  SCRAPE COMPLETE. Before finalizing, inspect raw dates:")
            print(f"  SELECT DISTINCT game_date FROM dbo.games_raw WHERE batch_id = {batch_id};")
            print("  Then, when year handling is confirmed:")
            print(f"  EXEC dbo.FinalizeMaxPrepsData @BatchID = {batch_id};")
            print("=" * 50 + "\n")


if __name__ == "__main__":
    main()