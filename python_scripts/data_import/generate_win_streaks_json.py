"""
generate_win_streaks_json.py
======================================
Generates: docs/data/win-streaks/win-streaks.json

Concept:
  Finds the longest consecutive winning streaks in high school football
  history based on data in HS_Scores. A streak is a sequence of wins
  with no losses or ties in between. Any loss OR tie ends the streak.

  The all-time record is De La Salle (Concord, CA) with 151 consecutive
  wins from 1992-2004. Historical records from before 1960 may be
  incomplete — Sims (Union County, SC) had a 96-game unbeaten streak
  (1945-1954) and Bedford County Training School (Shelbyville, TN) went
  82 games without a loss (1943-1950), but these programs are likely
  not fully represented in our database.

Approach:
  Step 1 — Pull all games from HS_Scores ordered by team and date
  Step 2 — For each team, find consecutive winning streaks (margin > 0)
            Any game with margin <= 0 (loss or tie) breaks the streak
  Step 3 — Rank by streak length, minimum MIN_GAMES, output top TOP_N

Output JSON schema:
  {
    "metadata": {
      "timestamp", "description", "min_games", "total_items"
    },
    "items": [
      {
        "rank":          int,
        "team":          str,
        "streak_length": int,
        "date_start":    str,   # YYYY-MM-DD
        "date_end":      str,   # YYYY-MM-DD
        "season_start":  int,
        "season_end":    int,
        "avg_margin":    float,
        "max_margin":    int,
        "games":         list   # [{date, season, opponent, margin}]
      }
    ]
  }
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
OUTPUT_DIR  = os.path.join(REPO_ROOT, "docs", "data", "win-streaks")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "win-streaks.json")

MIN_GAMES = 20    # minimum streak length to qualify
TOP_N     = 100   # number of streaks to output

# -- SQL: Pull all games from both team perspectives ---------------------------
# Returns one row per team per game with margin from that team's perspective

SQL_GET_GAMES = """
SELECT
    s.Home                          AS Team,
    CASE WHEN s.Home < s.Visitor
         THEN s.Home + '|' + s.Visitor
         ELSE s.Visitor + '|' + s.Home
    END                             AS GameKey,
    s.Date,
    s.Season,
    s.Visitor                       AS Opponent,
    s.Margin                        AS Team_Margin
FROM HS_Scores s
WHERE (s.Future_Game IS NULL OR s.Future_Game = 0)
  AND (s.Forfeit     IS NULL OR s.Forfeit     = 0)
  AND s.Date          IS NOT NULL
  AND s.Home_Score    IS NOT NULL
  AND s.Visitor_Score IS NOT NULL
  AND s.Margin        IS NOT NULL

UNION ALL

SELECT
    s.Visitor                       AS Team,
    CASE WHEN s.Home < s.Visitor
         THEN s.Home + '|' + s.Visitor
         ELSE s.Visitor + '|' + s.Home
    END                             AS GameKey,
    s.Date,
    s.Season,
    s.Home                          AS Opponent,
    -s.Margin                       AS Team_Margin
FROM HS_Scores s
WHERE (s.Future_Game IS NULL OR s.Future_Game = 0)
  AND (s.Forfeit     IS NULL OR s.Forfeit     = 0)
  AND s.Date          IS NOT NULL
  AND s.Home_Score    IS NOT NULL
  AND s.Visitor_Score IS NOT NULL
  AND s.Margin        IS NOT NULL

ORDER BY Team, Date;
"""

# -- Helpers -------------------------------------------------------------------

def safe_str(val, default=""):
    # step 1 - safe string conversion
    return str(val).strip() if val is not None else default

def safe_date(val):
    # step 2 - safe date conversion
    if val is None:
        return None
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    return str(val)[:10]

# -- Win streak finder ---------------------------------------------------------

def find_win_streaks(team_games, min_games):
    """
    Given a list of game dicts for ONE team (sorted by Date ascending),
    find all consecutive winning streaks (Team_Margin > 0).
    Any game with margin <= 0 (loss or tie) breaks the streak.
    Returns list of streak game-lists with length >= min_games.
    """
    # step 1 - initialize
    streaks       = []
    current_group = []

    for g in team_games:
        if g['team_margin'] > 0:
            # win - extend current streak
            current_group.append(g)
        else:
            # loss or tie - end current streak
            if len(current_group) >= min_games:
                streaks.append(current_group)
            current_group = []

    # step 2 - don't forget the last streak
    if len(current_group) >= min_games:
        streaks.append(current_group)

    return streaks

# -- Main ----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Win Streaks JSON Generator")
    print(f"Target: {OUTPUT_FILE}")
    print(f"Min games: {MIN_GAMES} | Top: {TOP_N}")
    print(f"Note: Losses AND ties break streaks.")
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

    # -- Step 1: Pull all games ------------------------------------------------
    print("\nStep 1: Pulling all games (may take a few minutes)...")
    try:
        cursor.execute(SQL_GET_GAMES)
        rows = cursor.fetchall()
        cols = [c[0].lower() for c in cursor.description]
        print(f"  {len(rows):,} team-game records retrieved.")
    except Exception as e:
        print(f"ERROR: Could not retrieve games: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    if not rows:
        print("WARNING: No game records returned.")
        sys.exit(0)

    # -- Step 2: Organize games by team ----------------------------------------
    print("\nStep 2: Organizing games by team...")

    team_games     = defaultdict(list)
    seen_game_keys = defaultdict(set)

    for row in rows:
        # step 1 - parse row
        g         = dict(zip(cols, row))
        team      = safe_str(g['team'])
        game_date = safe_date(g['date'])
        game_key  = f"{game_date}|{safe_str(g['gamekey'])}|{team}"

        # step 2 - skip true duplicates
        if game_key in seen_game_keys[team]:
            continue
        seen_game_keys[team].add(game_key)

        margin = int(g['team_margin']) if g['team_margin'] is not None else 0

        team_games[team].append({
            'date':        game_date,
            'season':      int(g['season']) if g['season'] else 0,
            'opponent':    safe_str(g['opponent']),
            'team_margin': margin,
        })

    print(f"  {len(team_games):,} teams with games.")

    # Sort each team's games by date
    for team in team_games:
        team_games[team].sort(key=lambda x: x['date'])

    # -- Step 3: Find win streaks ----------------------------------------------
    print(f"\nStep 3: Finding win streaks >= {MIN_GAMES} games...")

    all_streaks     = []
    teams_processed = 0

    for team, games in team_games.items():
        streaks = find_win_streaks(games, MIN_GAMES)
        for streak_games in streaks:
            margins = [g['team_margin'] for g in streak_games]
            all_streaks.append({
                'team':          team,
                'streak_length': len(streak_games),
                'date_start':    streak_games[0]['date'],
                'date_end':      streak_games[-1]['date'],
                'season_start':  streak_games[0]['season'],
                'season_end':    streak_games[-1]['season'],
                'avg_margin':    round(sum(margins) / len(margins), 1),
                'max_margin':    max(margins),
                'min_margin':    min(margins),
                'games':         streak_games,
            })
        teams_processed += 1
        if teams_processed % 5000 == 0:
            print(f"  Processed {teams_processed:,} teams...")

    print(f"  Found {len(all_streaks):,} qualifying streaks across all teams.")

    # Sort by streak length descending, avg_margin as tiebreaker
    all_streaks.sort(key=lambda x: (-x['streak_length'], -x['avg_margin']))
    top_streaks = all_streaks[:TOP_N]
    print(f"  Taking top {len(top_streaks)} by streak length.")

    # -- Step 4: Build output records ------------------------------------------
    print("\nStep 4: Building output records...")

    records = []
    for i, s in enumerate(top_streaks, 1):
        game_list = [{
            'date':     g['date'],
            'season':   g['season'],
            'opponent': g['opponent'],
            'margin':   g['team_margin'],
        } for g in s['games']]

        records.append({
            'rank':          i,
            'team':          s['team'],
            'streak_length': s['streak_length'],
            'date_start':    s['date_start'],
            'date_end':      s['date_end'],
            'season_start':  s['season_start'],
            'season_end':    s['season_end'],
            'avg_margin':    s['avg_margin'],
            'max_margin':    s['max_margin'],
            'min_margin':    s['min_margin'],
            'games':         game_list,
        })

    # -- Step 5: Write JSON ----------------------------------------------------
    print("\nStep 5: Writing JSON...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "metadata": {
            "timestamp":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":        "win-streaks",
            "min_games":   MIN_GAMES,
            "total_items": len(records),
            "description": (
                f"Top {TOP_N} longest consecutive winning streaks in high school football "
                f"history based on McKnight's database of 5M+ game records. "
                f"Any loss or tie ends a streak. "
                f"Data Caveat: Due to missing game logs prior to the digital era and varying "
                f"state rulings on forfeits, some streak lengths may differ slightly from "
                f"official state or national record books. For example, Charlotte Independence's "
                f"official streak is 109 games and South Panola's is 89 games. "
                f"8-man and 9-man streaks are included where data exists. "
                f"Pre-1960 records are likely incomplete — Sims (Union County, SC) had a "
                f"96-game unbeaten streak (1945-1954) and Bedford County Training School "
                f"(Shelbyville, TN) went 82 games without a loss (1943-1950). "
                f"Minimum {MIN_GAMES} wins required."
            ),
        },
        "items": records,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUTPUT_FILE}")
    if records:
        r = records[0]
        print(f"  #1: {r['team']}")
        print(f"      {r['streak_length']} wins | {r['date_start']} to {r['date_end']}")
        print(f"      Avg margin: +{r['avg_margin']} | Max margin: +{r['max_margin']}")
    print(f"\n  Total qualifying streaks found: {len(all_streaks):,}")
    print(f"  Output: top {len(records)}")
    print("\nDone.")

if __name__ == "__main__":
    main()