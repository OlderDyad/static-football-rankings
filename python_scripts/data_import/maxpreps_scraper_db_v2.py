# maxpreps_scraper_db_v2.py
#
# Based directly on: maxpreps_scraper_db.py - FINAL VERSION
#
# CHANGES vs the original (minimal — everything else is identical):
#
#   1. --season flag (e.g. --season 14-15). Prompted interactively if omitted.
#      Leave blank / omit for current season (behaves exactly like the original).
#
#   2. --state flag (e.g. --state FL). Optional — defaults to ALL teams in
#      HS_Team_MaxPreps, same as the original. Useful for targeted re-imports.
#
#   3. season_slug and season_year stored in scraping_batches so a resumed
#      batch knows which season it was scraping.
#
#   4. Past-season URL built as:
#        .../football/14-15/schedule/    (slug provided)
#      Current-season URL unchanged:
#        .../football/schedule/          (no slug)
#
#   5. season_year tagged on every games_raw row so FinalizeMaxPrepsData
#      (seasonaware version) stamps the correct year instead of GETDATE().
#
#   6. Driver resilience (from seasonal_v2): dead Chrome session is detected
#      and rebuilt automatically; per-team retry with backoff; consecutive
#      failure pause to handle throttling.
#
# FINALIZE with the season-aware proc:
#   EXEC dbo.FinalizeMaxPrepsData @BatchID = <B>;

import argparse
import logging
import random
import re
import time
from datetime import datetime

import pyodbc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIGURATION ===
SERVER_NAME       = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME     = "hs_football_database"
URL_PROCESS_LIMIT = 2000
WAIT_TIMEOUT      = 15
MAX_TEAM_RETRIES  = 3
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
    """'14-15' -> 2014. Returns None if blank or unparsable."""
    if not slug:
        return None
    m = re.match(r'^(\d{2})-(\d{2})$', slug.strip())
    if not m:
        logger.warning(f"Season slug '{slug}' is not in YY-YY form; treating as current season.")
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
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    )
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver


def is_driver_alive(driver):
    """True if the Selenium session is still responsive."""
    if driver is None:
        return False
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def ensure_driver(driver):
    """Return a live driver, rebuilding the browser if the session has died."""
    if is_driver_alive(driver):
        return driver
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass
    logger.info("Browser session dead. Starting a fresh session.")
    return setup_driver()


def handle_popups(driver, timeout=5):
    """Handles cookie consent pop-ups."""
    try:
        cookie_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
        logger.info("Cookie consent banner found. Clicking 'Accept'.")
        cookie_button.click()
        time.sleep(1)
    except TimeoutException:
        pass  # no banner — suppress noise


def scrape_schedule_data_robust(driver, batch_id, primary_team_name, season_year=None):
    """Collect raw game data from a schedule page.
    season_year is stamped on every row so finalization sets Season correctly."""
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

            date              = cells[0].text.strip()
            opponent_name_raw = cells[1].text.strip()
            result_text       = cells[2].text.strip()

            opponent_url = ""
            try:
                opponent_url = cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href')
            except Exception:
                pass

            if not date or not opponent_name_raw:
                continue

            games_data.append({
                'primary_team_name':     primary_team_name,
                'opponent_name_raw':     opponent_name_raw,
                'result_text':           result_text,
                'game_date':             date,
                'opponent_maxpreps_url': opponent_url,
                'batch_id':              batch_id,
                'season_year':           season_year,
            })
    return games_data


# --- DATABASE FUNCTIONS ---

def setup_and_get_batch(cursor, cli_season_slug=None, cli_state=None):
    """Finds a running batch and resumes it, or creates a new one.

    When resuming: reads season_slug / season_year from the existing batch row.
    When creating: prompts for season and optional state if not supplied via CLI,
                   then populates team_scraping_status from HS_Team_MaxPreps.

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

    logger.info("No active batch found. Creating a new one.")

    if cli_season_slug:
        slug = cli_season_slug.strip()
    else:
        slug = input(
            "Season slug (e.g. 14-15 for 2014, 22-23 for 2022 — "
            "leave blank for current season): "
        ).strip() or None

    if cli_state:
        state = cli_state.strip().upper()
    else:
        state = input(
            "State to scrape (2-letter code e.g. FL, or ALL for all teams) "
            "[default ALL]: "
        ).strip().upper() or "ALL"

    year = slug_to_year(slug)

    if state == "ALL":
        # National run — use HS_Team_MaxPreps which has the full 16k team list
        teams = cursor.execute(
            "SELECT DISTINCT Team_ID FROM dbo.HS_Team_MaxPreps;"
        ).fetchall()
    else:
        # State-filtered run — use URL_ProperName_Mapping which has correct
        # Team_IDs and State values after the 2026-06-08 ID/State fix
        teams = cursor.execute(
            """SELECT DISTINCT m.Team_ID
               FROM dbo.URL_ProperName_Mapping m
               JOIN dbo.HS_Team_Names t ON m.Team_ID = t.ID
               WHERE t.State = ?;""",
            state
        ).fetchall()

    if not teams:
        logger.warning(f"No teams found for state='{state}'. Check HS_Team_MaxPreps.")
        return None, None, None

    season_label = slug or "current"
    batch_name   = (
        f"MaxPreps Re-Import {state} {season_label} - "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    batch_id = cursor.execute(
        "INSERT INTO scraping_batches "
        "  (batch_name, created_date, total_teams, status, season_slug, season_year) "
        "OUTPUT INSERTED.batch_id "
        "VALUES (?, GETDATE(), ?, 'running', ?, ?);",
        batch_name, len(teams), slug, year
    ).fetchone()[0]

    cursor.executemany(
        "INSERT INTO dbo.team_scraping_status (team_id, batch_id) VALUES (?, ?);",
        [(t.Team_ID, batch_id) for t in teams]
    )
    cursor.connection.commit()

    logger.info(
        f"Created batch {batch_id}: {len(teams)} teams | "
        f"state={state} | season={season_label}"
    )
    return batch_id, slug, year


def update_team_status(cursor, batch_id, team_id, status, games_found=0, error_message=None):
    """Updates the status of a scraped team."""
    cursor.execute(
        """UPDATE dbo.team_scraping_status
           SET status = ?, attempts = attempts + 1, last_attempt = GETDATE(),
               games_found = ?, error_message = ?
           WHERE team_id = ? AND batch_id = ?;""",
        status, games_found, error_message, team_id, batch_id
    )
    cursor.connection.commit()


def save_raw_games_to_db(cursor, games_list):
    """Saves raw game rows to games_raw, including season_year tag."""
    if not games_list:
        return
    cursor.executemany(
        """INSERT INTO dbo.games_raw
               (primary_team_name, opponent_name_raw, result_text,
                game_date, opponent_maxpreps_url, batch_id, season_year)
           VALUES (?, ?, ?, ?, ?, ?, ?);""",
        [
            (g['primary_team_name'], g['opponent_name_raw'], g['result_text'],
             g['game_date'], g['opponent_maxpreps_url'], g['batch_id'], g['season_year'])
            for g in games_list
        ]
    )
    cursor.connection.commit()


def get_urls_to_process(cursor, batch_id, limit, season_slug=None):
    """Fetch next chunk of teams to scrape.
    Inserts season_slug into the schedule URL for past-season runs."""
    logger.info(
        f"Fetching up to {limit} teams for batch {batch_id} "
        f"(season={season_slug or 'current'})."
    )
    teams_to_process = cursor.execute(
        """SELECT TOP (?)
               S.team_id,
               M.URL AS MaxPrepsURL,
               M.ProperName
           FROM dbo.team_scraping_status AS S
           JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID
           WHERE S.batch_id = ? AND S.status IN ('pending', 'failed')
           ORDER BY CASE WHEN S.status = 'failed' THEN 0 ELSE 1 END, S.team_id;""",
        limit, batch_id
    ).fetchall()

    if not teams_to_process:
        logger.info("No more teams to process for this batch.")
        return []

    final_urls = []
    for team in teams_to_process:
        proper_name = team.ProperName or "Unknown Team"

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
        description="MaxPreps scraper — current or past season."
    )
    parser.add_argument(
        "--season", default=None,
        help="Season slug e.g. 14-15. Omit for current season."
    )
    parser.add_argument(
        "--state", default=None,
        help="2-letter state code e.g. FL. Omit for all states (default)."
    )
    args = parser.parse_args()

    logger.info("=== Starting MaxPreps Scraper v2 (current + past season) ===")
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
            logger.info("No more teams to process for this batch. Marking as complete.")
            cursor.execute(
                "UPDATE scraping_batches SET status='completed' WHERE batch_id=?;",
                batch_id
            )
            cursor.connection.commit()
            return

        logger.info(
            f"Starting: {len(urls_to_process)} URLs | "
            f"batch {batch_id} | season={season_slug or 'current'}"
        )

        driver = setup_driver()
        consecutive_failures = 0
        try:
            for i, (team_id, url, proper_name) in enumerate(urls_to_process, 1):
                logger.info(f"[{i}/{len(urls_to_process)}] Team ID {team_id}: {url}")

                success  = False
                last_err = None
                for attempt in range(1, MAX_TEAM_RETRIES + 1):
                    driver = ensure_driver(driver)
                    try:
                        driver.get(url)
                        handle_popups(driver)
                        games = scrape_schedule_data_robust(
                            driver, batch_id, proper_name, season_year
                        )
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
                            f"  Attempt {attempt}/{MAX_TEAM_RETRIES} failed "
                            f"for Team {team_id}: {last_err[:120]}"
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
                        f"✗ Gave up on Team {team_id} after {MAX_TEAM_RETRIES} attempts."
                    )

                # 5 consecutive failures = likely throttling — pause 5 minutes
                if consecutive_failures >= 5:
                    logger.error(
                        "5 consecutive failures — likely throttling. "
                        "Pausing 5 minutes. Re-running resumes failed teams first."
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
            print("  1. Inspect raw date format before finalizing:")
            print(f"     SELECT DISTINCT game_date, season_year")
            print(f"     FROM dbo.games_raw WHERE batch_id = {batch_id};")
            print("  2. Re-run to retry any failed teams:")
            print(f"     python maxpreps_scraper_db_v2.py")
            print("  3. When date format confirmed, finalize:")
            print(f"     EXEC dbo.FinalizeMaxPrepsData @BatchID = {batch_id};")
            print("=" * 50 + "\n")


if __name__ == "__main__":
    main()