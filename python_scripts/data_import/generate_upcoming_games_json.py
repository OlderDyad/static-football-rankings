"""
generate_upcoming_games_json.py
================================
Generates: docs/data/upcoming-games/upcoming-games.json
Page:      docs/pages/public/upcoming-games/index.html

The Greatest Games idea applied to games that haven't been played yet:
the top 100 matchups of the coming week, ranked by a Game Index built the
same way as the Pulse Rate Index (PRI) -- except the actual final margin is
replaced by the PROJECTED margin from the two teams' current Combined Ratings.

Game Index formula:
    Projected margin (home) = (Home_CR - Visitor_CR) / 0.958 + 1.6 home-field pts
    Game Index = (Home_CR + Visitor_CR) x Margin_Multiplier(|projected margin|)

Margin multipliers (same bands as Greatest Games; a projection is never an
exact tie, so the 0.85 tie band does not apply):
    <= 1 pt  -> 1.00
    <= 3 pt  -> 0.90
    <= 7 pt  -> 0.75
    <= 8 pt  -> 0.60
    >  8 pt  -> excluded

Qualifying filter, both teams must pass:
    Combined_Rating   > 20   (current season, latest calculated week)
    Not a non-11-man program (HS_Team_Level_History PlayerLevel 6, 8, 9)
  Optional (--five-year): Greatest Games' five-year avg > 20 and 2+ seasons.
  Off by default -- with it, a typical week has only ~40 qualifying games.

Upcoming games come from dbo.Future_Games (filled by FinalizeMaxPrepsData
from each team's full MaxPreps schedule). Games already in HS_Scores (played)
are skipped, and if the same pair appears more than once in the window
(rescheduled), the most recent batch's row is used.

Home-field note: 1.6 points, measured from 2004-2025 results (see
HOME_FIELD_PTS). Future_Games doesn't record neutral sites, so it is applied
to every game.

Usage:
    python generate_upcoming_games_json.py                     # today + next 6 days
    python generate_upcoming_games_json.py --start 2026-10-15 --end 2026-10-18
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

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
OUTPUT_DIR  = os.path.join(REPO_ROOT, "docs", "data", "upcoming-games")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "upcoming-games.json")

TOP_N = 100
ELITE_MIN = 20.0

# Home-field advantage in points, MEASURED 2026-10-15 from 1,764,090 MaxPreps-era
# (2004-2025) home/visitor games against final Week-52 ratings, by regression
# of actual home margin on rating difference: intercept 1.50 pts (all games,
# slope 1.00) and 1.73 pts (matchups within 14). Stable 1.0-1.8 every season.
# Deliberately NOT Coefficients.Home_Field_Adv_Margin (5.4), which the measured
# data does not support. Raw average home margin (3.33) overstates it because
# stronger teams host more often (playoff seeding).
HOME_FIELD_PTS = 1.6
COMBINED_PER_POINT = 0.958   # Combined_Rating = 0.958 x Margin rating + 2.791

# ── SQL ───────────────────────────────────────────────────────────────────────

SQL_LATEST = """
SELECT TOP 1 Season, Week
FROM HS_Rankings
WHERE Season <= YEAR(GETDATE())
ORDER BY Season DESC, Week DESC
"""


# Params: season, week, season, season, season, start, end
SQL_GAMES = """
;WITH cur AS (
    SELECT Home AS Team,
           ISNULL(Combined_Rating,
                  0.958 * Avg_Of_Avg_Of_Home_Modified_Score + 2.791) AS CR
    FROM HS_Rankings
    WHERE Season = ? AND Week = ?
),
ranked AS (
    SELECT Team, CR, ROW_NUMBER() OVER (ORDER BY CR DESC) AS NatRank
    FROM cur
),
hist AS (
    SELECT Home AS Team, Season,
           ISNULL(Combined_Rating,
                  0.958 * Avg_Of_Avg_Of_Home_Modified_Score + 2.791) AS CR
    FROM HS_Rankings
    WHERE Week = 52 AND Season BETWEEN ? - 4 AND ? - 1
),
elite AS (
    SELECT r.Team, r.CR, r.NatRank,
           (r.CR + ISNULL(SUM(h.CR), 0)) / (1 + COUNT(h.Season)) AS FiveYrAvg,
           1 + COUNT(h.Season)                                    AS SeasonsInWindow
    FROM ranked r
    LEFT JOIN hist h ON h.Team = r.Team
    WHERE NOT EXISTS (
        SELECT 1 FROM HS_Team_Level_History lh
        WHERE lh.TeamName = r.Team
          AND lh.PlayerLevel IN (6, 8, 9)
          AND ? BETWEEN lh.Season_Begin AND lh.Season_End
    )
    GROUP BY r.Team, r.CR, r.NatRank
    HAVING {having}
),
fg AS (
    SELECT f.GameID, f.RawHomeTeam AS Home, f.RawAwayTeam AS Visitor,
           CAST(f.GameDate AS date) AS GameDate, f.GameTime,
           ROW_NUMBER() OVER (
               PARTITION BY
                   CASE WHEN f.RawHomeTeam < f.RawAwayTeam THEN f.RawHomeTeam ELSE f.RawAwayTeam END,
                   CASE WHEN f.RawHomeTeam < f.RawAwayTeam THEN f.RawAwayTeam ELSE f.RawHomeTeam END
               ORDER BY f.BatchID DESC, f.FutureGameID DESC) AS rn
    FROM Future_Games f
    WHERE CAST(f.GameDate AS date) BETWEEN ? AND ?
      AND NOT EXISTS (SELECT 1 FROM HS_Scores s WHERE s.Access_ID = f.GameID)
)
SELECT g.GameID, g.GameDate, g.GameTime, g.Home, g.Visitor,
       eh.CR AS Home_CR, ev.CR AS Visitor_CR,
       eh.NatRank AS Home_Rank, ev.NatRank AS Visitor_Rank
FROM fg g
JOIN elite eh ON eh.Team = g.Home
JOIN elite ev ON ev.Team = g.Visitor
WHERE g.rn = 1
"""

# Params: season, season
SQL_RECORDS = """
SELECT Team, SUM(W) AS W, SUM(L) AS L, SUM(T) AS T
FROM (
    SELECT Home AS Team,
           CASE WHEN Home_Score > Visitor_Score THEN 1 ELSE 0 END AS W,
           CASE WHEN Home_Score < Visitor_Score THEN 1 ELSE 0 END AS L,
           CASE WHEN Home_Score = Visitor_Score THEN 1 ELSE 0 END AS T
    FROM HS_Scores
    WHERE Season = ? AND Home_Score IS NOT NULL AND Visitor_Score IS NOT NULL
      AND (Future_Game IS NULL OR Future_Game = 0)
    UNION ALL
    SELECT Visitor,
           CASE WHEN Visitor_Score > Home_Score THEN 1 ELSE 0 END,
           CASE WHEN Visitor_Score < Home_Score THEN 1 ELSE 0 END,
           CASE WHEN Visitor_Score = Home_Score THEN 1 ELSE 0 END
    FROM HS_Scores
    WHERE Season = ? AND Home_Score IS NOT NULL AND Visitor_Score IS NOT NULL
      AND (Future_Game IS NULL OR Future_Game = 0)
) x
GROUP BY Team
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def multiplier(abs_margin):
    if abs_margin <= 1:
        return 1.00
    if abs_margin <= 3:
        return 0.90
    if abs_margin <= 7:
        return 0.75
    if abs_margin <= 8:
        return 0.60
    return 0.0


def record_str(rec):
    if not rec:
        return ""
    w, l, t = rec
    return f"{w}-{l}" + (f"-{t}" if t else "")


def parse_args():
    p = argparse.ArgumentParser(description="Top upcoming games JSON generator.")
    p.add_argument("--start", help="first game date, YYYY-MM-DD (default: today)")
    p.add_argument("--end", help="last game date, YYYY-MM-DD (default: start + 6 days)")
    p.add_argument("--min-rating", type=float, default=ELITE_MIN,
                   help=f"minimum current Combined Rating for both teams (default {ELITE_MIN})")
    # 2026-10-15: five-year requirement OFF by default. Tested on the week of
    # 10/15-10/18: rating > 20 + five-year avg gave only 37 games within 8 pts;
    # rating > 20 alone gave 116 (enough for the top 100). A weekly preview
    # should judge teams on this season's strength.
    p.add_argument("--five-year", action="store_true",
                   help="also require five-year avg > min rating and 2+ seasons "
                        "(the all-time Greatest Games standard)")
    return p.parse_args()


def having_clause(min_rating, five_year):
    parts = [f"r.CR > {min_rating:.2f}"]
    if five_year:
        parts.append(f"(r.CR + ISNULL(SUM(h.CR), 0)) / (1 + COUNT(h.Season)) > {min_rating:.2f}")
        parts.append("1 + COUNT(h.Season) >= 2")
    return "\n       AND ".join(parts)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    start = date.fromisoformat(args.start) if args.start else date.today()
    end = date.fromisoformat(args.end) if args.end else start + timedelta(days=6)

    print("=" * 60)
    print("Upcoming Games JSON Generator")
    print(f"Target: {OUTPUT_FILE}")
    print(f"Game dates: {start} to {end}")
    print("=" * 60)

    try:
        conn = pyodbc.connect(CONNECTION_STRING, timeout=30)
        cur = conn.cursor()
    except Exception as e:
        print(f"ERROR: Could not connect: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        season, week = cur.execute(SQL_LATEST).fetchone()
        hfa = HOME_FIELD_PTS
        print(f"Ratings: season {season}, week {week} | home-field adjustment {hfa:.2f}")

        sql_games = SQL_GAMES.replace("{having}", having_clause(args.min_rating, args.five_year))
        print(f"Elite filter: rating > {args.min_rating:g}"
              + (f", five-year avg > {args.min_rating:g}, 2+ seasons" if args.five_year else ""))
        rows = cur.execute(sql_games, season, week, season, season, season,
                           start.isoformat(), end.isoformat()).fetchall()
        print(f"Games between two qualifying teams in the window: {len(rows)}")

        records = {r.Team: (int(r.W), int(r.L), int(r.T))
                   for r in cur.execute(SQL_RECORDS, season, season).fetchall()}
    except Exception as e:
        print(f"ERROR: Query failed: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)
    conn.close()

    games = []
    for r in rows:
        home_cr, vis_cr = float(r.Home_CR), float(r.Visitor_CR)
        # Combined Rating gap back to points (ratings are on a 1:1 point scale,
        # regression slope 1.00), plus home field. Positive = home favored.
        projected = (home_cr - vis_cr) / COMBINED_PER_POINT + hfa
        mult = multiplier(abs(projected))
        if mult == 0:
            continue
        favorite = r.Home if projected >= 0 else r.Visitor
        games.append({
            "game_id":          r.GameID,
            "game_date":        r.GameDate.isoformat(),
            "game_time":        str(r.GameTime) if r.GameTime else None,
            "home_team":        r.Home,
            "visitor_team":     r.Visitor,
            "home_rating":      round(home_cr, 2),
            "visitor_rating":   round(vis_cr, 2),
            "home_rank":        int(r.Home_Rank),
            "visitor_rank":     int(r.Visitor_Rank),
            "home_record":      record_str(records.get(r.Home)),
            "visitor_record":   record_str(records.get(r.Visitor)),
            "projected_margin": round(abs(projected), 1),
            "favorite":         favorite,
            "index_raw":        round((home_cr + vis_cr) * mult, 4),
        })

    print(f"Of those, projected within 8 points: {len(games)}")
    games.sort(key=lambda g: g["index_raw"], reverse=True)
    games = games[:TOP_N]
    max_raw = games[0]["index_raw"] if games else 1.0
    for i, g in enumerate(games, 1):
        g["rank"] = i
        g["index_normalised"] = round(g["index_raw"] / max_raw * 100.0, 2) if max_raw else 0.0

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output = {
        "metadata": {
            "timestamp":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":          "upcoming-games",
            "season":        int(season),
            "ratings_week":  int(week),
            "window_start":  start.isoformat(),
            "window_end":    end.isoformat(),
            "home_field_adv": round(hfa, 2),
            "total_items":   len(games),
            "top_n":         TOP_N,
            "description": (
                f"Top {TOP_N} upcoming games between elite programs, ranked by a Game "
                "Index: both teams' Combined Ratings added together, weighted by how "
                "close the projected margin is (8 points or fewer)."
            ),
        },
        "items": games,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUTPUT_FILE}")
    if games:
        top = games[0]
        print(f"  {len(games)} games | #1: {top['visitor_team']} at {top['home_team']} "
              f"({top['game_date']}, {top['favorite']} by {top['projected_margin']})")
    else:
        print("  No qualifying games in this window.")
    print("Done.")


if __name__ == "__main__":
    main()
