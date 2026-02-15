"""
generate_greatest_games_json.py
================================
Generates: docs/data/greatest-games/greatest-games.json

Schema notes (actual DB):
  - HS_Team_Names:         Team_Name, City, State, ...
  - HS_Team_Level_History: TeamName, PlayerLevel, Season_Begin, Season_End
  - HS_Rankings:           Home, Season, Week, Combined_Rating, ...
  - HS_Scores:             Home, Visitor, Season, Home_Score, Visitor_Score, Margin, ...

PRI formula:
    PRI = (Home_Combined_Rating + Visitor_Combined_Rating) x Margin_Multiplier

Margin multipliers:
    0 (tie)  -> 0.85
    1 pt     -> 1.00  (max drama)
    2-3 pt   -> 0.90
    4-7 pt   -> 0.75
    8 pt     -> 0.60
    9+ pt    -> EXCLUDED

Elite filter (both teams must pass ALL three):
    Combined_Rating   > 20  (current season)
    Five_Year_Avg     > 20  (rolling 5-year average)
    Seasons_In_Window >= 2  (minimum data requirement)

Non-11-man exclusion:
    Uses HS_Team_Level_History. Teams with PlayerLevel IN (6,8,9) for that
    season are excluded. Teams with no level history default to 11-man (included).
"""

import json
import os
import sys
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

# Script lives in python_scripts\ — one level below repo root
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_DIR  = os.path.join(REPO_ROOT, "docs", "data", "greatest-games")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "greatest-games.json")

TOP_N = 250

# ── SQL Query ─────────────────────────────────────────────────────────────────

SQL_QUERY = """
IF OBJECT_ID('tempdb..#ElitePrograms') IS NOT NULL DROP TABLE #ElitePrograms;
IF OBJECT_ID('tempdb..#GameScores')    IS NOT NULL DROP TABLE #GameScores;

-- STEP 1: Build #ElitePrograms
-- One row per (TeamName, Season) passing the elite filter.
-- Excludes non-11-man programs via HS_Team_Level_History.

SELECT
    r.Home                      AS TeamName,
    r.Season,
    r.Combined_Rating,
    AVG(r5.Combined_Rating)     AS Five_Year_Avg,
    COUNT(DISTINCT r5.Season)   AS Seasons_In_Window

INTO #ElitePrograms
FROM HS_Rankings r

INNER JOIN HS_Rankings r5
    ON  r5.Home   = r.Home
    AND r5.Season BETWEEN r.Season - 4 AND r.Season
    AND r5.Week   = 52

WHERE r.Week = 52

  -- Exclude confirmed non-11-man programs (8-man, 9-man, 6-man)
  -- Teams with no entry in HS_Team_Level_History are treated as 11-man
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

-- STEP 2: Score qualifying games, return TOP 250 by PRI descending

SELECT TOP {top_n}
    ROW_NUMBER() OVER (ORDER BY
        (ep_h.Combined_Rating + ep_v.Combined_Rating) *
        CASE
            WHEN ABS(s.Margin) = 0 THEN 0.85
            WHEN ABS(s.Margin) = 1 THEN 1.00
            WHEN ABS(s.Margin) <= 3 THEN 0.90
            WHEN ABS(s.Margin) <= 7 THEN 0.75
            WHEN ABS(s.Margin) = 8  THEN 0.60
            ELSE 0
        END DESC
    )                           AS Rank,

    s.Season,
    s.Home                      AS Home_Team,
    s.Visitor                   AS Visitor_Team,
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

INTO #GameScores
FROM HS_Scores s

INNER JOIN #ElitePrograms ep_h
    ON  ep_h.TeamName = s.Home
    AND ep_h.Season   = s.Season

INNER JOIN #ElitePrograms ep_v
    ON  ep_v.TeamName = s.Visitor
    AND ep_v.Season   = s.Season

WHERE
    (s.Future_Game IS NULL OR s.Future_Game = 0)
    AND (s.Forfeit IS NULL OR s.Forfeit = 0)
    AND ABS(s.Margin) <= 8;

SELECT * FROM #GameScores ORDER BY Rank;

DROP TABLE #ElitePrograms;
DROP TABLE #GameScores;
""".format(top_n=TOP_N)

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise(value, max_value):
    if max_value <= 0:
        return 0.0
    return round((value / max_value) * 100.0, 2)

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

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Greatest Games JSON Generator")
    print(f"Target: {OUTPUT_FILE}")
    print("=" * 60)

    print("\nConnecting to SQL Server...")
    try:
        conn = pyodbc.connect(CONNECTION_STRING, timeout=30)
        cursor = conn.cursor()
        print("Connected.")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nRunning PRI v3 query (may take up to 2 minutes)...")
    try:
        cursor.execute(SQL_QUERY)

        # Advance past intermediate result sets (temp table DROP/SELECT INTO)
        while cursor.description is None:
            if not cursor.nextset():
                break

        rows = cursor.fetchall()
        columns = [col[0].lower() for col in cursor.description]
        print(f"Query returned {len(rows)} rows.")

    except Exception as e:
        print(f"ERROR: Query failed: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    if not rows:
        print("WARNING: No rows returned. Check query and elite filter thresholds.")
        sys.exit(0)

    # Build records
    records = []
    for row in rows:
        r = dict(zip(columns, row))
        records.append({
            "rank":          safe_int(r.get("rank")),
            "season":        safe_int(r.get("season")),
            "home_team":     safe_str(r.get("home_team")),
            "visitor_team":  safe_str(r.get("visitor_team")),
            "home_score":    safe_int(r.get("home_score")),
            "visitor_score": safe_int(r.get("visitor_score")),
            "margin":        safe_int(r.get("margin")),
            "pri_raw":       safe_float(r.get("pri_raw")),
        })

    # Normalise PRI to 0-100
    max_pri = max(r["pri_raw"] for r in records) if records else 1.0
    print(f"Max raw PRI: {max_pri:.4f}")
    for r in records:
        r["pri_normalised"] = normalise(r["pri_raw"], max_pri)

    # Write JSON
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "metadata": {
            "timestamp":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":        "greatest-games",
            "total_items": len(records),
            "top_n":       TOP_N,
            "description": (
                "Top 250 greatest games in high school football history, "
                "ranked by the Pulse Rate Index (PRI v3). "
                "Only games between elite programs (Combined_Rating > 20, "
                "five-year avg > 20) with margin 8 points or fewer are included."
            ),
        },
        "items": records,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUTPUT_FILE}")
    print(f"  {len(records)} games | max PRI: {max_pri:.4f} | {output['metadata']['timestamp']}")
    print("\nDone.")


if __name__ == "__main__":
    main()