"""
generate_greatest_rivalries_json.py
=====================================
Generates: docs/data/greatest-rivalries/greatest-rivalries.json

Approach:
  Step 1 — Pull top 50,000 qualifying games from SQL (both teams elite,
            margin <= 8) with PRI scores. Same elite filter as Greatest Games.
  Step 2 — Aggregate by normalized team pair (alphabetical so A vs B = B vs A).
            Compute: meeting count, total PRI, average PRI, season range.
  Step 3 — Pull all-time head-to-head record for each qualifying pair
            from HS_Scores (no elite/margin filter).
  Step 4 — Filter to pairs with >= MIN_MEETINGS qualifying meetings.
            Sort by Total PRI descending. Output top 100.

Output JSON schema:
  {
    "metadata": { timestamp, total_items, min_meetings, description },
    "items": [
      {
        "rank":               int,
        "team_a":             str,   # alphabetically first
        "team_b":             str,
        "qualifying_meetings":int,   # games in top-50k pool
        "total_pri":          float, # sum of pri_normalised across qualifying games
        "avg_pri":            float, # total_pri / qualifying_meetings
        "season_first":       int,   # earliest qualifying meeting
        "season_last":        int,   # most recent qualifying meeting
        "alltime_team_a_wins":int,
        "alltime_team_b_wins":int,
        "alltime_ties":       int,
        "series_leader":      str,   # "Team A leads X-Y", "Series tied X-X"
        "qualifying_games":   list   # [{season, home, visitor, home_score,
                                     #   visitor_score, margin, pri_normalised}]
      }
    ]
  }
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import pyodbc

# ── Configuration ─────────────────────────────────────────────────────────────

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_DIR  = os.path.join(REPO_ROOT, "docs", "data", "greatest-rivalries")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "greatest-rivalries.json")

TOP_GAMES    = 50_000   # qualifying game pool
MIN_MEETINGS = 5        # minimum qualifying meetings to appear — tune as needed
TOP_RIVALS   = 100      # number of rivalries to output

# ── SQL: Pull qualifying games ────────────────────────────────────────────────
#
# Same elite filter as Greatest Games:
#   - Both teams Combined_Rating > 20, five-year avg > 20, >= 2 seasons in window
#   - Non-11-man programs excluded via HS_Team_Level_History
#   - Margin <= 8
# Returns top 50,000 by PRI descending.

SQL_QUALIFYING_GAMES = """
IF OBJECT_ID('tempdb..#EP_Rivals') IS NOT NULL DROP TABLE #EP_Rivals;

-- Build elite programs temp table
SELECT
    r.Home                      AS TeamName,
    r.Season,
    r.Combined_Rating,
    AVG(r5.Combined_Rating)     AS Five_Year_Avg,
    COUNT(DISTINCT r5.Season)   AS Seasons_In_Window

INTO #EP_Rivals
FROM HS_Rankings r

INNER JOIN HS_Rankings r5
    ON  r5.Home   = r.Home
    AND r5.Season BETWEEN r.Season - 4 AND r.Season
    AND r5.Week   = 52

WHERE r.Week = 52

  AND NOT EXISTS (
      SELECT 1
      FROM HS_Team_Level_History lh
      WHERE lh.TeamName    = r.Home
        AND lh.PlayerLevel IN (6, 8, 9)
        AND r.Season BETWEEN lh.Season_Begin AND lh.Season_End
  )

GROUP BY
    r.Home,
    r.Season,
    r.Combined_Rating

HAVING
    r.Combined_Rating           > 20
    AND AVG(r5.Combined_Rating) > 20
    AND COUNT(DISTINCT r5.Season) >= 2;

-- Score and return top qualifying games
SELECT TOP {top_games}
    s.Season,
    s.Home,
    s.Visitor,
    s.Home_Score,
    s.Visitor_Score,
    s.Margin,
    CAST(
        (ep_h.Combined_Rating + ep_v.Combined_Rating) *
        CASE
            WHEN ABS(s.Margin) = 0 THEN 0.85
            WHEN ABS(s.Margin) = 1 THEN 1.00
            WHEN ABS(s.Margin) <= 3 THEN 0.90
            WHEN ABS(s.Margin) <= 7 THEN 0.75
            WHEN ABS(s.Margin) = 8  THEN 0.60
            ELSE 0
        END
    AS DECIMAL(10,4))           AS PRI_Raw

FROM HS_Scores s

INNER JOIN #EP_Rivals ep_h
    ON  ep_h.TeamName = s.Home
    AND ep_h.Season   = s.Season

INNER JOIN #EP_Rivals ep_v
    ON  ep_v.TeamName = s.Visitor
    AND ep_v.Season   = s.Season

WHERE
    (s.Future_Game IS NULL OR s.Future_Game = 0)
    AND (s.Forfeit IS NULL OR s.Forfeit = 0)
    AND ABS(s.Margin) <= 8

ORDER BY PRI_Raw DESC;

DROP TABLE #EP_Rivals;
""".format(top_games=TOP_GAMES)

# ── SQL: All-time head-to-head record for a pair ──────────────────────────────
#
# No elite or margin filter — all games ever played between the two programs.
# Returns win counts for each team plus ties.
#
# FIX: Team_B_Wins is computed as "games where Team_A lost" (flipping > to <).
# This avoids a pyodbc/SQL Server parameter binding issue where two identical
# CASE expression patterns with different positional ? params can return the
# same result.  By using distinct SQL logic (> vs <) for Team_A_Wins vs
# Team_B_Wins, all 4 CASE params reference team_a and the results are correct.

SQL_ALLTIME_RECORD = """
SELECT
    SUM(CASE WHEN (Home = ? AND Home_Score > Visitor_Score)
             OR   (Visitor = ? AND Visitor_Score > Home_Score)
             THEN 1 ELSE 0 END)   AS Team_A_Wins,
    SUM(CASE WHEN (Home = ? AND Home_Score < Visitor_Score)
             OR   (Visitor = ? AND Visitor_Score < Home_Score)
             THEN 1 ELSE 0 END)   AS Team_B_Wins,
    SUM(CASE WHEN Home_Score = Visitor_Score THEN 1 ELSE 0 END) AS Ties
FROM HS_Scores
WHERE
    (
        (Home = ? AND Visitor = ?)
        OR (Home = ? AND Visitor = ?)
    )
    AND (Future_Game IS NULL OR Future_Game = 0)
    AND (Forfeit IS NULL OR Forfeit = 0);
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def pair_key(team_a, team_b):
    """Normalized pair key — alphabetical so order doesn't matter."""
    return tuple(sorted([team_a, team_b]))

def normalise(value, max_value):
    if max_value <= 0:
        return 0.0
    return round((float(value) / float(max_value)) * 100.0, 2)

def safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def safe_str(val, default=""):
    if val is None:
        return default
    return str(val).strip()

def series_leader_text(team_a, team_b, a_wins, b_wins, ties):
    """Format the series leader string."""
    if a_wins > b_wins:
        return f"{team_a} leads {a_wins}-{b_wins}" + (f"-{ties}" if ties else "")
    elif b_wins > a_wins:
        return f"{team_b} leads {b_wins}-{a_wins}" + (f"-{ties}" if ties else "")
    else:
        return f"Series tied {a_wins}-{b_wins}" + (f"-{ties}" if ties else "")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Greatest Rivalries JSON Generator")
    print(f"Target: {OUTPUT_FILE}")
    print(f"Game pool: top {TOP_GAMES:,} | Min meetings: {MIN_MEETINGS} | Output: top {TOP_RIVALS}")
    print("=" * 60)

    # ── Connect ───────────────────────────────────────────────────────────────
    print("\nConnecting to SQL Server...")
    try:
        conn = pyodbc.connect(CONNECTION_STRING, timeout=30)
        cursor = conn.cursor()
        print("Connected.")
    except Exception as e:
        print(f"ERROR: Could not connect: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Step 1: Pull qualifying games ─────────────────────────────────────────
    print(f"\nStep 1: Pulling top {TOP_GAMES:,} qualifying games (may take 2-3 minutes)...")
    try:
        cursor.execute(SQL_QUALIFYING_GAMES)

        # Advance past intermediate result sets
        while cursor.description is None:
            if not cursor.nextset():
                break

        rows = cursor.fetchall()
        columns = [col[0].lower() for col in cursor.description]
        print(f"  Retrieved {len(rows):,} qualifying games.")

    except Exception as e:
        print(f"ERROR: Qualifying games query failed: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not rows:
        print("WARNING: No qualifying games returned.")
        conn.close()
        sys.exit(0)

    # ── Step 2: Normalise PRI and aggregate by pair ───────────────────────────
    print("\nStep 2: Normalising PRI and aggregating by rivalry pair...")

    games = [dict(zip(columns, r)) for r in rows]
    max_pri = float(max(g["pri_raw"] for g in games)) if games else 1.0

    # Aggregate
    pair_data = defaultdict(lambda: {
        "games": [],
        "seasons": [],
    })

    for g in games:
        home    = safe_str(g["home"])
        visitor = safe_str(g["visitor"])
        key     = pair_key(home, visitor)
        pri_n   = normalise(safe_float(g["pri_raw"]), max_pri)

        pair_data[key]["games"].append({
            "season":        safe_int(g["season"]),
            "home":          home,
            "visitor":       visitor,
            "home_score":    safe_int(g["home_score"]),
            "visitor_score": safe_int(g["visitor_score"]),
            "margin":        safe_int(g["margin"]),
            "pri_normalised": pri_n,
        })
        pair_data[key]["seasons"].append(safe_int(g["season"]))

    print(f"  Found {len(pair_data):,} unique rivalry pairs.")

    # Filter to minimum meetings and compute totals
    qualifying_pairs = []
    for (team_a, team_b), data in pair_data.items():
        meetings = len(data["games"])
        if meetings < MIN_MEETINGS:
            continue

        total_pri = round(sum(g["pri_normalised"] for g in data["games"]), 2)
        avg_pri   = round(total_pri / meetings, 2)
        seasons   = data["seasons"]

        qualifying_pairs.append({
            "team_a":               team_a,
            "team_b":               team_b,
            "qualifying_meetings":  meetings,
            "total_pri":            total_pri,
            "avg_pri":              avg_pri,
            "season_first":         min(seasons),
            "season_last":          max(seasons),
            "qualifying_games":     sorted(data["games"], key=lambda x: x["season"]),
        })

    # Sort by total PRI descending, take top 100
    qualifying_pairs.sort(key=lambda x: x["total_pri"], reverse=True)
    top_pairs = qualifying_pairs[:TOP_RIVALS]

    print(f"  {len(qualifying_pairs):,} pairs meet the {MIN_MEETINGS}+ meeting threshold.")
    print(f"  Taking top {len(top_pairs)} by Total PRI.")

    # ── Step 3: All-time head-to-head records ─────────────────────────────────
    print(f"\nStep 3: Fetching all-time head-to-head records for {len(top_pairs)} pairs...")

    records = []
    for i, pair in enumerate(top_pairs, 1):
        team_a = pair["team_a"]
        team_b = pair["team_b"]

        try:
            # Parameters: team_a used for BOTH Team_A_Wins (where A wins)
            # and Team_B_Wins (where A loses = B wins).
            # WHERE clause uses team_a + team_b to filter to the matchup.
            cursor.execute(SQL_ALLTIME_RECORD, (
                team_a, team_a,   # Team_A_Wins: team_a home win + team_a visitor win
                team_a, team_a,   # Team_B_Wins: team_a home loss + team_a visitor loss
                team_a, team_b,   # WHERE clause pair 1
                team_b, team_a,   # WHERE clause pair 2
            ))
            row = cursor.fetchone()
            a_wins = safe_int(row[0]) if row else 0
            b_wins = safe_int(row[1]) if row else 0
            ties   = safe_int(row[2]) if row else 0
        except Exception as e:
            print(f"  WARNING: Could not fetch record for {team_a} vs {team_b}: {e}")
            a_wins, b_wins, ties = 0, 0, 0

        leader = series_leader_text(team_a, team_b, a_wins, b_wins, ties)

        # Validation check (first pair only)
        if i == 1:
            total_games = a_wins + b_wins + ties
            print(f"  Validation — {team_a} vs {team_b}:")
            print(f"    {team_a} wins: {a_wins}")
            print(f"    {team_b} wins: {b_wins}")
            print(f"    Ties: {ties}  |  Total games: {total_games}")
            print(f"    Series leader: {leader}")

        records.append({
            "rank":                i,
            "team_a":              team_a,
            "team_b":              team_b,
            "qualifying_meetings": pair["qualifying_meetings"],
            "total_pri":           pair["total_pri"],
            "avg_pri":             pair["avg_pri"],
            "season_first":        pair["season_first"],
            "season_last":         pair["season_last"],
            "alltime_team_a_wins": a_wins,
            "alltime_team_b_wins": b_wins,
            "alltime_ties":        ties,
            "series_leader":       leader,
            "qualifying_games":    pair["qualifying_games"],
        })

        if i % 10 == 0:
            print(f"  Processed {i}/{len(top_pairs)}...")

    conn.close()

    # ── Step 4: Write JSON ────────────────────────────────────────────────────
    print("\nStep 4: Writing JSON...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "metadata": {
            "timestamp":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":         "greatest-rivalries",
            "total_items":  len(records),
            "top_games":    TOP_GAMES,
            "min_meetings": MIN_MEETINGS,
            "description":  (
                f"Top {TOP_RIVALS} greatest rivalries in high school football history. "
                f"Rivalries are ranked by Total PRI — the sum of Pulse Rate Index scores "
                f"across all qualifying meetings (both programs elite, margin <= 8 points). "
                f"Minimum {MIN_MEETINGS} qualifying meetings required. "
                f"All-time head-to-head records include all games regardless of margin."
            ),
        },
        "items": records,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUTPUT_FILE}")
    print(f"  {len(records)} rivalries | top pair: {records[0]['team_a']} vs {records[0]['team_b']} "
          f"({records[0]['qualifying_meetings']} meetings, Total PRI {records[0]['total_pri']:.1f})")
    print(f"\nNote: If results look thin, lower MIN_MEETINGS (currently {MIN_MEETINGS}).")
    print("Done.")


if __name__ == "__main__":
    main()