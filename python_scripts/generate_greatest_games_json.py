"""
generate_greatest_games_json.py
================================
Generates: docs/data/greatest-games/greatest-games.json

Runs the Pulse Rate Index (PRI) v3 query against hs_football_database and
writes a JSON file consumed by the Greatest Games static page.

PRI formula:
    PRI = (Home_Combined_Rating + Visitor_Combined_Rating) × Margin_Multiplier

Margin multipliers:
    0 (tie)  → 0.85
    1 pt     → 1.00   (max drama)
    2–3 pt   → 0.90
    4–7 pt   → 0.75
    8 pt     → 0.60
    9+ pt    → EXCLUDED

Elite filter (both teams must pass):
    Combined_Rating  > 20  (current season)
    Five_Year_Avg    > 20  (rolling 5-year average)
    Seasons_In_Window >= 2

Output JSON schema:
    {
      "metadata": { timestamp, total_items, description },
      "items": [
        {
          "rank":           int,
          "season":         int,
          "home_team":      str,
          "visitor_team":   str,
          "home_score":     int,
          "visitor_score":  int,
          "margin":         int,   # home_score - visitor_score
          "pri_raw":        float, # raw PRI value
          "pri_normalised": float  # scaled 0–100 (100 = highest game in dataset)
        },
        ...
      ]
    }

Usage:
    python generate_greatest_games_json.py

Hook into master update cycle after generate_global_data.py (Step 3).
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

# Relative to this script's location — adjust if script lives elsewhere
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT    = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR   = os.path.join(REPO_ROOT, "docs", "data", "greatest-games")
OUTPUT_FILE  = os.path.join(OUTPUT_DIR, "greatest-games.json")

TOP_N        = 250    # number of games to include
MIN_PRI_RANK = TOP_N  # safety — only keep TOP_N rows from SQL

# ── SQL query ─────────────────────────────────────────────────────────────────
#
# Uses temp tables for performance (CTE version ran >60 min; this runs <2 min).
# Step 1: build #ElitePrograms — teams that pass the elite filter for their season.
# Step 2: score all qualifying games, return TOP 250.
#
# NOTE: Is_Verified / PlayerLevel exclusion is baked in.
#   PlayerLevel IN (6,8,9) AND Is_Verified = 1  → excluded
#   All others → included (unverified states default to 11-man pending review)

SQL_QUERY = """
-- ============================================================
-- Greatest Games — Pulse Rate Index v3
-- ============================================================

-- Temp table cleanup (idempotent — safe to re-run in same session)
IF OBJECT_ID('tempdb..#ElitePrograms') IS NOT NULL DROP TABLE #ElitePrograms;
IF OBJECT_ID('tempdb..#GameScores')    IS NOT NULL DROP TABLE #GameScores;

-- ── STEP 1: Build #ElitePrograms ─────────────────────────────────────────────
-- One row per (TeamName, Season) for programs that pass the elite filter.
-- Five-year window: [Season-4, Season] inclusive.

SELECT
    r.Home                          AS TeamName,
    r.Season,
    r.Combined_Rating,              -- current-season rating
    AVG(r5.Combined_Rating)         AS Five_Year_Avg,
    COUNT(DISTINCT r5.Season)       AS Seasons_In_Window,

    -- Classification status (for metadata/debugging — not shown in UI)
    CASE
        WHEN tn.Is_Verified = 1 AND tn.PlayerLevel IN (6, 8, 9) THEN 'Excluded-NonEleven'
        WHEN tn.Is_Verified = 1 AND tn.PlayerLevel = 11          THEN 'Verified'
        ELSE                                                           'Unverified'
    END                             AS Classification_Status

INTO #ElitePrograms
FROM HS_Rankings r

-- Join to rolling 5-year window
INNER JOIN HS_Rankings r5
    ON  r5.Home   = r.Home
    AND r5.Season BETWEEN r.Season - 4 AND r.Season
    AND r5.Week   = 52

-- Join for classification
LEFT JOIN HS_Team_Names tn
    ON  tn.TeamName = r.Home

WHERE r.Week = 52
  -- Exclude confirmed non-11-man programs
  AND NOT (tn.Is_Verified = 1 AND tn.PlayerLevel IN (6, 8, 9))

GROUP BY
    r.Home,
    r.Season,
    r.Combined_Rating,
    tn.Is_Verified,
    tn.PlayerLevel

HAVING
    r.Combined_Rating  > 20   -- elite season
    AND AVG(r5.Combined_Rating) > 20   -- sustained excellence
    AND COUNT(DISTINCT r5.Season) >= 2; -- minimum data

-- ── STEP 2: Score all qualifying games, return TOP 250 ────────────────────────

SELECT TOP {top_n}
    ROW_NUMBER() OVER (ORDER BY
        (ep_h.Combined_Rating + ep_v.Combined_Rating) *
        CASE
            WHEN ABS(s.Margin) = 0 THEN 0.85
            WHEN ABS(s.Margin) = 1 THEN 1.00
            WHEN ABS(s.Margin) <= 3 THEN 0.90
            WHEN ABS(s.Margin) <= 7 THEN 0.75
            WHEN ABS(s.Margin) = 8  THEN 0.60
            ELSE 0   -- 9+ excluded via WHERE clause
        END
    DESC)                                       AS Rank,

    s.Season,
    s.Home                                      AS Home_Team,
    s.Visitor                                   AS Visitor_Team,
    s.Home_Score,
    s.Visitor_Score,
    s.Margin,                                   -- home_score - visitor_score

    -- Raw PRI
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
    AS DECIMAL(10,4))                           AS PRI_Raw,

    ep_h.Classification_Status                  AS Home_Classification,
    ep_v.Classification_Status                  AS Visitor_Classification

INTO #GameScores
FROM HS_Scores s

INNER JOIN #ElitePrograms ep_h
    ON  ep_h.TeamName = s.Home
    AND ep_h.Season   = s.Season

INNER JOIN #ElitePrograms ep_v
    ON  ep_v.TeamName = s.Visitor
    AND ep_v.Season   = s.Season

WHERE
    s.Future_Game IS NULL OR s.Future_Game = 0
    AND s.Forfeit  IS NULL OR s.Forfeit    = 0
    AND ABS(s.Margin) <= 8;   -- hard cutoff: 9+ point games excluded

-- Return results (PRI_Normalised is calculated in Python from the max value)
SELECT * FROM #GameScores ORDER BY Rank;

-- Cleanup
DROP TABLE #ElitePrograms;
DROP TABLE #GameScores;
""".format(top_n=TOP_N)

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise(value: float, max_value: float) -> float:
    """Scale raw PRI to 0–100 where 100 = top game."""
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

    # ── Connect ───────────────────────────────────────────────────────────────
    print("\nConnecting to SQL Server...")
    try:
        conn = pyodbc.connect(CONNECTION_STRING, timeout=30)
        cursor = conn.cursor()
        print("Connected.")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Execute query ─────────────────────────────────────────────────────────
    print("\nRunning PRI v3 query (may take up to 2 minutes)...")
    try:
        # pyodbc needs each batch separated — split on the GO-equivalent
        # Since we're using temp tables in one session, execute as one block
        cursor.execute(SQL_QUERY)

        # Advance past any intermediate result sets (temp table creation)
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
        print("WARNING: No rows returned. Check PRI query and elite filter thresholds.")
        sys.exit(0)

    # ── Build records ─────────────────────────────────────────────────────────
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

    # ── Normalise PRI ─────────────────────────────────────────────────────────
    max_pri = max(r["pri_raw"] for r in records) if records else 1.0
    print(f"Max raw PRI: {max_pri:.4f} (game #{1})")
    for r in records:
        r["pri_normalised"] = normalise(r["pri_raw"], max_pri)

    # ── Write JSON ────────────────────────────────────────────────────────────
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
                "Only games between elite programs (Combined Rating > 20, "
                "five-year avg > 20) with margin ≤ 8 points are included."
            ),
        },
        "items": records,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Written: {OUTPUT_FILE}")
    print(f"  {len(records)} games | max PRI: {max_pri:.4f} | "
          f"timestamp: {output['metadata']['timestamp']}")
    print("\nDone.")


if __name__ == "__main__":
    main()