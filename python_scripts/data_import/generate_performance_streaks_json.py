"""
generate_performance_streaks_json.py
======================================
Generates: docs/data/performance-streaks/performance-streaks.json

Concept:
  Using the De La Salle 151-game streak as a benchmark, we calculate a
  "Game Performance" score for every team in every game:

    Game_Performance = AVG(both teams' Combined_Rating) + (Team_Margin / 2)

  Where:
    - Combined_Rating = 0.958 * Avg_Of_Avg_Of_Home_Modified_Score + 2.791
    - Team_Margin is positive for wins, negative for losses
    - Ratings are taken from HS_Rankings at Week 52 of each season
    - If a team has no Week 52 rating, 0 is used as a fallback

  The threshold is computed DYNAMICALLY each run as the minimum
  Game_Performance recorded during DLS's verified 151-game streak
  (1992-09-11 through 2004-09-04). This ensures the benchmark stays
  correct as rating calculations are updated over time.

  This script finds every team's longest consecutive streak of games
  where their Game_Performance stayed >= the DLS threshold.

  "Consecutive" means consecutive games played (ordered by Date),
  not consecutive calendar weeks. A single below-threshold game
  ends the streak.

Approach:
  Step 0 - Compute DLS benchmark threshold dynamically
  Step 1 - Build #Ratings temp table (Week 52 ratings for all teams/seasons)
  Step 2 - Score every game from both team perspectives (LEFT JOIN so
            unrated opponents don't break streaks)
  Step 3 - For each team, use gap-and-islands to find consecutive
            qualifying streaks (Game_Performance >= threshold)
  Step 4 - Rank streaks by length, minimum MIN_GAMES, output top TOP_N
"""

import json
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

import pyodbc

# -- Configuration -------------------------------------------------------------

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR  = os.path.join(REPO_ROOT, "docs", "data", "performance-streaks")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "performance-streaks.json")

DLS_STREAK      = 151     # verified game count of DLS win streak
MIN_GAMES       = 20      # minimum streak length to qualify
TOP_N           = 100     # number of streaks to output
THRESHOLD_FLOOR = 15.0    # safety floor if DLS query returns unexpectedly low value

# DLS streak date range (verified from Oakland Tribune Dec 7 2003 + 2004 game)
DLS_START_DATE  = '1992-09-11'
DLS_END_DATE    = '2004-09-04'

# -- SQL: Compute DLS benchmark threshold dynamically --------------------------

SQL_DLS_BENCHMARK = """
SELECT MIN(
    CAST(
        (ISNULL(rh.[Avg_Of_Avg_Of_Home_Modified_Score] * 0.958 + 2.791, 0) +
         ISNULL(rv.[Avg_Of_Avg_Of_Home_Modified_Score] * 0.958 + 2.791, 0)) / 2.0
        + CASE WHEN s.Home = 'Concord De La Salle (CA)'
               THEN  s.Margin / 2.0
               ELSE -s.Margin / 2.0
          END
    AS DECIMAL(10, 4))
) AS DLS_Min_Performance
FROM HS_Scores s
LEFT JOIN HS_Rankings rh
    ON  rh.Home   = s.Home
    AND rh.Season = s.Season
    AND rh.Week   = 52
LEFT JOIN HS_Rankings rv
    ON  rv.Home   = s.Visitor
    AND rv.Season = s.Season
    AND rv.Week   = 52
WHERE (s.Home = 'Concord De La Salle (CA)' OR s.Visitor = 'Concord De La Salle (CA)')
  AND s.Date BETWEEN '1992-09-11' AND '2004-09-04'
  AND (s.Future_Game IS NULL OR s.Future_Game = 0)
  AND (s.Forfeit     IS NULL OR s.Forfeit     = 0)
  AND s.Home_Score    IS NOT NULL
  AND s.Visitor_Score IS NOT NULL
"""

# -- SQL: Build ratings temp table ---------------------------------------------

SQL_BUILD_RATINGS = """
IF OBJECT_ID('tempdb..#Ratings') IS NOT NULL DROP TABLE #Ratings;

SELECT
    Home    AS TeamName,
    Season,
    (0.958 * [Avg_Of_Avg_Of_Home_Modified_Score] + 2.791) AS Combined_Rating
INTO #Ratings
FROM HS_Rankings
WHERE Week = 52
  AND [Avg_Of_Avg_Of_Home_Modified_Score] IS NOT NULL;
"""

# -- SQL: Score every game from both perspectives ------------------------------
# LEFT JOIN so games with unrated opponents are still included (rating = 0)

SQL_SCORE_GAMES = """
SELECT
    s.Home                                      AS Team,
    CASE WHEN s.Home < s.Visitor
         THEN s.Home + '|' + s.Visitor
         ELSE s.Visitor + '|' + s.Home
    END                                         AS GameKey,
    s.Date,
    s.Season,
    s.Visitor                                   AS Opponent,
    s.Margin                                    AS Team_Margin,
    ISNULL(rh.Combined_Rating, 0)               AS Team_Rating,
    ISNULL(rv.Combined_Rating, 0)               AS Opp_Rating,
    CAST(
        (ISNULL(rh.Combined_Rating, 0) + ISNULL(rv.Combined_Rating, 0)) / 2.0
        + s.Margin / 2.0
    AS DECIMAL(10, 4))                          AS Game_Performance
FROM HS_Scores s
LEFT JOIN #Ratings rh
    ON  rh.TeamName = s.Home
    AND rh.Season   = s.Season
LEFT JOIN #Ratings rv
    ON  rv.TeamName = s.Visitor
    AND rv.Season   = s.Season
WHERE (s.Future_Game IS NULL OR s.Future_Game = 0)
  AND (s.Forfeit     IS NULL OR s.Forfeit     = 0)
  AND s.Date          IS NOT NULL
  AND s.Home_Score    IS NOT NULL
  AND s.Visitor_Score IS NOT NULL

UNION ALL

SELECT
    s.Visitor                                   AS Team,
    CASE WHEN s.Home < s.Visitor
         THEN s.Home + '|' + s.Visitor
         ELSE s.Visitor + '|' + s.Home
    END                                         AS GameKey,
    s.Date,
    s.Season,
    s.Home                                      AS Opponent,
    -s.Margin                                   AS Team_Margin,
    ISNULL(rv.Combined_Rating, 0)               AS Team_Rating,
    ISNULL(rh.Combined_Rating, 0)               AS Opp_Rating,
    CAST(
        (ISNULL(rh.Combined_Rating, 0) + ISNULL(rv.Combined_Rating, 0)) / 2.0
        + (-s.Margin) / 2.0
    AS DECIMAL(10, 4))                          AS Game_Performance
FROM HS_Scores s
LEFT JOIN #Ratings rh
    ON  rh.TeamName = s.Home
    AND rh.Season   = s.Season
LEFT JOIN #Ratings rv
    ON  rv.TeamName = s.Visitor
    AND rv.Season   = s.Season
WHERE (s.Future_Game IS NULL OR s.Future_Game = 0)
  AND (s.Forfeit     IS NULL OR s.Forfeit     = 0)
  AND s.Date          IS NOT NULL
  AND s.Home_Score    IS NOT NULL
  AND s.Visitor_Score IS NOT NULL

ORDER BY Team, Date;
"""

# -- Helpers -------------------------------------------------------------------

def safe_float(val, default=0.0):
    # step 1 - safe float conversion
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def safe_str(val, default=""):
    # step 2 - safe string conversion
    return str(val).strip() if val is not None else default

def safe_date(val):
    # step 3 - safe date conversion
    if val is None:
        return None
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    return str(val)[:10]

# -- Gap-and-islands streak finder ---------------------------------------------

def find_streaks(team_games, threshold, min_games):
    """
    Given a list of game dicts for ONE team (sorted by Date ascending),
    find all consecutive streaks where Game_Performance >= threshold.
    Returns list of streak game-lists with length >= min_games.

    Gap-and-islands approach:
      - rn_all:  sequential counter over ALL games
      - rn_qual: sequential counter over QUALIFYING games only
      - Within a consecutive qualifying streak, (rn_all - rn_qual) is constant
      - Group by that constant to identify streak groups
    """
    # step 1 - initialize counters
    streaks   = []
    rn_all    = 0
    rn_qual   = 0
    tagged    = []

    for g in team_games:
        rn_all += 1
        if g['game_performance'] >= threshold:
            rn_qual += 1
            island = rn_all - rn_qual
            tagged.append((island, g))

    if not tagged:
        return []

    # step 2 - group by island key
    current_island = tagged[0][0]
    current_group  = [tagged[0][1]]

    for island, g in tagged[1:]:
        if island == current_island:
            current_group.append(g)
        else:
            if len(current_group) >= min_games:
                streaks.append(current_group)
            current_island = island
            current_group  = [g]

    if len(current_group) >= min_games:
        streaks.append(current_group)

    return streaks

# -- Main ----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Performance Streaks JSON Generator")
    print(f"Target: {OUTPUT_FILE}")
    print(f"Min games: {MIN_GAMES} | Top: {TOP_N}")
    print(f"Benchmark: De La Salle {DLS_STREAK}-game streak (threshold computed dynamically)")
    print("=" * 60)

    # -- Connect ---------------------------------------------------------------
    print("\nConnecting to SQL Server...")
    try:
        conn = pyodbc.connect(CONNECTION_STRING, timeout=30)
        cursor = conn.cursor()
        print("Connected.")
    except Exception as e:
        print(f"ERROR: Could not connect: {e}", file=sys.stderr)
        sys.exit(1)

    # -- Step 0: Compute DLS benchmark threshold -------------------------------
    print(f"\nStep 0: Computing DLS benchmark threshold ({DLS_START_DATE} to {DLS_END_DATE})...")
    try:
        cursor.execute(SQL_DLS_BENCHMARK)
        row = cursor.fetchone()
        print(f"  Raw query result: {row}")
        if row and row[0] is not None:
            threshold = float(row[0])
            if threshold < THRESHOLD_FLOOR:
                print(f"  WARNING: Computed threshold {threshold:.2f} below floor "
                      f"{THRESHOLD_FLOOR}. Using floor value.")
                threshold = THRESHOLD_FLOOR
        else:
            print(f"  WARNING: Could not compute DLS threshold. Using fallback 18.58.")
            threshold = 18.58
        print(f"  DLS minimum game performance: {threshold:.2f}")
    except Exception as e:
        print(f"  WARNING: DLS threshold query failed ({e}). Using fallback 18.58.")
        threshold = 18.58

    # -- Step 1: Build ratings temp table --------------------------------------
    print("\nStep 1: Building ratings temp table...")
    try:
        cursor.execute(SQL_BUILD_RATINGS)
        cursor.execute("SELECT COUNT(*) FROM #Ratings")
        rating_count = cursor.fetchone()[0]
        print(f"  {rating_count:,} team-season ratings loaded.")
    except Exception as e:
        print(f"ERROR: Could not build ratings table: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # -- Step 2: Score all games -----------------------------------------------
    print("\nStep 2: Scoring all games (may take several minutes)...")
    try:
        cursor.execute(SQL_SCORE_GAMES)
        rows = cursor.fetchall()
        cols = [c[0].lower() for c in cursor.description]
        print(f"  {len(rows):,} team-game records retrieved.")
    except Exception as e:
        print(f"ERROR: Could not score games: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    if not rows:
        print("WARNING: No game records returned.")
        sys.exit(0)

        # -- Step 3: Organize games by team ----------------------------------------
    print("\nStep 3: Organizing games by team...")

    team_games     = defaultdict(list)
    seen_game_keys = defaultdict(set)
    
    for row in rows:
        g        = dict(zip(cols, row))
        team     = safe_str(g['team'])
        
        # Add the date to make the key unique per actual game played
        game_date = safe_date(g['date'])
        game_key  = f"{game_date}|{safe_str(g['gamekey'])}|{team}"
        
        perf     = safe_float(g['game_performance'])

        if game_key in seen_game_keys[team]:
            continue
            
        seen_game_keys[team].add(game_key)
        
        team_games[team].append({
            'date':             game_date,
            'season':           int(g['season']) if g['season'] else 0,
            'opponent':         safe_str(g['opponent']),
            'team_margin':      int(g['team_margin']) if g['team_margin'] else 0,
            'team_rating':      safe_float(g['team_rating']),
            'opp_rating':       safe_float(g['opp_rating']),
            'game_performance': perf,
        })

    print(f"  {len(team_games):,} teams with games.")

    # Sort each team's games by date
    for team in team_games:
        team_games[team].sort(key=lambda x: x['date'])

    # Debug DLS specifically
    dls_team = 'Concord De La Salle (CA)'
    if dls_team in team_games:
        dls_games = team_games[dls_team]
        print(f"  DLS has {len(dls_games)} games total")
        dls_streak_games = [g for g in dls_games
                           if g['date'] >= '1992-09-11'
                           and g['date'] <= '2004-09-04']
        print(f"  DLS streak period games: {len(dls_streak_games)}")
        below = [g for g in dls_streak_games if g['game_performance'] < threshold]
        print(f"  DLS games below threshold during streak: {len(below)}")
        for g in below:
            print(f"    {g['date']} vs {g['opponent']} perf:{g['game_performance']:.4f}")

    # -- Step 4: Find streaks --------------------------------------------------
    print(f"\nStep 4: Finding streaks >= {MIN_GAMES} games above threshold {threshold:.2f}...")

    all_streaks     = []
    teams_processed = 0

    for team, games in team_games.items():
        streaks = find_streaks(games, threshold, min_games=MIN_GAMES)
        for streak_games in streaks:
            perfs = [g['game_performance'] for g in streak_games]
            all_streaks.append({
                'team':          team,
                'streak_length': len(streak_games),
                'date_start':    streak_games[0]['date'],
                'date_end':      streak_games[-1]['date'],
                'season_start':  streak_games[0]['season'],
                'season_end':    streak_games[-1]['season'],
                'min_perf':      round(min(perfs), 2),
                'avg_perf':      round(sum(perfs) / len(perfs), 2),
                'max_perf':      round(max(perfs), 2),
                'games':         streak_games,
            })
        teams_processed += 1
        if teams_processed % 5000 == 0:
            print(f"  Processed {teams_processed:,} teams...")

    print(f"  Found {len(all_streaks):,} qualifying streaks across all teams.")

    # Sort by streak length descending, avg_perf as tiebreaker
    all_streaks.sort(key=lambda x: (-x['streak_length'], -x['avg_perf']))
    top_streaks = all_streaks[:TOP_N]
    print(f"  Taking top {len(top_streaks)} by streak length.")

    # -- Step 5: Build output records ------------------------------------------
    print("\nStep 5: Building output records...")

    records = []
    for i, s in enumerate(top_streaks, 1):
        game_list = [{
            'date':             g['date'],
            'season':           g['season'],
            'opponent':         g['opponent'],
            'margin':           g['team_margin'],
            'game_performance': round(g['game_performance'], 2),
        } for g in s['games']]

        records.append({
            'rank':          i,
            'team':          s['team'],
            'streak_length': s['streak_length'],
            'date_start':    s['date_start'],
            'date_end':      s['date_end'],
            'season_start':  s['season_start'],
            'season_end':    s['season_end'],
            'min_perf':      s['min_perf'],
            'avg_perf':      s['avg_perf'],
            'max_perf':      s['max_perf'],
            'games':         game_list,
        })

    # -- Step 6: Write JSON ----------------------------------------------------
    print("\nStep 6: Writing JSON...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "metadata": {
            "timestamp":         datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":              "performance-streaks",
            "threshold":         round(threshold, 2),
            "dls_streak_length": DLS_STREAK,
            "min_games":         MIN_GAMES,
            "total_items":       len(records),
            "description": (
                f"Top {TOP_N} longest performance streaks in high school football history. "
                f"A streak is a consecutive sequence of games where the team's Game Performance "
                f"score stayed at or above {threshold:.2f} — the minimum recorded during "
                f"De La Salle (Concord CA)'s record {DLS_STREAK}-game winning streak (1992-2004). "
                f"Game Performance = Average of both teams Combined Rating + (Team Margin / 2). "
                f"Unrated opponents use a rating of 0. "
                f"Minimum {MIN_GAMES} qualifying games required."
            ),
        },
        "items": records,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUTPUT_FILE}")
    print(f"  Threshold used: {threshold:.2f}")
    if records:
        r = records[0]
        print(f"  #1: {r['team']}")
        print(f"      {r['streak_length']} games | {r['date_start']} to {r['date_end']}")
        print(f"      Min: {r['min_perf']} | Avg: {r['avg_perf']} | Max: {r['max_perf']}")
    print(f"\n  Total qualifying streaks found: {len(all_streaks):,}")
    print(f"  Output: top {len(records)}")
    print(f"\nNote: If DLS 151-game streak is not #1, rerun rating calc for 1992-2004")
    print("      then rerun this script.")
    print("\nDone.")


if __name__ == "__main__":
    main()