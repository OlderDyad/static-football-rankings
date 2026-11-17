"""
top100_tracker.py  (added 2026-11-14)
=====================================
Weekend "Top 100 tracker": scrapes the MaxPreps schedule pages of the current
national top 100 (Combined Rating), finalizes the new results into HS_Scores,
then builds a page showing how each team did against its rating expectation.

Generates: docs/data/top100-tracker/top100-tracker.json
Page:      docs/pages/public/top100-tracker/index.html (static, reads the JSON)

For each game of a top-100 team this season (betting-style, from the team's side):
    line   = -(Team CR - Opponent CR) / 0.958 -/+ 1.6 home field (0 if Neutral),
             rounded to the half point; negative = favored ("-7.5"), 0 = PK.
             Both CRs are from the latest rated week BEFORE the game's week
             (HS_Rankings, DATEPART(WEEK) like the pipeline). No line for games
             before this season's first weekly rating.
    pick   = R if the team the ratings favored won, U (upset) if not; no pick on PK.
    vs_line = actual margin minus the points the line expected (+ = beat it).
Next game (Future_Games, next 7 days) gets a line from the current ratings.
(2026-11-15 rework after David's review: spread instead of "expected",
 sorted by rank, one combined table, ATS record instead of avg deviation.)
Top 100 = latest rated week, 11-man programs only (same filter as Games of
the Week, generate_upcoming_games_json.py).

Scraping reuses maxpreps_scraper_db.py (driver, page parser, raw-game insert)
and its lock file, so it never runs at the same time as the nightly scraper or
weekly_pipeline.py (the pipeline waits while the lock is held). Its batches
are named "Top100 Tracker - <date>", which neither the scraper's resume logic
nor weekly_pipeline.py's BATCH_PREFIX matches.

Usage (python_scripts\\data_import):
    python top100_tracker.py                 # scrape + build + git push
    python top100_tracker.py --no-scrape     # build page from current data only
    python top100_tracker.py --no-push       # don't commit/push
    python top100_tracker.py --limit 5       # test: scrape only 5 teams
Scheduled by top100_watcher.ps1 (Saturday and Sunday mornings).
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone

import pyodbc

import maxpreps_scraper_db as mp

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(REPO_ROOT, "docs", "data", "top100-tracker")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "top100-tracker.json")
PAGE_DIR = os.path.join(REPO_ROOT, "docs", "pages", "public", "top100-tracker")
LOG_FILE = os.path.join(SCRIPT_DIR, "top100_tracker_log.txt")

TOP_N = 100
HOME_FIELD_PTS = 1.6          # measured 2004-2025, see generate_upcoming_games_json.py
COMBINED_PER_POINT = 0.958    # Combined_Rating = 0.958 x Margin rating + 2.791
BATCH_PREFIX = "Top100 Tracker - "
LOCK_WAIT_MINUTES = 45
RECENT_DAYS = 3               # "this weekend" = games in the last 3 days

CR_EXPR = "ISNULL(Combined_Rating, 0.958 * Avg_Of_Avg_Of_Home_Modified_Score + 2.791)"

SQL_LATEST = """
SELECT TOP 1 Season, Week FROM HS_Rankings
WHERE Season <= YEAR(GETDATE()) ORDER BY Season DESC, Week DESC
"""

SQL_TOP = f"""
;WITH cur AS (
    SELECT Home AS Team, {CR_EXPR} AS CR FROM HS_Rankings WHERE Season = ? AND Week = ?
), ok AS (
    SELECT c.Team, c.CR FROM cur c
    WHERE NOT EXISTS (SELECT 1 FROM HS_Team_Level_History lh
                      WHERE lh.TeamName = c.Team AND lh.PlayerLevel IN (6, 8, 9)
                        AND ? BETWEEN lh.Season_Begin AND lh.Season_End)
)
SELECT TOP ({TOP_N}) Team, CR, ROW_NUMBER() OVER (ORDER BY CR DESC) AS NatRank
FROM ok ORDER BY CR DESC
"""

SQL_URLS = """
SELECT m.Team_ID, m.ProperName, m.URL FROM dbo.URL_ProperName_Mapping m
JOIN dbo.HS_Team_Names t ON t.ID = m.Team_ID WHERE m.ProperName = ?
"""

SQL_GAMES = """
SELECT s.ID, CAST(s.[Date] AS date) AS GameDate, DATEPART(WEEK, s.[Date]) AS Wk,
       s.Home, s.Visitor, s.Home_Score, s.Visitor_Score, ISNULL(CAST(s.Neutral AS int), 0) AS Neutral
FROM HS_Scores s
WHERE s.Season = ? AND s.Home_Score IS NOT NULL AND s.Visitor_Score IS NOT NULL
  AND (s.Future_Game IS NULL OR s.Future_Game = 0)
  AND (s.Home IN (SELECT Team FROM #t100) OR s.Visitor IN (SELECT Team FROM #t100))
ORDER BY s.[Date]
"""

SQL_RATINGS = f"""
SELECT Home AS Team, Season, Week, {CR_EXPR} AS CR FROM HS_Rankings
WHERE Season = ? AND Season = ?
"""


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} - {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def connect():
    return pyodbc.connect(mp.DB_CONNECTION_STRING, timeout=30)


# --- scraping ----------------------------------------------------------------

def wait_for_lock():
    deadline = time.time() + LOCK_WAIT_MINUTES * 60
    while True:
        if mp.acquire_lock():
            return True
        if time.time() > deadline:
            return False
        log("Another scraper holds the lock; waiting 5 minutes...")
        time.sleep(300)


def scrape(cur, top, limit=None):
    teams = []
    for t in top[:limit] if limit else top:
        rows = cur.execute(SQL_URLS, t["team"]).fetchall()
        if not rows:
            log(f"  no MaxPreps URL mapped for {t['team']} - skipped")
            continue
        urls = []
        for r in rows:
            u = mp._clean_schedule_url(r.URL)
            if u not in urls:
                urls.append(u)
        teams.append((rows[0].Team_ID, t["team"], urls))
    if not teams:
        log("No teams to scrape.")
        return None

    name = f"{BATCH_PREFIX}{datetime.now():%Y-%m-%d %H:%M}"
    batch_id = cur.execute(
        "INSERT INTO scraping_batches (batch_name, created_date, total_teams, status) "
        "OUTPUT INSERTED.batch_id VALUES (?, GETDATE(), ?, 'running');", name, len(teams)).fetchone()[0]
    cur.executemany("INSERT INTO dbo.team_scraping_status (team_id, batch_id) VALUES (?, ?);",
                    [(tid, batch_id) for tid, _, _ in {t[0]: t for t in teams}.values()])
    cur.connection.commit()
    log(f"Batch {batch_id} '{name}': {len(teams)} teams.")

    mp.kill_orphaned_scraper_chrome()
    driver = mp.setup_driver()
    total = 0
    try:
        for i, (tid, proper, urls) in enumerate(teams, 1):
            games, err = [], None
            attempts, retried = list(urls), False
            while attempts:
                url = attempts.pop(0)
                try:
                    driver.get(url)
                    mp.handle_popups(driver)
                    games = mp.scrape_schedule_data_robust(driver, batch_id, proper)
                    if games:
                        break
                except Exception as e:
                    err = str(e).strip()[:500]
                    # same dead-browser signatures maxpreps_scraper_db.py restarts on,
                    # plus 10054 (connection reset): the 2026-11-14 test run hit it
                    low = err.lower()
                    if any(k in low for k in ("winerror 10061", "winerror 10054", "connection aborted",
                                              "connection reset", "invalid session id",
                                              "session not created", "max retries exceeded")):
                        log(f"  dead browser session ({err[:60]}...) -- restarting the driver")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        mp.kill_orphaned_scraper_chrome()
                        time.sleep(3)
                        driver = mp.setup_driver()
                        if not retried:          # one more try on a fresh browser
                            retried = True
                            attempts.insert(0, url)
            if games:
                mp.save_raw_games_to_db(cur, games)
                mp.update_team_status(cur, batch_id, tid, "completed", len(games))
                total += len(games)
            elif err is None:
                mp.update_team_status(cur, batch_id, tid, "completed", 0)
            else:
                mp.update_team_status(cur, batch_id, tid, "failed", error_message=err)
                log(f"  [{i}] {proper}: failed ({err[:120]})")
            if i < len(teams):
                time.sleep(random.uniform(4, 8))
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        mp.kill_orphaned_scraper_chrome()

    log(f"Scraped {total} raw schedule rows; finalizing batch {batch_id}...")
    cur.execute("EXEC dbo.FinalizeMaxPrepsData @BatchID = ?", batch_id)
    cur.connection.commit()
    cur.execute("UPDATE scraping_batches SET status = 'completed' WHERE batch_id = ?", batch_id)
    cur.connection.commit()
    log(f"Batch {batch_id} finalized and completed.")
    return batch_id


# --- expectation vs result ------------------------------------------------------

def spread_of(exp):
    """Betting-style line for the team: negative = favored. Half-point steps."""
    if exp is None:
        return None
    return -round(exp * 2) / 2


def ats(actual, exp):
    """Against the spread, from the team's side: (W/L/P, points beyond the line)."""
    if exp is None:
        return None, None
    line = -spread_of(exp)                  # points the team was expected to win by
    d = actual - line
    return ("W" if d > 0 else "L" if d < 0 else "P"), round(d, 1)


SQL_NEXT = """
SELECT f.GameID, CAST(f.GameDate AS date) AS GameDate, f.RawHomeTeam AS Home, f.RawAwayTeam AS Visitor
FROM Future_Games f
WHERE CAST(f.GameDate AS date) BETWEEN CAST(GETDATE() AS date) AND DATEADD(day, 7, CAST(GETDATE() AS date))
  AND (f.RawHomeTeam IN (SELECT Team FROM #t100) OR f.RawAwayTeam IN (SELECT Team FROM #t100))
  AND NOT EXISTS (SELECT 1 FROM HS_Scores s WHERE s.Access_ID = f.GameID)
ORDER BY f.GameDate
"""


def build(cur, season, week, top):
    cur.execute("IF OBJECT_ID('tempdb..#t100') IS NOT NULL DROP TABLE #t100; "
                "CREATE TABLE #t100 (Team varchar(150) PRIMARY KEY);")
    cur.executemany("INSERT INTO #t100 VALUES (?)", [(t["team"],) for t in top])
    games = cur.execute(SQL_GAMES, season).fetchall()
    upcoming = cur.execute(SQL_NEXT).fetchall()

    ratings, current = {}, {}
    for r in cur.execute(SQL_RATINGS, season, season).fetchall():
        if r.Season == season:
            ratings.setdefault(r.Team, []).append((int(r.Week), float(r.CR)))
            if int(r.Week) == int(week):
                current[r.Team] = float(r.CR)
    for v in ratings.values():
        v.sort()

    def pre(team, wk):
        """Rating from the latest rated week before the game's week (no fallback:
        before this season's first weekly rating there is no line)."""
        best = None
        for w, cr in ratings.get(team, []):
            if w < wk:
                best = (cr, w)
            else:
                break
        return best or (None, None)

    info = {t["team"]: t for t in top}
    per_team = {t["team"]: [] for t in top}
    for g in games:
        for side in ("home", "visitor"):
            team = g.Home if side == "home" else g.Visitor
            if team not in info:
                continue
            opp = g.Visitor if side == "home" else g.Home
            pf, pa = (g.Home_Score, g.Visitor_Score) if side == "home" else (g.Visitor_Score, g.Home_Score)
            tcr, tw = pre(team, g.Wk)
            ocr, ow = pre(opp, g.Wk)
            hfa = 0.0 if g.Neutral else (HOME_FIELD_PTS if side == "home" else -HOME_FIELD_PTS)
            exp = (tcr - ocr) / COMBINED_PER_POINT + hfa if tcr is not None and ocr is not None else None
            act = int(pf - pa)
            res, beyond = ats(act, exp)
            sp = spread_of(exp)
            # straight-up pick: did the team the ratings favored win? (PK = no pick)
            pick = None if sp in (None, 0) else ("R" if (sp < 0) == (act > 0) and act != 0 else "U")
            per_team[team].append({
                "date": g.GameDate.isoformat(), "opponent": opp,
                "opponent_rank": info[opp]["rank"] if opp in info else None,
                "site": "N" if g.Neutral else ("H" if side == "home" else "A"),
                "points_for": int(pf), "points_against": int(pa),
                "result": "W" if act > 0 else ("L" if act < 0 else "T"),
                "spread": spread_of(exp), "line_week": tw if exp is not None else None,
                "pick": pick, "vs_line": beyond,
            })

    nxt = {}
    for f in upcoming:
        for side in ("home", "visitor"):
            team = f.Home if side == "home" else f.Visitor
            if team not in info or team in nxt:
                continue
            opp = f.Visitor if side == "home" else f.Home
            tcr, ocr = current.get(team), current.get(opp)
            exp = (tcr - ocr) / COMBINED_PER_POINT + (HOME_FIELD_PTS if side == "home" else -HOME_FIELD_PTS) \
                if tcr is not None and ocr is not None else None
            nxt[team] = {"date": f.GameDate.isoformat(), "opponent": opp,
                         "opponent_rank": info[opp]["rank"] if opp in info else None,
                         "site": "H" if side == "home" else "A", "spread": spread_of(exp),
                         "line_week": int(week) if exp is not None else None}

    teams_out = []
    for t in top:
        gl = per_team[t["team"]]
        rec = {k: sum(1 for x in gl if x["result"] == k) for k in "WLT"}
        pk = {k: sum(1 for x in gl if x["pick"] == k) for k in "RU"}
        teams_out.append({
            "rank": t["rank"], "team": t["team"], "rating": round(t["cr"], 2),
            "record": f"{rec['W']}-{rec['L']}" + (f"-{rec['T']}" if rec["T"] else ""),
            "picks": f"{pk['R']}-{pk['U']}",
            "last_game": gl[-1] if gl else None,
            "next_game": nxt.get(t["team"]),
            "game_log": gl,
        })

    # how often the ratings picked the winner (each game once, even if both teams are top 100)
    seen, wk_cut = {}, (date.today() - timedelta(days=7)).isoformat()
    for t in teams_out:
        for g in t["game_log"]:
            if g["pick"]:
                seen[(g["date"],) + tuple(sorted((t["team"], g["opponent"])))] = (g["pick"], g["date"] >= wk_cut)
    def rate(vals):
        n = len(vals); r = sum(1 for p in vals if p == "R")
        return {"right": r, "games": n, "pct": round(100.0 * r / n, 1) if n else None}
    pick_season = rate([p for p, _ in seen.values()])
    pick_week = rate([p for p, w in seen.values() if w])

    return {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "picks_last_7_days": pick_week, "picks_season": pick_season,
            "type": "top100-tracker", "season": int(season), "ratings_week": int(week),
            "home_field_adv": HOME_FIELD_PTS, "points_per_rating": COMBINED_PER_POINT,
            "total_teams": len(teams_out),
            "description": "The national top 100 by Combined Rating: last game, the line our "
                           "ratings set for it, and how the team did against it.",
        },
        "teams": teams_out,
    }


# --- publish -----------------------------------------------------------------------

def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def publish():
    paths = ["docs/data/top100-tracker", "docs/pages/public/top100-tracker"]
    git("add", *paths)
    rc, out = git("diff", "--cached", "--quiet", "--", *paths)
    if rc == 0:
        log("Nothing changed on the page; no commit.")
        return
    rc, out = git("commit", "-m", f"Top 100 tracker update {datetime.now():%Y-%m-%d %H:%M}", "--", *paths)
    log(f"git commit: {out.splitlines()[0] if out else rc}")
    rc, out = git("push", "origin", "main")
    if rc != 0:
        log(f"git push failed ({rc}): {out[-300:]}  -- run 'git pull --rebase' then 'git push' by hand.")
    else:
        log("Pushed to GitHub.")


def main():
    ap = argparse.ArgumentParser(description="Top 100 weekend tracker")
    ap.add_argument("--no-scrape", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--limit", type=int, help="scrape only the first N teams (testing)")
    a = ap.parse_args()

    log("=== Top 100 tracker started ===")
    cn = connect(); cur = cn.cursor()
    season, week = cur.execute(SQL_LATEST).fetchone()
    top = [{"team": r.Team, "cr": float(r.CR), "rank": int(r.NatRank)}
           for r in cur.execute(SQL_TOP, season, week, season).fetchall()]
    log(f"Ratings: season {season}, week {week}; top {len(top)} teams (#1 {top[0]['team'] if top else '-'}).")

    if not a.no_scrape:
        if wait_for_lock():
            try:
                scrape(cur, top, a.limit)
            except Exception as e:
                log(f"Scrape failed: {e} -- building the page from the data already in HS_Scores.")
            finally:
                mp.release_lock()
        else:
            log(f"Lock still held after {LOCK_WAIT_MINUTES} min; building from existing data without scraping.")

    data = build(cur, season, week, top)
    cn.close()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Written {OUTPUT_FILE}: {len(data['teams'])} teams, "
        f"{sum(1 for t in data['teams'] if t['next_game'])} with a game in the next 7 days.")

    if not a.no_push:
        publish()
    log("=== Done ===")


if __name__ == "__main__":
    main()
