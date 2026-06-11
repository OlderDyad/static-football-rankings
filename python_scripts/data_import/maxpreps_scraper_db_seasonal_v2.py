# maxpreps_scraper_db_seasonal_v2.py
# Based on: maxpreps_scraper_db_seasonal.py
#
# WHAT'S NEW vs v1 (resilience only; season logic unchanged):
#   - Driver health check: a dead Chrome/chromedriver session is detected and a
#     fresh browser is started automatically, instead of every remaining team
#     failing against a dead session (the WinError 10061 cascade).
#   - Per-team retry with backoff: a transient remote reset (10054) retries the
#     same URL a few times before the team is marked 'failed'.
#   - A team is only marked 'failed' after retries are exhausted, so re-running
#     (which scrapes 'failed' teams first) genuinely resumes where it stopped.
#
# WHAT'S NEW vs v2 original:
#   - Batch creation now uses URL_ProperName_Mapping (joined to HS_Team_Names)
#     instead of HS_Team_MaxPreps, which was found to be corrupted/incomplete.
#   - When no running batch exists, prompts for state and season interactively
#     (or accepts --state / --season on the command line for scripted runs).
#   - ALL keyword for --state scrapes all mapped teams nationally.
#
# Season behavior, URL building, DB writes, and the games_raw season_year tag
# are otherwise identical to v2 original.

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
SERVER_NAME   = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
URL_PROCESS_LIMIT  = 2000
WAIT_TIMEOUT       = 15
MAX_TEAM_RETRIES   = 3
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
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    )
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver


def is_driver_alive(driver):
    if driver is None:
        return False
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def ensure_driver(driver):
    if is_driver_alive(driver):
        return driver
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass
    logger.info("Browser session is dead or missing. Starting a fresh session.")
    return setup_driver()


def handle_popups(driver, timeout=5):
    try:
        cookie_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
        logger.info("Cookie consent banner found. Clicking 'Accept'.")
        cookie_button.click()
        time.sleep(1)
    except TimeoutException:
        pass


def scrape_schedule_data_robust(driver, batch_id, primary_team_name, season_year=None):
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

            date             = cells[0].text.strip()
            opponent_name_raw = cells[1].text.strip()
            result_text      = cells[2].text.strip()

            opponent_url = ""
            try:
                opponent_url = cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href')
            except Exception:
                pass

            if not date or not opponent_name_raw:
                continue

            games_data.append({
                'primary_team_name':    primary_team_name,
                'opponent_name_raw':    opponent_name_raw,
                'result_text':          result_text,
                'game_date':            date,
                'opponent_maxpreps_url': opponent_url,
                'batch_id':             batch_id,
                'season_year':          season_year,
            })
    return games_data


# --- DATABASE FUNCTIONS ---

def setup_and_get_batch(cursor, cli_season_slug=None, cli_state=None):
    """
    Finds a running batch and resumes it, or creates a new one.

    When creating a new batch:
      - Prompts for state and season if not supplied via CLI args.
      - Queries URL_ProperName_Mapping (joined to HS_Team_Names) for the team list.
        This is the same source the scraper uses when it actually fetches URLs,
        so the batch team list and the scrape list are always in sync.
      - State 'ALL' scrapes every mapped team nationally.

    Returns (batch_id, season_slug, season_year).
    """
    sql_find_running = (
        "SELECT TOP 1 batch_id, season_slug, season_year "
        "FROM scraping_batches WHERE status = 'running' ORDER BY created_date DESC;"
    )
    running = cursor.execute(sql_find_running).fetchone()
    if running:
        batch_id = running.batch_id
        slug     = running.season_slug
        year     = running.season_year
        if slug is None and cli_season_slug:
            slug = cli_season_slug
            year = slug_to_year(slug)
        logger.info(
            f"Resuming existing 'running' batch with ID: {batch_id} "
            f"(season={slug or 'current'})."
        )
        return batch_id, slug, year

    # ----------------------------------------------------------------
    # No running batch — gather parameters then create one
    # ----------------------------------------------------------------
    if cli_season_slug:
        slug = cli_season_slug.strip()
    else:
        slug = input(
            "\nNo running batch found. Enter season slug (e.g. 14-15 for 2014, "
            "22-23 for 2022, leave blank for current season): "
        ).strip() or None

    if cli_state:
        state = cli_state.strip().upper()
    else:
        state = input(
            "Enter state to scrape (2-letter code, e.g. FL  —  or ALL for all states): "
        ).strip().upper()

    year = slug_to_year(slug)

    # Query URL_ProperName_Mapping filtered by state
    if state == 'ALL':
        sql_teams = "SELECT DISTINCT Team_ID FROM dbo.URL_ProperName_Mapping WHERE Team_ID IS NOT NULL;"
        teams = cursor.execute(sql_teams).fetchall()
    else:
        sql_teams = """
            SELECT DISTINCT m.Team_ID
            FROM dbo.URL_ProperName_Mapping m
            JOIN dbo.HS_Team_Names t ON m.Team_ID = t.ID
            WHERE t.State = ?;
        """
        teams = cursor.execute(sql_teams, state).fetchall()

    if not teams:
        logger.warning(f"No mapped teams found for state='{state}'. Check HS_Team_Names.State values.")
        return None, None, None

    state_label    = state
    season_label   = slug or 'current'
    batch_name_str = (
        f"MaxPreps Re-Import {state_label} {season_label} - "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    insert_sql = (
        "INSERT INTO scraping_batches "
        "  (batch_name, created_date, total_teams, status, season_slug, season_year) "
        "OUTPUT INSERTED.batch_id "
        "VALUES (?, GETDATE(), ?, 'running', ?, ?);"
    )
    batch_id = cursor.execute(
        insert_sql, batch_name_str, len(teams), slug, year
    ).fetchone()[0]

    status_entries = [(team.Team_ID, batch_id) for team in teams]
    cursor.executemany(
        "INSERT INTO dbo.team_scraping_status (team_id, batch_id) VALUES (?, ?);",
        status_entries
    )
    cursor.connection.commit()

    logger.info(
        f"Created batch {batch_id}: {len(teams)} teams | "
        f"state={state_label} | season={season_label}"
    )
    return batch_id, slug, year


def update_team_status(cursor, batch_id, team_id, status, games_found=0, error_message=None):
    sql = """
        UPDATE dbo.team_scraping_status
        SET status = ?, attempts = attempts + 1, last_attempt = GETDATE(),
            games_found = ?, error_message = ?
        WHERE team_id = ? AND batch_id = ?;
    """
    cursor.execute(sql, status, games_found, error_message, team_id, batch_id)
    cursor.connection.commit()


def save_raw_games_to_db(cursor, games_list):
    if not games_list:
        return
    game_tuples = [
        (g['primary_team_name'], g['opponent_name_raw'], g['result_text'],
         g['game_date'], g['opponent_maxpreps_url'], g['batch_id'], g['season_year'])
        for g in games_list
    ]
    cursor.executemany(
        "INSERT INTO dbo.games_raw "
        "  (primary_team_name, opponent_name_raw, result_text, game_date, "
        "   opponent_maxpreps_url, batch_id, season_year) "
        "VALUES (?, ?, ?, ?, ?, ?, ?);",
        game_tuples
    )
    cursor.connection.commit()


def get_urls_to_process(cursor, batch_id, limit, season_slug=None):
    logger.info(f"Fetching up to {limit} teams for batch {batch_id} (season={season_slug or 'current'}).")
    sql = """
        SELECT TOP (?)
            S.team_id,
            M.URL AS MaxPrepsURL,
            M.ProperName
        FROM dbo.team_scraping_status AS S
        JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
        WHERE S.batch_id = ? AND S.status IN ('pending', 'failed')
        ORDER BY CASE WHEN S.status = 'failed' THEN 0 ELSE 1 END, S.team_id;
    """
    teams_to_process = cursor.execute(sql, limit, batch_id).fetchall()

    if not teams_to_process:
        logger.info("No more teams to process for this batch.")
        return []

    final_urls = []
    for team in teams_to_process:
        proper_name = team.ProperName if team.ProperName else "Unknown Team"

        base_url = team.MaxPrepsURL.strip().rstrip('/')
        while (base_url.endswith('/football')
               or base_url.endswith('/schedule')
               or re.search(r'/\d{2}-\d{2}$', base_url)):
            if base_url.endswith('/schedule'):
                base_url = base_url[:-len('/schedule')].rstrip('/')
            if re.search(r'/\d{2}-\d{2}$', base_url):
                base_url = re.sub(r'/\d{2}-\d{2}$', '', base_url).rstrip('/')
            if base_url.endswith('/football'):
                base_url = base_url[:-len('/football')].rstrip('/')

        if season_slug:
            schedule_url = f"{base_url}/football/{season_slug}/schedule/"
        else:
            schedule_url = f"{base_url}/football/schedule/"

        final_urls.append((team.team_id, schedule_url, proper_name))

    return final_urls


# --- MAIN EXECUTION BLOCK ---

def main():
    parser = argparse.ArgumentParser(
        description="DB-driven MaxPreps scraper (season-aware, resilient)."
    )
    parser.add_argument(
        "--season", default=None,
        help="Season slug, e.g. 14-15. Prompted interactively if omitted."
    )
    parser.add_argument(
        "--state", default=None,
        help="2-letter state code, e.g. FL. Use ALL for all states. Prompted if omitted."
    )
    args = parser.parse_args()

    logger.info("=== Starting Season-Aware DB-Driven MaxPreps Scraper (v2, resilient) ===")
    connection, batch_id = None, None
    try:
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor     = connection.cursor()
        logger.info("Connected to database successfully.")

        batch_id, season_slug, season_year = setup_and_get_batch(
            cursor,
            cli_season_slug=args.season,
            cli_state=args.state,
        )
        if not batch_id:
            return

        urls_to_process = get_urls_to_process(cursor, batch_id, URL_PROCESS_LIMIT, season_slug)
        if not urls_to_process:
            logger.info("No more teams to process for this batch.")
            return

        logger.info(
            f"Starting to process {len(urls_to_process)} URLs for batch_id {batch_id} "
            f"(season={season_slug or 'current'}, year={season_year})"
        )

        driver = setup_driver()
        consecutive_failures = 0
        try:
            for i, (team_id, url, proper_name) in enumerate(urls_to_process, 1):
                logger.info(f"[{i}/{len(urls_to_process)}] Processing Team ID {team_id}: {url}")

                success  = False
                last_err = None
                for attempt in range(1, MAX_TEAM_RETRIES + 1):
                    driver = ensure_driver(driver)
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
                            logger.warning(f"✗ No games found for Team ID {team_id}, marked complete.")
                        success = True
                        break
                    except Exception as e:
                        last_err = str(e).strip()[:1000]
                        logger.warning(
                            f"  Attempt {attempt}/{MAX_TEAM_RETRIES} failed for Team {team_id}: {last_err}"
                        )
                        if not is_driver_alive(driver):
                            driver = ensure_driver(driver)
                        if attempt < MAX_TEAM_RETRIES:
                            time.sleep(random.uniform(10, 20) * attempt)

                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    update_team_status(cursor, batch_id, team_id, 'failed', error_message=last_err)
                    logger.error(
                        f"✗ Gave up on Team {team_id} after {MAX_TEAM_RETRIES} attempts: {last_err}"
                    )

                if consecutive_failures >= 5:
                    logger.error(
                        "5 consecutive teams failed — likely throttling. "
                        "Pausing 5 minutes. Re-running resumes 'failed' teams first."
                    )
                    time.sleep(300)
                    consecutive_failures = 0

                if i < len(urls_to_process):
                    time.sleep(random.uniform(8, 15))
        finally:
            if is_driver_alive(driver):
                driver.quit()

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        if connection:
            connection.close()
            logger.info("Database connection closed.")
        if batch_id:
            print("\n" + "=" * 50)
            print("  SCRAPE PASS COMPLETE.")
            print("  Inspect raw date format before finalizing:")
            print(f"  SELECT DISTINCT game_date, season_year FROM dbo.games_raw WHERE batch_id = {batch_id};")
            print("  Any 'failed' teams are retried first on the next run.")
            print("  When date format is confirmed, finalize:")
            print(f"  EXEC dbo.FinalizeMaxPrepsData @BatchID = {batch_id};")
            print("=" * 50 + "\n")


if __name__ == "__main__":
    main()