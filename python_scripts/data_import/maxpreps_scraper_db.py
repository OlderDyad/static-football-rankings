# maxpreps_scraper_db.py - FINAL VERSION
#
# 2026-09-11: Added alias-URL fallback for scraping. Each team's URL comes
# from URL_ProperName_Mapping as before, but get_urls_to_process() now also
# pulls any known historical/alternate URLs for that team from a companion
# table, URL_ProperName_Mapping_Aliases (Team_ID, URL) -- populated mainly
# by researching Unmatched_Opponents rows surfaced during FinalizeMaxPrepsData
# (see STATE_ONBOARDING_AND_CLEANUP_GUIDE.md). main() tries the primary URL
# first and falls back through the known aliases if it returns zero games,
# instead of giving up. If URL_ProperName_Mapping_Aliases doesn't exist yet
# in this database, aliases are silently skipped and behavior is identical
# to the previous version (kept as maxpreps_scraper_db_old.py).

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
import subprocess
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
# 2026-09-13: added a file handler alongside the console handler. Previously
# this only logged via basicConfig's default console stream, which is why
# last year's Task Scheduler run failed silently with no diagnostic record --
# Task Scheduler runs with no attached console, so every log line simply had
# nowhere to go. The log file lives next to this script and rotates by being
# overwritten each run is NOT what we want (we want a running history across
# many overnight runs), so mode='a' (append) is used, not 'w'.
import os as _os
_LOG_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "maxpreps_scraper_log.txt")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {_LOG_FILE}")

# --- DRIVER AND SCRAPING FUNCTIONS ---
# 2026-10-02 fix: orphaned headless Chrome cleanup. When chromedriver dies
# mid-run, the "dead browser session" recovery calls driver.quit(), which
# fails silently (nothing left to talk to), so the old headless Chrome kept
# running and a new one was started on top of it. 13 restarts between
# 10/01 and 10/02 left ~91 chrome.exe processes behind, using enough memory
# that the user's own Chrome would no longer open. Every Chrome this script
# starts now gets its own --user-data-dir with a fixed marker in the name,
# so leftovers can be found and killed by command line without ever
# touching the user's own Chrome windows.
_CHROME_PROFILE_MARKER = "maxpreps_scraper_chrome_"

def kill_orphaned_scraper_chrome():
    """Kill chrome.exe processes started by this scraper (matched by the
    profile marker) and delete their temp profile folders. Call only when no
    driver is in use -- it also kills the current one."""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
          "Where-Object { $_.CommandLine -like '*" + _CHROME_PROFILE_MARKER + "*' } | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=120)
    except Exception as e:
        logger.warning(f"Orphaned-Chrome cleanup failed: {e}")
    import glob, shutil, tempfile
    for d in glob.glob(_os.path.join(tempfile.gettempdir(), _CHROME_PROFILE_MARKER + "*")):
        shutil.rmtree(d, ignore_errors=True)

def setup_driver():
    """Sets up the Chrome driver."""
    chrome_options = Options()
    # 2026-09-15 fix: both automated 9PM runs (9/14, 9/15) failed within 8
    # seconds with "session not created: Chrome instance exited" -- confirmed
    # NOT a chromedriver/Chrome version mismatch (that was the 9/13 issue,
    # fixed separately by clearing the Selenium Manager cache). This time a
    # visible-but-blank Chrome window was observed sitting on a bare 'data:'
    # URL, meaning chromedriver spawned the process but the WebDriver session
    # handshake never completed. The PC's screen sleeps after 1 hour idle
    # (confirmed by the user; PC/disk power itself never sleeps) -- consistent
    # with non-headless Chrome's renderer/GPU process failing to attach once
    # the display is asleep at 9PM. --headless=new (the modern headless mode,
    # not the deprecated --headless) renders pages/JS identically without
    # needing a real display surface, so screen sleep can no longer interfere.
    chrome_options.add_argument("--headless=new")
    # 2026-09-16 fix: headless mode alone didn't hold -- the 9/15 9PM
    # Task-Scheduler-triggered run failed the same way (5 sec, "session not
    # created: Chrome instance exited"), while a manual interactive run
    # minutes later on the same machine/cache/config worked cleanly. That
    # rules out a recurring driver/Chrome version mismatch (same environment,
    # different outcome) and points at Task Scheduler's execution context
    # specifically. Even in headless mode Chrome still tries to initialize a
    # GPU process by default (the harmless "AMD VideoProcessorGetOutputExtension"
    # warning seen during interactive headless testing is this) -- under
    # Task Scheduler's more restricted context, GPU device access can be
    # denied outright instead of just warning, crashing Chrome at launch.
    # --disable-gpu is the standard companion flag for headless Chrome under
    # a constrained/service-like session; doesn't affect scraping since no
    # rendering/compositing is needed to read page text.
    chrome_options.add_argument("--disable-gpu")
    # 2026-09-18 fix: even after the script exits and driver.quit() closes
    # the main browser, Chrome's background update-checker helper process
    # was observed lingering for ~10 hours (repeated "Failed to open named
    # pipe server" errors from chrome\updater\ipc\update_service_dialer_win.cc,
    # every ~5 hours, until manually Ctrl+C'd) -- wasted CPU/RAM overnight,
    # harmless to data but worth stopping outright since this scraper never
    # needs Chrome's own auto-update mechanism to run at all.
    chrome_options.add_argument("--disable-component-update")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    # 2026-09-17 fix: four separate hypothesis-driven fixes (chromedriver
    # cache clear, --headless=new, --disable-gpu, removing -RunLevel Highest)
    # have ALL failed to stop "session not created: Chrome instance exited"
    # under Task Scheduler, while every interactive test succeeds -- with no
    # real detail beyond that generic, symbol-less Selenium-level message.
    # Capturing chromedriver's own verbose log is the actual next step,
    # instead of guessing at a 5th cause blind. This writes chromedriver's
    # internal diagnostic output (the real OS-level failure reason -- e.g.
    # a specific DLL/permission/process-creation error) to a file for
    # inspection after the next Task-Scheduler-triggered failure.
    driver_log_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "chromedriver_verbose.log")
    import tempfile
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp(prefix=_CHROME_PROFILE_MARKER)}")
    service = Service(log_output=driver_log_path, service_args=['--verbose'])
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
                # 2026-09-19 fix: the raw href MaxPreps links to on a schedule
                # row is the opponent's TEAM HOME page (e.g. ".../mustangs/
                # football/"), never their schedule sub-page -- unlike the
                # PRIMARY team's URL, which always goes through
                # _clean_schedule_url() before we navigate to it. Without this
                # same normalization here, EVERY opponent_maxpreps_url stored
                # in games_raw fails to match URL_ProperName_Mapping.URL
                # (always ".../football/schedule/") in FinalizeMaxPrepsData's
                # join -- confirmed via batch 33: 96,198 games logged to
                # Unmatched_Opponents, 0 reached HS_Scores, 100% failure.
                opponent_url = _clean_schedule_url(
                    cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href')
                )
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
def setup_and_get_batch(cursor, batch_name, force_new=False):
    """Finds a running batch or creates a new one.

    2026-09-14 fix: scraping_batches/team_scraping_status are SHARED with
    other tools (confirmed: rescrape_2019_ambiguous.py, used for task #40's
    2019 date-truncation reconciliation, creates its own batches in these
    same tables, named "2019 Date Truncation Reconciliation - <timestamp>").
    The old query here -- "any batch with status='running'" -- doesn't
    distinguish whose batch it is. On 2026-09-13/14 this actually happened:
    our automation resumed and auto-finalized two of that tool's batches
    (31, 32), including scraping one team (Barnsdall) through the WRONG
    URL-building logic (current-season page instead of the 2019 historical
    page the reconciliation tool targets), before this fix existed. Verified
    that specific incident didn't corrupt data (the 4 finalized rows were
    legitimately 2019-dated), but the risk was real and remains for batches
    27/28/30 (still have genuine pending reconciliation work) unless this
    query is scoped to only OUR OWN batches. BATCH_NAME below always starts
    with "MaxPreps Scrape - ", so filtering on that prefix is safe and
    matches only batches this script itself created.
    """
    sql_find_running = ("SELECT TOP 1 batch_id FROM scraping_batches "
                         "WHERE status = 'running' AND batch_name LIKE 'MaxPreps Scrape - %' "
                         "ORDER BY created_date DESC;")
    running_batch = cursor.execute(sql_find_running).fetchone()
    if running_batch:
        logger.info(f"Resuming existing 'running' MaxPreps batch with ID: {running_batch[0]}")
        return running_batch[0]

    # 2026-09-13 fix (superseded 2026-09-25): originally only started a
    # brand-new (full re-scrape) batch on Sunday nights, to stop the nightly
    # trigger from launching a fresh 16k-team batch every single night the
    # instant the prior one flipped to 'completed'. That assumed a batch
    # would take close to a full week to drain.
    #
    # 2026-09-25 fix: that assumption broke once batch 34 hit the known
    # permanently-pending duplicate-team-record floor (~973 teams / 6,552
    # team_scraping_status rows with no joinable URL_ProperName_Mapping
    # entry -- see task #52 / STATE_ONBOARDING_AND_CLEANUP_GUIDE.md).
    # get_urls_to_process() can never return those rows (INNER JOIN filters
    # them out), so once every *joinable* team is done, the batch legitimately
    # finishes in days, not a week -- confirmed live: batch 34 (created
    # Sunday 9/20) hit empty results by Thursday 9/24, then sat idle firing
    # ~19-second no-op runs every night until the next Sunday under the old
    # gate. Removing the day-of-week restriction means a finished batch is
    # immediately followed by a new one on the very next run (manual or
    # watcher), instead of losing up to 6 idle days of score-collection each
    # cycle. force_new (--force-new-batch) is kept as a param for backward
    # compatibility but no longer changes behavior here -- both paths now do
    # the same thing.
    logger.info("No active MaxPreps batch found; creating a new one.")
    # 2026-09-25 fix: build the batch from URL_ProperName_Mapping, NOT
    # HS_Team_MaxPreps. HS_Team_MaxPreps is known-corrupted (some Team_IDs
    # were wrongly assigned hundreds of other schools' URLs): 16,333 rows but
    # only 8,370 distinct Team_IDs, 973 of them with no mapping URL at all.
    # Because get_urls_to_process() picks each team's URL from
    # URL_ProperName_Mapping by Team_ID, every school whose URL had been
    # folded into a wrong Team_ID was silently never scraped -- 2026 had only
    # 7,384 teams with games vs 2025's 16,120. URL_ProperName_Mapping has
    # 16,230 distinct mapped Team_IDs, and maxpreps_scraper_db_seasonal_v2.py
    # (June 2026 re-import) already switched to this same query for the same
    # reason; the fix just never made it into this weekly scraper. Side
    # effect: no more duplicate status rows and no permanently-pending floor,
    # since every team in the batch is joinable by construction.
    # 2026-09-25 follow-up: first run with the query above failed on
    # FK__team_scra__team___7B863AD4 -- some URL_ProperName_Mapping.Team_IDs
    # no longer exist in HS_Team_Names (orphaned by merges/removals), and
    # team_scraping_status.team_id is FK'd to HS_Team_Names.ID. Joining to
    # HS_Team_Names keeps only valid teams (same join the seasonal_v2
    # per-state path already used).
    sql_teams_to_scrape = """
        SELECT DISTINCT M.Team_ID
        FROM dbo.URL_ProperName_Mapping AS M
        JOIN dbo.HS_Team_Names AS T ON T.ID = M.Team_ID
        WHERE M.Team_ID IS NOT NULL;
    """
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

def _clean_schedule_url(raw_url):
    """Same base-URL cleaning as before, factored out so it can be applied
    to alias URLs too."""
    base_url = raw_url.strip().rstrip('/')
    while base_url.endswith('/football') or base_url.endswith('/schedule'):
        if base_url.endswith('/schedule'):
            base_url = base_url[:-len('/schedule')].rstrip('/')
        if base_url.endswith('/football'):
            base_url = base_url[:-len('/football')].rstrip('/')
    return f"{base_url}/football/schedule/"

def get_urls_to_process(cursor, batch_id, limit):
    """
    Uses the correct mapping table and adds robust URL cleaning to handle
    inconsistent data.

    Returns each team's candidate URLs as a LIST (primary URL first, then
    any known historical/alias URLs from URL_ProperName_Mapping_Aliases),
    so main() can fall back to an alias if the primary URL no longer has
    the team's schedule (slug changed, page moved, school renamed, etc.).
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

    team_ids = [team.team_id for team in teams_to_process]

    # Pull any known historical/alias URLs for these teams in one query.
    # URL_ProperName_Mapping_Aliases(Team_ID, URL) is a companion table --
    # see STATE_ONBOARDING_AND_CLEANUP_GUIDE.md for how it gets populated
    # (mainly from researching Unmatched_Opponents rows). If the table
    # doesn't exist yet in this database, aliases are just skipped --
    # behavior is then identical to the old script (maxpreps_scraper_db_old.py).
    aliases_by_team = {}
    try:
        placeholders = ",".join("?" for _ in team_ids)
        alias_sql = f"""
            SELECT Team_ID, URL FROM dbo.URL_ProperName_Mapping_Aliases
            WHERE Team_ID IN ({placeholders})
            ORDER BY Team_ID, AddedAt DESC;
        """
        for row in cursor.execute(alias_sql, *team_ids).fetchall():
            aliases_by_team.setdefault(row.Team_ID, []).append(row.URL)
    except pyodbc.Error as e:
        logger.warning(f"URL_ProperName_Mapping_Aliases not available ({e}); "
                        f"continuing with primary URLs only.")

    final_urls = []
    for team in teams_to_process:
        proper_name = team.ProperName if team.ProperName else "Unknown Team"
        candidates = [_clean_schedule_url(team.MaxPrepsURL)]
        for alias_url in aliases_by_team.get(team.team_id, []):
            cleaned = _clean_schedule_url(alias_url)
            if cleaned not in candidates:
                candidates.append(cleaned)
        final_urls.append((team.team_id, candidates, proper_name))

    return final_urls

# --- SINGLE-INSTANCE GUARD ---
# 2026-09-21 fix: two manually-launched runs overlapped (06:27 and 11:05,
# both with an 8-hour cap) and are the likely cause of an SSMS lock-up that
# day -- two concurrent processes both writing to games_raw/HS_Scores/
# Unmatched_Opponents/team_scraping_status, made worse by the periodic
# finalize (every 200 teams) added 2026-09-21 running twice as often as
# before. A simple PID-checked lock file refuses a second start rather than
# relying on remembering to check Get-CimInstance by hand every time.
_LOCK_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "maxpreps_scraper.lock")

def acquire_lock():
    """Returns True if the lock was acquired (safe to proceed), False if
    another instance appears to already be running."""
    if _os.path.exists(_LOCK_FILE):
        try:
            with open(_LOCK_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            result = subprocess.run(['tasklist', '/FI', f'PID eq {old_pid}'],
                                     capture_output=True, text=True)
            if str(old_pid) in result.stdout:
                logger.error(f"Another instance (PID {old_pid}) appears to already be "
                             f"running (lock file: {_LOCK_FILE}). Refusing to start a "
                             f"second concurrent scraper -- this caused a real SSMS "
                             f"lock-up incident on 2026-09-21. If that PID is definitely "
                             f"not actually running anymore, delete the lock file and retry.")
                return False
        except Exception:
            pass  # stale/corrupt lock file contents -- fall through and overwrite it
    with open(_LOCK_FILE, 'w') as f:
        f.write(str(_os.getpid()))
    return True

def release_lock():
    try:
        _os.remove(_LOCK_FILE)
    except Exception:
        pass

# --- MAIN EXECUTION BLOCK ---
def main():
    import argparse
    parser = argparse.ArgumentParser(description="MaxPreps current-season scraper.")
    parser.add_argument('--force-new-batch', action='store_true',
                         help="Start a new full-sweep batch now even if today isn't Sunday. "
                              "For manual/deliberate kickoffs only -- never pass this from "
                              "an unattended/scheduled run.")
    args = parser.parse_args()

    logger.info("=== Starting Simplified DB-Driven MaxPreps Scraper ===" +
                (" (--force-new-batch)" if args.force_new_batch else ""))

    if not acquire_lock():
        return

    connection, batch_id = None, None
    try:
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        logger.info("Connected to database successfully.")

        batch_id = setup_and_get_batch(cursor, BATCH_NAME, force_new=args.force_new_batch)
        if not batch_id: return

        urls_to_process = get_urls_to_process(cursor, batch_id, URL_PROCESS_LIMIT)
        if not urls_to_process:
            logger.info("No more teams to process for this batch. Marking as complete.")
            # 2026-09-13 fix: this used to be a no-op comment, meaning
            # setup_and_get_batch()'s "WHERE status = 'running'" lookup would
            # find this same finished batch forever and every future run
            # (e.g. the weekly Sunday-night re-scrape) would find zero
            # pending/failed teams and exit doing nothing -- silently, with
            # no error, since nothing distinguishes "finished" from "nothing
            # left to do this run" without this UPDATE. Only touches the
            # 'status' column (the only one confirmed in use elsewhere in
            # this script) to avoid guessing at columns not seen in use.
            cursor.execute("UPDATE scraping_batches SET status = 'completed' WHERE batch_id = ?", batch_id)
            cursor.connection.commit()
            logger.info(f"Batch {batch_id} marked 'completed'. Next run will start a fresh batch "
                        f"covering every mapped team in dbo.URL_ProperName_Mapping.")

            # 2026-09-13: auto-finalize when the batch flips running ->
            # completed. 2026-09-19: FinalizeMaxPrepsData's Unmatched_Opponents
            # insert now has its own NOT EXISTS guard (RawGameID = games_raw.
            # raw_id), matching the guard HS_Scores/Future_Games already had --
            # so calling it here is just the final call of the batch, not a
            # special "only safe place to call it" case anymore. See the
            # matching finalize call after the per-team scrape loop below,
            # which now runs every night so games show up in HS_Scores the
            # same day they're scraped instead of waiting for the whole
            # multi-day batch to exhaust every mapped team.
            try:
                logger.info(f"Auto-finalizing batch {batch_id} via dbo.FinalizeMaxPrepsData...")
                cursor.execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = ?", batch_id)
                cursor.connection.commit()
                logger.info(f"Batch {batch_id} finalized successfully.")
            except Exception as e:
                logger.error(f"FinalizeMaxPrepsData failed for batch {batch_id}: {e}", exc_info=True)
                logger.error(f"Run this manually once fixed: EXEC dbo.FinalizeMaxPrepsData @BatchID = {batch_id};")
            return

        logger.info(f"Starting to process {len(urls_to_process)} URLs for batch_id {batch_id}")
        kill_orphaned_scraper_chrome()  # leftovers from a killed/crashed earlier run
        driver = setup_driver()
        try:
            for i, (team_id, candidates, proper_name) in enumerate(urls_to_process, 1):
                logger.info(f"[{i}/{len(urls_to_process)}] Processing Team ID {team_id} "
                            f"({len(candidates)} candidate URL(s))")

                games, used_url, last_error = [], None, None
                for c_i, url in enumerate(candidates, 1):
                    try:
                        driver.get(url)
                        handle_popups(driver)
                        games = scrape_schedule_data_robust(driver, batch_id, proper_name)
                        if games:
                            used_url = url
                            if c_i > 1:
                                logger.info(f"  Primary URL had no games; alias URL #{c_i - 1} succeeded: {url}")
                            break
                        else:
                            logger.info(f"  Candidate {c_i}/{len(candidates)} ({url}) returned no games.")
                    except Exception as e:
                        last_error = str(e).strip()[:1000]
                        logger.warning(f"  Candidate {c_i}/{len(candidates)} ({url}) failed: {last_error}")

                        # 2026-09-14 fix: a crashed/exited chromedriver process
                        # makes every subsequent driver.get() call fail
                        # identically (observed live: team 26 crashed the
                        # session, then teams 35/39/42/44/52/59... each spent
                        # ~35 seconds retrying/failing against the dead
                        # session before giving up -- left overnight this
                        # would burn the entire runtime cap failing every
                        # remaining team in the batch instead of recovering).
                        # rescrape_2019_ambiguous.py already had this exact
                        # recovery pattern; porting it here.
                        if ('WinError 10061' in last_error or 'Connection aborted' in last_error
                                or 'invalid session id' in last_error.lower()
                                or 'session not created' in last_error.lower()):
                            logger.warning("  Detected a dead browser session -- restarting the driver...")
                            try:
                                driver.quit()
                            except Exception:
                                pass
                            kill_orphaned_scraper_chrome()  # quit() can't reach a dead driver's Chrome
                            time.sleep(3)
                            driver = setup_driver()

                if games:
                    save_raw_games_to_db(cursor, games)
                    update_team_status(cursor, batch_id, team_id, 'completed', len(games))
                    logger.info(f"Saved {len(games)} raw games for Team ID {team_id} (used {used_url})")
                elif last_error is None:
                    # Every candidate URL loaded fine but had zero games listed.
                    update_team_status(cursor, batch_id, team_id, 'completed', 0)
                    logger.warning(f"No games found for Team ID {team_id} on any of "
                                   f"{len(candidates)} candidate URL(s), but marking as complete.")
                else:
                    update_team_status(cursor, batch_id, team_id, 'failed', error_message=last_error)
                    logger.error(f"Failed processing Team ID {team_id} on all "
                                 f"{len(candidates)} candidate URL(s): {last_error}")

                # 2026-09-21 fix: finalize periodically DURING the loop, not
                # only after it completes. Discovered live on batch 34's
                # first overnight run: the wrapper's 8-hour runtime cap
                # force-kills this process externally (Stop-Process -Force)
                # when a single chunk (URL_PROCESS_LIMIT=2000 teams at
                # ~18 sec/team is itself ~10 hours -- longer than the cap),
                # which means Python's own control flow never reaches the
                # post-loop finalize call added 2026-09-19. That run scraped
                # 33,391 raw games and finalized ZERO of them -- silently,
                # since the process was killed, not errored. Calling finalize
                # here too means a forced kill can only ever lose the last
                # <200 teams' worth of games, not a whole night's.
                if i % 200 == 0:
                    try:
                        logger.info(f"Periodic finalize (team {i}/{len(urls_to_process)}) for batch {batch_id}...")
                        cursor.execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = ?", batch_id)
                        cursor.connection.commit()
                    except Exception as e:
                        logger.error(f"Periodic finalize failed for batch {batch_id}: {e}", exc_info=True)

                if i < len(urls_to_process):
                    time.sleep(random.uniform(8, 15))
        finally:
            try:
                driver.quit()
            except Exception:
                pass
            kill_orphaned_scraper_chrome()

        # 2026-09-19: finalize after every night's chunk, not just once at
        # full batch completion. Batch 33 (started 2026-09-14) sat with ZERO
        # 2026 games visible in HS_Scores for 5+ days because finalize only
        # ran at the "no more teams" transition -- for a ~16k-team national
        # batch that can take well over a week, that's a multi-day blackout
        # every single weekly sweep. Safe to call every run now that
        # Unmatched_Opponents has its own dedup guard (see comment above);
        # HS_Scores/Future_Games were already idempotent.
        logger.info(f"Auto-finalizing batch {batch_id} via dbo.FinalizeMaxPrepsData "
                    f"(incremental -- this run's newly scraped games only need to show up)...")
        try:
            cursor.execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = ?", batch_id)
            cursor.connection.commit()
            logger.info(f"Batch {batch_id} finalized (incremental).")
        except Exception as e:
            logger.error(f"FinalizeMaxPrepsData failed for batch {batch_id}: {e}", exc_info=True)
            logger.error(f"Run this manually once fixed: EXEC dbo.FinalizeMaxPrepsData @BatchID = {batch_id};")
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
        release_lock()

if __name__ == "__main__":
    main()
