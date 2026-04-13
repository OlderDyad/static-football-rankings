"""
generate_border_wars_json.py
=============================
Generates: docs/data/border-wars/border-wars.json

Approach:
  For each state, find the top 5 opponent states by total games played
  in cross-state matchups (home state != visitor state).
  Compute all-time W-L-T and win % (ties = 0.5 win) for each matchup.
  No team-level filtering — all programs included.

Output JSON schema:
  {
    "metadata": { timestamp, total_states, description },
    "items": [
      {
        "state":     str,   # e.g. "TX"
        "opponents": [
          {
            "state":    str,    # opponent state code
            "wins":     int,
            "losses":   int,
            "ties":     int,
            "games":    int,
            "win_pct":  float   # (wins + 0.5*ties) / games * 100
          },
          ... (up to 5)
        ]
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
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR  = os.path.join(REPO_ROOT, "docs", "data", "border-wars")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "border-wars.json")

TOP_OPPONENTS = 5  # top N opponent states per state

# ── SQL ───────────────────────────────────────────────────────────────────────
#
# Pull all cross-state games with home/visitor state codes.
# HS_Team_Names.State holds the state code for each team.
# We join twice — once for home team, once for visitor team.
# Only include completed, non-forfeit games.

VALID_STATES = {
    # US States + DC
    'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID',
    'IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO',
    'MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA',
    'RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
    # Canadian Provinces
    'AB','BC','MB','NB','NS','ON','QC','SK'
}

SQL_CROSS_STATE_GAMES = """
SELECT
    SUBSTRING(RIGHT(RTRIM(s.Home), 4), 2, 2)     AS Home_State,
    SUBSTRING(RIGHT(RTRIM(s.Visitor), 4), 2, 2)  AS Visitor_State,
    s.Home_Score,
    s.Visitor_Score
FROM HS_Scores s
WHERE
    s.Home    LIKE '%([A-Z][A-Z])'
    AND s.Visitor LIKE '%([A-Z][A-Z])'
    AND SUBSTRING(RIGHT(RTRIM(s.Home), 4), 2, 2)
        <> SUBSTRING(RIGHT(RTRIM(s.Visitor), 4), 2, 2)
    AND (s.Future_Game IS NULL OR s.Future_Game = 0)
    AND (s.Forfeit     IS NULL OR s.Forfeit     = 0)
    AND s.Home_Score    IS NOT NULL
    AND s.Visitor_Score IS NOT NULL
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def win_pct(wins, losses, ties):
    """Win % with ties counting as 0.5 win."""
    games = wins + losses + ties
    if games == 0:
        return 0.0
    return round(((wins + 0.5 * ties) / games) * 100.0, 1)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Border Wars JSON Generator")
    print(f"Target: {OUTPUT_FILE}")
    print(f"Top {TOP_OPPONENTS} opponent states per state")
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

    # ── Pull cross-state games ────────────────────────────────────────────────
    print("\nStep 1: Pulling cross-state games...")
    try:
        cursor.execute(SQL_CROSS_STATE_GAMES)
        rows = cursor.fetchall()
        print(f"  Retrieved {len(rows):,} cross-state games.")
    except Exception as e:
        print(f"ERROR: Query failed: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    if not rows:
        print("WARNING: No cross-state games returned.")
        sys.exit(0)

    # ── Aggregate W-L-T by state pair ─────────────────────────────────────────
    # Key: (state_a, state_b) where state_a is the perspective state
    # We store from BOTH perspectives so lookup is simple.
    print("\nStep 2: Aggregating W-L-T by state pair...")

    # records[state][opponent_state] = {"wins": 0, "losses": 0, "ties": 0}
    records = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0}))

    for row in rows:
        home_state    = str(row[0]).strip()
        visitor_state = str(row[1]).strip()
        home_score    = int(row[2]) if row[2] is not None else 0
        visitor_score = int(row[3]) if row[3] is not None else 0

        # Skip invalid state codes
        if home_state not in VALID_STATES or visitor_state not in VALID_STATES:
            continue

        if home_score > visitor_score:
            # Home wins
            records[home_state][visitor_state]["wins"]   += 1
            records[visitor_state][home_state]["losses"] += 1
        elif visitor_score > home_score:
            # Visitor wins
            records[visitor_state][home_state]["wins"]   += 1
            records[home_state][visitor_state]["losses"] += 1
        else:
            # Tie
            records[home_state][visitor_state]["ties"] += 1
            records[visitor_state][home_state]["ties"] += 1

    print(f"  Found {len(records):,} states with cross-state game history.")

    # ── Build output items ────────────────────────────────────────────────────
    print("\nStep 3: Building top-5 opponent lists...")

    items = []
    for state in sorted(records.keys()):
        opponents_raw = []
        for opp_state, rec in records[state].items():
            w = rec["wins"]
            l = rec["losses"]
            t = rec["ties"]
            g = w + l + t
            opponents_raw.append({
                "state":   opp_state,
                "wins":    w,
                "losses":  l,
                "ties":    t,
                "games":   g,
                "win_pct": win_pct(w, l, t),
            })

        # Sort by total games descending, then win_pct descending as tiebreaker
        opponents_raw.sort(key=lambda x: (-x["games"], -x["win_pct"]))
        top_opponents = opponents_raw[:TOP_OPPONENTS]

        items.append({
            "state":     state,
            "opponents": top_opponents,
        })

    print(f"  Built entries for {len(items):,} states.")

    # ── Write JSON ────────────────────────────────────────────────────────────
    print("\nStep 4: Writing JSON...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "metadata": {
            "timestamp":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":         "border-wars",
            "total_states": len(items),
            "description":  (
                f"All-time cross-state win-loss records for each state. "
                f"Shows the top {TOP_OPPONENTS} opponent states by total games played. "
                f"Win % calculated with ties counting as half a win. "
                f"Includes all programs regardless of classification."
            ),
        },
        "items": items,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUTPUT_FILE}")
    print(f"  {len(items)} states")
    total_games = len(rows)
    print(f"  {total_games:,} cross-state games processed")
    print(f"  Top state by games: {items[0]['state']} "
          f"({sum(o['games'] for o in items[0]['opponents'])} games vs top 5 opponents)")
    print("\nDone.")


if __name__ == "__main__":
    main()