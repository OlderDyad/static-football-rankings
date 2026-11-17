"""
weekly_pipeline.py
==================
Weekly in-season automation: scrape -> finalize -> ratings -> sanity checks
-> (optionally) publish.

Replaces maxpreps_watcher.ps1 (nightly 9PM, 8-hour-capped scraper runs).
Decided 2026-09-25: a full batch is ~14,500 teams at ~18 sec/team (~73 hours
of scraping), which the 8-hour nightly cap stretched to ~9 nights -- longer
than a week, so the cycle kept falling behind. Instead, this starts a fresh
batch every Sunday morning and runs the scraper back-to-back until the batch
is done (~3 days), then calculates that week's ratings, sanity-checks them,
and publishes (or stops for review -- see AUTO_PUBLISH).

Like maxpreps_watcher.ps1, this runs as an ordinary process in your logged-in
session, NOT through Task Scheduler (Task Scheduler's session can't launch
Chrome for Selenium -- see the maxpreps_watcher.ps1 header for that history).

MODES
  python weekly_pipeline.py --loop
      Run forever: wait for Sunday START_HOUR, run the pipeline, repeat.
      This is what the Startup-folder shortcut launches.
  python weekly_pipeline.py --now
      Run the pipeline once, immediately (resumes a running batch if there is
      one), then exit.
  python weekly_pipeline.py --now --loop
      Run once now, then keep going on the weekly schedule.
  python weekly_pipeline.py --skip-scrape --now
      Skip scraping; just ratings + checks (+ publish if enabled) for the
      most recent completed Saturday's week.
  Add --publish to publish even when AUTO_PUBLISH is False. Add --season/
  --week to override the computed values. NOTE: the week is computed from
  the day you run it, so a --skip-scrape re-run on a later day needs --week
  to target the same week. To publish a READY_TO_PUBLISH result after
  reviewing it, the simplest route is just running
  scripts\run_update_cycle.ps1 yourself, as before.

WHAT IT DOES EACH WEEK
  1. Scrape: runs maxpreps_scraper_db.py repeatedly (each run is up to 2,000
     teams, ~10 hours) until the batch is marked 'completed'. Safety valves:
       - PER_RUN_CAP_HOURS kills a single hung run (the next run resumes).
       - If 2 runs in a row make no progress: a small leftover tail
         (<= STUCK_TAIL_FRACTION of the batch) is accepted -- the batch is
         closed and finalized; anything bigger stops the pipeline as FAILED.
       - MAX_SCRAPE_DAYS stops a runaway week.
  2. Finalize: EXEC FinalizeMaxPrepsData for the batch (safe to repeat --
     its inserts are NOT EXISTS-guarded).
  3. Ratings: run_full_rankings_recalc.py for the season at the target week
     (the week of the most recent Saturday before the batch started, computed
     with the same DATEPART(WEEK, ...) that dbo.ScoresWinLoss uses).
  4. Checks (fail closed -- nothing is published if any fail):
       - no HS_Rankings rows for this season at a week LATER than the target
         (a stale test run like the 2026 Week=52 run would otherwise win the
         MAX(Week) the site uses)
       - one row per team (no duplicates)
       - top margin rating <= MAX_MARGIN (historical ceiling is ~189)
       - team count >= MIN_TEAM_RATIO x the prior week's count
       - Combined_Rating populated for every row
  5. Publish: scripts\\run_update_cycle.ps1 -NoPause, only if AUTO_PUBLISH or
     --publish. Otherwise the status file says READY_TO_PUBLISH.

WHERE TO LOOK
  weekly_pipeline_status.txt  -- one-glance current state (overwritten)
  weekly_pipeline_log.txt     -- full running log (appended)
"""

import argparse
import datetime as dt
import os
import subprocess
import sys
import time
import traceback

import pyodbc

# --- CONFIGURATION ---------------------------------------------------------
SCRIPT_DIR = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"
REPO_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
SCRAPER = os.path.join(SCRIPT_DIR, "maxpreps_scraper_db.py")
RECALC = os.path.join(REPO_ROOT, "python_scripts", "run_full_rankings_recalc.py")
UPDATE_CYCLE = os.path.join(REPO_ROOT, "scripts", "run_update_cycle.ps1")
CONN_STR = (r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;"
            r"DATABASE=hs_football_database;Trusted_Connection=yes;")

START_WEEKDAY = 6            # Monday=0 ... Sunday=6
START_HOUR = 6               # 6 AM Sunday
PER_RUN_CAP_HOURS = 12       # one scraper run is ~10h (2,000 teams x ~18s)
MAX_SCRAPE_DAYS = 5          # give up on the week after this
STUCK_TAIL_FRACTION = 0.02   # accept up to 2% of the batch never finishing
MAX_MARGIN = 200.0           # all-time best margin rating is ~189
MIN_TEAM_RATIO = 0.90        # vs prior week's team count for the season
AUTO_PUBLISH = False         # start False; flip to True once you trust it

LOG_FILE = os.path.join(SCRIPT_DIR, "weekly_pipeline_log.txt")
STATUS_FILE = os.path.join(SCRIPT_DIR, "weekly_pipeline_status.txt")
BATCH_PREFIX = "MaxPreps Scrape - %"
# ---------------------------------------------------------------------------


class PipelineError(Exception):
    pass


def log(msg):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} - {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_status(state, **details):
    lines = [f"Last updated: {dt.datetime.now():%Y-%m-%d %H:%M:%S}",
             f"State: {state}"]
    lines += [f"{k}: {v}" for k, v in details.items()]
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"STATUS -> {state}" + (f" ({details})" if details else ""))


def db():
    return pyodbc.connect(CONN_STR, autocommit=True)


def query_one(sql, *params):
    with db() as conn:
        return conn.cursor().execute(sql, *params).fetchone()


def query_all(sql, *params):
    with db() as conn:
        return conn.cursor().execute(sql, *params).fetchall()


def execute(sql, *params):
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql, *params)
        while cur.nextset():
            pass


# --- season / week ---------------------------------------------------------

def target_saturday(start):
    """Most recent Saturday strictly before the start date: the last full
    weekend of games a batch started at `start` can capture."""
    d = start.date() - dt.timedelta(days=1)
    while d.weekday() != 5:
        d -= dt.timedelta(days=1)
    return d


def season_for(sat):
    """Aug-Dec -> that year; January (late playoffs) -> previous year;
    Feb-Jul -> None (off-season, skip)."""
    if sat.month >= 8:
        return sat.year
    if sat.month == 1:
        return sat.year - 1
    return None


def week_for(sat):
    """Same DATEPART(WEEK, ...) dbo.ScoresWinLoss filters on, so the cutoff
    matches exactly. January games belong to the prior season -> 52."""
    if sat.month == 1:
        return 52
    wk = query_one("SELECT DATEPART(WEEK, CAST(? AS date))", sat.isoformat())[0]
    return min(int(wk), 52)


# --- scraping --------------------------------------------------------------

def latest_batch():
    return query_one(
        "SELECT TOP 1 batch_id, status, total_teams FROM dbo.scraping_batches "
        "WHERE batch_name LIKE ? ORDER BY batch_id DESC", BATCH_PREFIX)


def batch_row(batch_id):
    return query_one(
        "SELECT batch_id, status, total_teams FROM dbo.scraping_batches WHERE batch_id = ?",
        batch_id)


def remaining_teams(batch_id):
    return query_one(
        "SELECT COUNT(DISTINCT S.team_id) FROM dbo.team_scraping_status AS S "
        "JOIN dbo.URL_ProperName_Mapping AS M ON S.team_id = M.Team_ID "
        "WHERE S.batch_id = ? AND S.status IN ('pending', 'failed')", batch_id)[0]


def kill_tree(pid):
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                   capture_output=True, text=True)
    # chromedriver orphans only -- never touches your own Chrome windows
    subprocess.run(["taskkill", "/IM", "chromedriver.exe", "/F"],
                   capture_output=True, text=True)


def scraper_lock_holder():
    """PID of a scraper that's already running (per its lock file), else None."""
    lock = os.path.join(SCRIPT_DIR, "maxpreps_scraper.lock")
    if not os.path.exists(lock):
        return None
    try:
        with open(lock) as f:
            pid = int(f.read().strip())
    except Exception:
        return None
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                         capture_output=True, text=True).stdout
    return pid if str(pid) in out else None


def run_scraper_once():
    # A manual run (or anything else) already scraping: wait for it instead
    # of launching a copy that would refuse to start and look like "no
    # progress".
    while (pid := scraper_lock_holder()) is not None:
        write_status("WAITING_FOR_OTHER_SCRAPER", PID=pid)
        time.sleep(600)
    log("Launching maxpreps_scraper_db.py")
    proc = subprocess.Popen([sys.executable, SCRAPER], cwd=SCRIPT_DIR)
    try:
        proc.wait(timeout=PER_RUN_CAP_HOURS * 3600)
        log(f"Scraper run exited with code {proc.returncode}")
    except subprocess.TimeoutExpired:
        log(f"Scraper run exceeded {PER_RUN_CAP_HOURS}h -- stopping it (next run resumes).")
        kill_tree(proc.pid)


def scrape_phase(season, week):
    start = time.time()
    pre = latest_batch()
    tracked = pre.batch_id if pre and pre.status == "running" else None
    if tracked:
        log(f"Batch {tracked} is still running -- resuming it rather than starting a new one.")
    prev_remaining, no_progress = None, 0

    while True:
        write_status("SCRAPING", Season=season, Week=week, Batch=tracked or "(new)")
        run_scraper_once()

        if tracked is None:
            b = latest_batch()
            if not b or (pre and b.batch_id == pre.batch_id):
                no_progress += 1
                log("Scraper did not create a new batch this run.")
                if no_progress >= 2:
                    raise PipelineError("Scraper failed to create a new batch twice in a row "
                                        "-- check maxpreps_scraper_log.txt.")
                time.sleep(60)
                continue
            tracked = b.batch_id
            log(f"New batch {tracked} created with {b.total_teams} teams.")

        b = batch_row(tracked)
        if b.status == "completed":
            log(f"Batch {tracked} is completed.")
            break

        remaining = remaining_teams(tracked)
        log(f"Batch {tracked}: {remaining} scrapable teams left of {b.total_teams}.")
        if prev_remaining is not None and remaining >= prev_remaining:
            no_progress += 1
        else:
            no_progress = 0
        prev_remaining = remaining

        if no_progress >= 2:
            if remaining <= STUCK_TAIL_FRACTION * b.total_teams:
                log(f"No progress for 2 runs; accepting stuck tail of {remaining} teams "
                    f"and closing batch {tracked}.")
                execute("UPDATE dbo.scraping_batches SET status = 'completed' WHERE batch_id = ?",
                        tracked)
                break
            raise PipelineError(f"No scraping progress for 2 runs with {remaining} teams left "
                                f"in batch {tracked} -- check maxpreps_scraper_log.txt.")

        if time.time() - start > MAX_SCRAPE_DAYS * 86400:
            raise PipelineError(f"Scraping exceeded {MAX_SCRAPE_DAYS} days; batch {tracked} "
                                f"still has {remaining} teams left.")
        time.sleep(60)

    log(f"Running FinalizeMaxPrepsData for batch {tracked} (safe to repeat).")
    execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = ?", tracked)
    return tracked


# --- ratings + checks ------------------------------------------------------

def ratings_phase(season, week):
    later = query_all("SELECT DISTINCT Week FROM dbo.HS_Rankings WHERE Season = ? AND Week > ?",
                      season, week)
    if later:
        weeks = ", ".join(str(r.Week) for r in later)
        raise PipelineError(
            f"HS_Rankings already has {season} rows for later week(s) {weeks}. The site shows "
            f"the highest week, so this week's ratings would be hidden. If those are stale test "
            f"runs, delete them (DELETE FROM HS_Rankings WHERE Season = {season} AND Week > "
            f"{week};) and re-run with --skip-scrape --now.")

    write_status("CALCULATING_RATINGS", Season=season, Week=week)
    log(f"Running ratings for {season}, Week {week}")
    result = subprocess.run([sys.executable, RECALC, "--begin", str(season), "--end",
                             str(season), "--week", str(week), "--yes"],
                            cwd=os.path.dirname(RECALC), capture_output=True, text=True)
    for line in (result.stdout + result.stderr).splitlines():
        log(f"  [recalc] {line}")
    if result.returncode != 0:
        raise PipelineError(f"run_full_rankings_recalc.py exited with code {result.returncode}.")


def checks_phase(season, week):
    problems = []
    row = query_one(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT Home) AS teams, "
        "MAX(Avg_Of_Avg_Of_Home_Modified_Score) AS top_margin, "
        "SUM(CASE WHEN Combined_Rating IS NULL THEN 1 ELSE 0 END) AS null_combined "
        "FROM dbo.HS_Rankings WHERE Season = ? AND Week = ?", season, week)
    if not row.n:
        raise PipelineError(f"No HS_Rankings rows written for {season} Week {week}.")
    if row.n != row.teams:
        problems.append(f"duplicate rows: {row.n} rows for {row.teams} teams")
    if row.top_margin is not None and row.top_margin > MAX_MARGIN:
        problems.append(f"top margin rating {row.top_margin:.1f} exceeds {MAX_MARGIN}")
    if row.null_combined:
        problems.append(f"{row.null_combined} rows missing Combined_Rating")

    prior = query_one(
        "SELECT TOP 1 Week, COUNT(DISTINCT Home) AS teams FROM dbo.HS_Rankings "
        "WHERE Season = ? AND Week < ? GROUP BY Week ORDER BY Week DESC", season, week)
    if prior and row.teams < MIN_TEAM_RATIO * prior.teams:
        problems.append(f"team count dropped: {row.teams} vs {prior.teams} in Week {prior.Week}")

    top = f"{row.top_margin:.1f}" if row.top_margin is not None else "n/a"
    summary = (f"{row.teams} teams, top margin {top}"
               + (f", prior week {prior.Week}: {prior.teams} teams" if prior else ""))
    log(f"Checks for {season} Week {week}: {summary}")
    if problems:
        raise PipelineError("Sanity checks failed -- not publishing: " + "; ".join(problems))
    return summary


def publish_phase():
    write_status("PUBLISHING")
    log("Running run_update_cycle.ps1 -NoPause")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                             "-File", UPDATE_CYCLE, "-NoPause"],
                            cwd=os.path.dirname(UPDATE_CYCLE), capture_output=True, text=True)
    for line in (result.stdout + result.stderr).splitlines():
        log(f"  [publish] {line}")
    if result.returncode != 0:
        raise PipelineError(f"run_update_cycle.ps1 exited with code {result.returncode}.")


# --- orchestration ---------------------------------------------------------

def run_pipeline(start, args):
    sat = target_saturday(start)
    season = args.season or season_for(sat)
    if season is None:
        log(f"{sat} is off-season -- nothing to do this week.")
        write_status("IDLE_OFFSEASON", Saturday=sat)
        return
    week = args.week or week_for(sat)
    log(f"=== Pipeline start: season {season}, week {week} (games through {sat}) ===")

    try:
        batch = None
        if not args.skip_scrape:
            batch = scrape_phase(season, week)
        ratings_phase(season, week)
        summary = checks_phase(season, week)
        if AUTO_PUBLISH or args.publish:
            publish_phase()
            write_status("PUBLISHED", Season=season, Week=week, Batch=batch, Checks=summary)
        else:
            write_status("READY_TO_PUBLISH", Season=season, Week=week, Batch=batch,
                         Checks=summary,
                         Next="Review the ratings, then publish by running "
                              "scripts\\run_update_cycle.ps1 yourself")
    except PipelineError as exc:
        write_status("FAILED", Season=season, Week=week, Reason=str(exc))
    except Exception:
        write_status("FAILED", Season=season, Week=week,
                     Reason="unexpected error -- see weekly_pipeline_log.txt")
        log(traceback.format_exc())


def next_start_after(t):
    d = t + dt.timedelta(days=(START_WEEKDAY - t.weekday()) % 7)
    candidate = d.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
    if candidate <= t:
        candidate += dt.timedelta(days=7)
    return candidate


def sleep_until(target):
    log(f"Next pipeline run: {target:%Y-%m-%d %H:%M}")
    write_status("WAITING", NextRun=f"{target:%Y-%m-%d %H:%M}")
    while True:
        remaining = (target - dt.datetime.now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 3600))


def main():
    p = argparse.ArgumentParser(description="Weekly scrape -> ratings -> publish pipeline.")
    p.add_argument("--loop", action="store_true", help="run forever on the weekly schedule")
    p.add_argument("--now", action="store_true", help="run once immediately")
    p.add_argument("--skip-scrape", action="store_true", help="ratings/checks/publish only")
    p.add_argument("--publish", action="store_true", help="publish even if AUTO_PUBLISH is False")
    p.add_argument("--season", type=int, help="override computed season")
    p.add_argument("--week", type=int, help="override computed week")
    args = p.parse_args()
    if not (args.loop or args.now):
        p.error("use --now, --loop, or both")

    log(f"=== weekly_pipeline.py started (PID {os.getpid()}) "
        f"loop={args.loop} now={args.now} skip_scrape={args.skip_scrape} ===")

    last_start = None
    if args.now:
        last_start = dt.datetime.now()
        run_pipeline(last_start, args)
    if not args.loop:
        return

    # Scheduled runs never reuse one-off overrides
    args.skip_scrape = args.publish = False
    args.season = args.week = None
    while True:
        target = next_start_after(last_start or dt.datetime.now())
        # If a long week ran past its Sunday start, go immediately instead of
        # losing a whole week.
        if target > dt.datetime.now():
            sleep_until(target)
        last_start = dt.datetime.now()
        run_pipeline(last_start, args)


if __name__ == "__main__":
    main()
