#!/usr/bin/env python3
"""
rescrape_2019_ambiguous.py

Re-scrapes the LIVE 2019 MaxPreps schedule for just the teams involved in
the "Ambiguous" rows from maxpreps_2019_date_truncation_fix.py -- games
where the 2019 date-truncation bug (see that script's docstring) left 2+
equally-plausible Friday/Thursday/Saturday candidates and couldn't be
auto-corrected from the stored data alone.

Built on your EXISTING, working scraping pipeline (maxpreps_scraper_db.py's
Selenium setup + the games_raw / scraping_batches / FinalizeMaxPrepsData
flow, already verified safe for date parsing -- see
maxpreps_2019_date_truncation_fix.py's docstring for why the CURRENT proc
doesn't have the 2019 bug) rather than a one-off scraper, so:
  - the real 2019 schedule goes through the exact same, already-trusted
    parsing code path as every other import
  - it's reusable for any other state's ambiguous 2019 rows, not just OK
  - it produces normal HS_Scores rows with a normal per-game Source URL
    (.../football/19-20/schedule/), auditable the same way as everything
    else in the table

WHAT THIS DOES NOT DO: it never touches HS_Scores or the existing
(corrupted) rows directly, and it never touches the general/current-season
scraping batches -- this creates its own narrowly-scoped batch containing
ONLY the affected teams. After this finishes, run in SSMS:
    EXEC dbo.FinalizeMaxPrepsData @BatchID = <printed batch_id>;
which inserts the freshly-scraped 2019 games as NEW HS_Scores rows (it
will NOT overwrite/delete the existing corrupted rows -- reconciliation
against those is a separate follow-up step). Then run
reconcile_2019_ambiguous.py to match each Ambiguous row's corrupted date
against the freshly-scraped real date and apply the fix with full audit
logging.

IMPORTANT -- TEST SMALL FIRST: FinalizeMaxPrepsData's opponent-matching
join strips the season_slug segment from the scraped opponent URL to
match it back to URL_ProperName_Mapping. Whether MaxPreps' opponent links
on a historical (/19-20/) schedule page actually carry that season
segment isn't something I could verify without running it -- if they
don't, opponent_url will come back NULL and those specific rows will be
silently excluded from the HS_Scores insert (not wrong, just dropped).
Use --limit 5 first, run FinalizeMaxPrepsData on that small batch, and
confirm the expected number of rows actually landed in HS_Scores before
running the full team list.

Usage:
  python rescrape_2019_ambiguous.py --input ok_2019_ambiguous.csv --limit 5   # small validation test first
  python rescrape_2019_ambiguous.py --input ok_2019_ambiguous.csv             # full run, once validated
"""

import argparse
import logging
import random
import time

import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text

from maxpreps_scraper_db import setup_driver, handle_popups, scrape_schedule_data_robust

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
DB_CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER_NAME};"
    f"DATABASE={DATABASE_NAME};"
    f"Trusted_Connection=yes;"
)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

SEASON_SLUG = '19-20'
SEASON_YEAR = 2019


def get_affected_teams(csv_path):
    df = pd.read_csv(csv_path)
    return sorted(pd.unique(pd.concat([df['Home'], df['Visitor']])))


def match_teams_to_urls(team_names):
    df = pd.read_sql(text("SELECT Team_ID, URL, ProperName FROM URL_ProperName_Mapping"), engine)
    lookup = dict(zip(df['ProperName'], zip(df['Team_ID'], df['URL'])))
    matched, unmatched = [], []
    for name in team_names:
        if name in lookup:
            team_id, url = lookup[name]
            matched.append((team_id, name, url))
        else:
            unmatched.append(name)
    return matched, unmatched


def build_2019_schedule_url(raw_url):
    """Same base-URL cleaning as maxpreps_scraper_db.get_urls_to_process(),
    but inserts the season_slug segment so we hit the historical 2019
    schedule page instead of the current one."""
    base_url = raw_url.strip().rstrip('/')
    while base_url.endswith('/football') or base_url.endswith('/schedule'):
        if base_url.endswith('/schedule'):
            base_url = base_url[:-len('/schedule')].rstrip('/')
        if base_url.endswith('/football'):
            base_url = base_url[:-len('/football')].rstrip('/')
    return f"{base_url}/football/{SEASON_SLUG}/schedule/"


def get_pending_teams(cursor, batch_id):
    """For --resume-batch-id: only the teams still 'pending' or 'failed'
    in an existing batch (mirrors maxpreps_scraper_db.py's resumable
    design) -- so a crash partway through doesn't mean re-scraping teams
    that already succeeded."""
    cursor.execute("""
        SELECT s.team_id, m.ProperName, m.URL
        FROM dbo.team_scraping_status s
        JOIN dbo.URL_ProperName_Mapping m ON s.team_id = m.Team_ID
        WHERE s.batch_id = ? AND s.status IN ('pending', 'failed')
        ORDER BY CASE WHEN s.status = 'failed' THEN 0 ELSE 1 END, s.team_id;
    """, batch_id)
    return [(row.team_id, row.ProperName, row.URL) for row in cursor.fetchall()]


def create_batch(cursor, matched):
    batch_name = f"2019 Date Truncation Reconciliation - {time.strftime('%Y-%m-%d %H:%M')}"
    insert_sql = ("INSERT INTO scraping_batches (batch_name, created_date, total_teams, status, season_slug, season_year) "
                  "OUTPUT INSERTED.batch_id VALUES (?, GETDATE(), ?, 'running', ?, ?);")
    batch_id = cursor.execute(insert_sql, batch_name, len(matched), SEASON_SLUG, SEASON_YEAR).fetchone()[0]
    status_entries = [(team_id, batch_id) for team_id, _, _ in matched]
    cursor.executemany("INSERT INTO dbo.team_scraping_status (team_id, batch_id) VALUES (?, ?);", status_entries)
    cursor.connection.commit()
    return batch_id


def save_raw_games(cursor, games_list, batch_id):
    if not games_list:
        return
    game_tuples = [
        (g['primary_team_name'], g['opponent_name_raw'], g['result_text'], g['game_date'],
         g['opponent_maxpreps_url'], batch_id, SEASON_YEAR)
        for g in games_list
    ]
    sql = """
        INSERT INTO dbo.games_raw
            (primary_team_name, opponent_name_raw, result_text, game_date, opponent_maxpreps_url, batch_id, season_year)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    cursor.executemany(sql, game_tuples)
    cursor.connection.commit()


def update_status(cursor, batch_id, team_id, status, games_found=0, error_message=None):
    cursor.execute("""
        UPDATE dbo.team_scraping_status
        SET status = ?, attempts = attempts + 1, last_attempt = GETDATE(), games_found = ?, error_message = ?
        WHERE team_id = ? AND batch_id = ?;
    """, status, games_found, error_message, team_id, batch_id)
    cursor.connection.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', required=True, help="CSV from maxpreps_2019_date_truncation_fix.py --output (the Ambiguous report)")
    parser.add_argument('--limit', type=int, default=None, help="Only scrape the first N matched teams (use for a small validation test before the full run)")
    parser.add_argument('--resume-batch-id', type=int, default=None,
                         help="Resume an existing batch instead of creating a new one -- only re-scrapes teams "
                              "still 'pending'/'failed' in that batch, so a crash partway through doesn't mean "
                              "re-scraping teams that already succeeded.")
    args = parser.parse_args()

    connection = pyodbc.connect(DB_CONNECTION_STRING)
    cursor = connection.cursor()

    if args.resume_batch_id:
        batch_id = args.resume_batch_id
        matched = get_pending_teams(cursor, batch_id)
        logger.info(f"Resuming batch_id {batch_id}: {len(matched)} team(s) still pending/failed.")
    else:
        team_names = get_affected_teams(args.input)
        logger.info(f"{len(team_names)} distinct team(s) found in {args.input}.")

        matched, unmatched = match_teams_to_urls(team_names)
        logger.info(f"{len(matched)} matched to a MaxPreps URL, {len(unmatched)} unmatched.")
        if unmatched:
            logger.warning("Unmatched (no URL_ProperName_Mapping row -- will need manual lookup): " + ", ".join(unmatched))

        if args.limit:
            matched = matched[:args.limit]
            logger.info(f"--limit {args.limit}: scraping only {len(matched)} team(s) this run.")

        batch_id = create_batch(cursor, matched)
        logger.info(f"Created scoped batch_id {batch_id} for {len(matched)} team(s), season_slug={SEASON_SLUG}.")

    if not matched:
        logger.info("Nothing left to scrape.")
        connection.close()
        return

    driver = setup_driver()
    try:
        i = 0
        while i < len(matched):
            team_id, proper_name, raw_url = matched[i]
            i += 1
            schedule_url = build_2019_schedule_url(raw_url)
            logger.info(f"[{i}/{len(matched)}] {proper_name} => {schedule_url}")
            try:
                driver.get(schedule_url)
                handle_popups(driver)
                games = scrape_schedule_data_robust(driver, batch_id, proper_name)
                if games:
                    save_raw_games(cursor, games, batch_id)
                    update_status(cursor, batch_id, team_id, 'completed', len(games))
                    logger.info(f"  Saved {len(games)} raw games.")
                else:
                    update_status(cursor, batch_id, team_id, 'completed', 0)
                    logger.warning("  No games found.")
            except Exception as e:
                error_msg = str(e).strip()[:1000]
                update_status(cursor, batch_id, team_id, 'failed', error_message=error_msg)
                logger.error(f"  Failed: {error_msg}")

                # A dead/crashed Chrome session makes every subsequent
                # driver call fail identically -- restart it once so the
                # rest of the batch isn't wasted spinning against a
                # session that no longer exists.
                if 'WinError 10061' in error_msg or 'Connection aborted' in error_msg or 'invalid session id' in error_msg.lower():
                    logger.warning("  Detected a dead browser session -- restarting the driver...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(3)
                    driver = setup_driver()
            if i < len(matched):
                time.sleep(random.uniform(8, 15))
    finally:
        driver.quit()
        connection.close()

    print("\n" + "=" * 60)
    print("  SCRAPE COMPLETE. Next steps:")
    print(f"  1. In SSMS: EXEC dbo.FinalizeMaxPrepsData @BatchID = {batch_id};")
    print(f"  2. Verify: SELECT COUNT(*) FROM HS_Scores WHERE Source LIKE '%/19-20/%' AND BatchID = {batch_id};")
    print(f"  3. Then run: python reconcile_2019_ambiguous.py --input {args.input} --batch-id {batch_id}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
