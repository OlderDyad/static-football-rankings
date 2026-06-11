"""
newspaper_batch_coverage.py
===================================================================
Per-YEAR newspaper coverage analysis for a fresh import batch.

RUN THIS *BEFORE* dedup (EXEC RemoveDuplicateGamesParameterized), then dedup.
Running it before dedup is the ONLY way to capture which papers overlap (the
backup map). After dedup that information is gone.

For one season + one batch-start date it prints three things:
  1. COMPLETENESS  -- games you had before, net-new this batch, new total.
                      (Did this year close its gap vs the expected curve?)
  2. PER-PAPER NET-NEW -- each paper and how many NEW games it added (games not
                      already in your data), biggest first. Read down to pick
                      your set.
  3. BACKUP MAP    -- pairs of papers that cover the same games (high shared
                      count = interchangeable; one is a backup for the other
                      when print quality is bad).

READ-ONLY: this script only SELECTs. It does not delete or dedup anything.

USAGE
-----
    cd C:\\Users\\demck\\OneDrive\\Football_2024\\static-football-rankings\\python_scripts\\data_import
    python newspaper_batch_coverage.py --season 1966 --batch-after 2026-06-10 --state CA
    # optional: compare against a reference season to see the gap
    python newspaper_batch_coverage.py --season 1966 --batch-after 2026-06-10 --state CA --reference-season 1968

DEPENDENCIES: pandas, pyodbc
"""

import argparse
import sys
import pandas as pd

# Reuse the DB connection string + clustering from the gap script.
from geo_gap_analysis import (
    CONN_STR, BASELINE_START, BASELINE_END, NAMED_MARKETS, assign_named_markets,
)


# ---------------------------------------------------------------------------
# MARKET MODE: "is the Sacramento AREA complete?" (cluster, not paper)
# ---------------------------------------------------------------------------
def _pull_market_rows(conn, state, season_lo, season_hi):
    """One row per team-APPEARANCE (home + visitor) with geo + paper, across the
    season range AND the baseline window (for the expected-per-team denominator)."""
    state_like = f"%({state})"
    lo = min(season_lo, BASELINE_START)
    hi = max(season_hi, BASELINE_END)
    q = """
        WITH sides AS (
            SELECT s.ID AS game_id, s.Season, s.Source, s.Home AS team_name
            FROM dbo.HS_Scores s
            WHERE (s.Future_Game = 0 OR s.Future_Game IS NULL)
              AND s.Season BETWEEN ? AND ? AND s.Home LIKE ?
            UNION ALL
            SELECT s.ID, s.Season, s.Source, s.Visitor
            FROM dbo.HS_Scores s
            WHERE (s.Future_Game = 0 OR s.Future_Game IS NULL)
              AND s.Season BETWEEN ? AND ? AND s.Visitor LIKE ?
        )
        SELECT g.game_id, g.Season, g.Source, g.team_name,
               tn.Latitude AS lat, tn.Longitude AS lon
        FROM sides g
        LEFT JOIN dbo.HS_Team_Names tn ON tn.Team_Name = g.team_name
    """
    params = [lo, hi, state_like, lo, hi, state_like]
    return pd.read_sql(q, conn, params=params)


def market_completeness(conn, state, season_lo, season_hi, only_cluster=None):
    """
    Per (cluster, season): appearances-per-active-team vs the cluster's own
    2004-2011 baseline -> completeness. Answers "is this AREA complete?" for
    each season, independent of which paper would fill it.
    """
    markets = NAMED_MARKETS[state]
    df = _pull_market_rows(conn, state, season_lo, season_hi)
    df = df[df.lat.notna() & df.lon.notna()].copy()
    if df.empty:
        print("\n=== MARKET COMPLETENESS ===\n  No geocoded rows in range.")
        return
    df = assign_named_markets(df, markets)
    if only_cluster:
        df = df[df.cluster == only_cluster]

    # per (cluster, season): appearances / active teams
    cs = (df.groupby(["cluster", "Season"])
            .agg(apps=("game_id", "size"), teams=("team_name", "nunique"))
            .reset_index())
    cs["apt"] = cs["apps"] / cs["teams"].replace(0, 1)

    # expected per-season apt = mean over baseline years, per cluster
    base = cs[(cs.Season >= BASELINE_START) & (cs.Season <= BASELINE_END)]
    expected = base.groupby("cluster")["apt"].mean().rename("expected_apt")

    hist = cs[(cs.Season >= season_lo) & (cs.Season <= season_hi)].merge(
        expected, on="cluster", how="left")
    hist["completeness"] = (hist["apt"] / hist["expected_apt"]).round(2)
    hist = hist[["cluster", "Season", "apps", "teams", "apt",
                 "expected_apt", "completeness"]].sort_values(["cluster", "Season"])

    print("\n=== MARKET COMPLETENESS (is the AREA complete, per season?) ===")
    print("  completeness = this season's games-per-team / the area's 2004-2011 norm.")
    print("  Treat as a GUIDE, not a precise gauge (small per-market counts are noisy).")
    pd.set_option("display.max_rows", 200)
    print(hist.round(2).to_string(index=False))


def paper_within_market(conn, state, season_lo, season_hi, only_cluster=None):
    """
    Within each cluster + season: which papers supplied the games, and how many.
    Answers "which instrument is filling this area, and is it tapped out?"
    (Counts are total games supplied, not net-new -- this is a composition view.)
    """
    markets = NAMED_MARKETS[state]
    df = _pull_market_rows(conn, state, season_lo, season_hi)
    df = df[df.lat.notna() & df.lon.notna()].copy()
    df = df[(df.Season >= season_lo) & (df.Season <= season_hi)]
    if df.empty:
        print("\n=== PAPER WITHIN MARKET ===\n  No rows in range.")
        return
    df = assign_named_markets(df, markets)
    if only_cluster:
        df = df[df.cluster == only_cluster]
    # collapse Source filename -> paper name (cut at the season token is unreliable
    # across many seasons, so cut at first 4-digit year run).
    df["paper"] = df["Source"].astype(str).str.replace(r"_?\d{4}_.*$", "", regex=True).str.slice(0, 40)
    # one row per (cluster, game) so a game counts once per cluster
    g = df.drop_duplicates(["cluster", "game_id"])
    comp = (g.groupby(["cluster", "paper"]).size().rename("games").reset_index()
              .sort_values(["cluster", "games"], ascending=[True, False]))
    print("\n=== PAPER WITHIN MARKET (which instrument fills this area) ===")
    print(comp.to_string(index=False))


# ---------------------------------------------------------------------------
# Original batch-mode paper-name extraction (single season)
# ---------------------------------------------------------------------------
# Source looks like: "The_Sacramento_Bee_1967_10_07_17 (1).csv"
# The paper name is everything BEFORE the "_<season>_" chunk. We cut there so
# every page/date/OCR-variant of the same paper collapses to one name.
def paper_expr(season):
    # SQL expression that extracts the paper name from Source for this season.
    # CHARINDEX finds "_1966_"; LEFT keeps the text before it.
    tag = f"'_{season}_'"
    return (f"LEFT(Source, CASE WHEN CHARINDEX({tag}, Source) > 0 "
            f"THEN CHARINDEX({tag}, Source) - 1 ELSE LEN(Source) END)")


# ---------------------------------------------------------------------------
# 1. COMPLETENESS
# ---------------------------------------------------------------------------
def completeness(conn, season, batch_after, state, reference_season):
    state_like = f"%({state})"
    q = f"""
        SELECT
            SUM(CASE WHEN Date_Added <= ? THEN 1 ELSE 0 END) AS had_before,
            SUM(CASE WHEN Date_Added >  ? THEN 1 ELSE 0 END) AS net_new_this_batch,
            COUNT(*) AS total_now
        FROM dbo.HS_Scores
        WHERE Season = ?
          AND (Home LIKE ? OR Visitor LIKE ?)
    """
    row = pd.read_sql(q, conn, params=[batch_after, batch_after, season,
                                       state_like, state_like]).iloc[0]

    print("\n=== 1. COMPLETENESS ===")
    print(f"  {state} {season}: had {int(row.had_before)} before, "
          f"+{int(row.net_new_this_batch)} new this batch, "
          f"= {int(row.total_now)} now.")

    if reference_season:
        qr = f"""
            SELECT COUNT(*) AS ref_total FROM dbo.HS_Scores
            WHERE Season = ? AND (Home LIKE ? OR Visitor LIKE ?)
        """
        ref = pd.read_sql(qr, conn, params=[reference_season, state_like, state_like]).iloc[0]
        ref_total = int(ref.ref_total)
        # expected ~1.5%/yr falloff from the reference season
        yrs = reference_season - season
        expected = ref_total * (1 - 0.015) ** yrs
        pct = 100 * row.total_now / expected if expected else 0
        print(f"  Reference {reference_season}: {ref_total} games. "
              f"Expected ~{expected:,.0f} for {season} (after ~1.5%/yr falloff).")
        print(f"  {season} is now at {pct:.0f}% of expected "
              f"({'on/above target' if pct >= 98 else 'still short -> add more papers'}).")


# ---------------------------------------------------------------------------
# 2. PER-PAPER NET-NEW
# ---------------------------------------------------------------------------
def per_paper_net_new(conn, season, batch_after, state):
    state_like = f"%({state})"
    pexpr = paper_expr(season)
    q = f"""
        SELECT {pexpr} AS paper, COUNT(*) AS net_new_games
        FROM dbo.HS_Scores
        WHERE Season = ?
          AND (Home LIKE ? OR Visitor LIKE ?)
          AND Date_Added > ?
        GROUP BY {pexpr}
        ORDER BY net_new_games DESC
    """
    df = pd.read_sql(q, conn, params=[season, state_like, state_like, batch_after])
    print("\n=== 2. PER-PAPER NET-NEW (pick papers from the top down) ===")
    if df.empty:
        print("  No new rows for this batch. Check --batch-after date.")
    else:
        print(df.to_string(index=False))
        print(f"  Total new games this batch: {int(df.net_new_games.sum())}")
    return df


# ---------------------------------------------------------------------------
# 3. BACKUP MAP  (only meaningful BEFORE dedup)
# ---------------------------------------------------------------------------
def backup_map(conn, season, batch_after, state, min_shared=5):
    """
    For the new batch, build an unordered game key (date + sorted team pair) so
    a flipped Home/Visitor counts as the same game. Then count, for each pair of
    papers, how many games they BOTH carried. High shared count = the two papers
    cover the same teams = backups for each other.
    """
    state_like = f"%({state})"
    pexpr = paper_expr(season)
    # Pull the batch rows with paper + an unordered game key.
    q = f"""
        SELECT {pexpr} AS paper,
               CAST(Date AS DATE) AS d,
               CASE WHEN Home < Visitor THEN Home ELSE Visitor END AS team_a,
               CASE WHEN Home < Visitor THEN Visitor ELSE Home END AS team_b
        FROM dbo.HS_Scores
        WHERE Season = ?
          AND (Home LIKE ? OR Visitor LIKE ?)
          AND Date_Added > ?
    """
    df = pd.read_sql(q, conn, params=[season, state_like, state_like, batch_after])
    print("\n=== 3. BACKUP MAP (papers covering the same games) ===")
    if df.empty:
        print("  No batch rows.")
        return
    df["game_key"] = df["d"].astype(str) + "|" + df["team_a"] + "|" + df["team_b"]

    # For each game, which papers carried it? Then count co-occurrences.
    from itertools import combinations
    from collections import Counter
    pair_counts = Counter()
    for _, grp in df.groupby("game_key"):
        papers = sorted(grp["paper"].unique())
        for a, b in combinations(papers, 2):
            pair_counts[(a, b)] += 1

    if not pair_counts:
        print("  No two papers shared a game (no overlap detected).")
        return
    rows = [{"paper_a": a, "paper_b": b, "shared_games": n}
            for (a, b), n in pair_counts.items() if n >= min_shared]
    if not rows:
        print(f"  No paper pair shared >= {min_shared} games "
              f"(little overlap; few natural backups).")
        return
    out = pd.DataFrame(rows).sort_values("shared_games", ascending=False)
    print(out.to_string(index=False))
    print("  -> High shared_games = interchangeable papers (one backs up the other).")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Newspaper coverage analysis. Two modes:\n"
                    "  BATCH  (default): one season, all papers, net-new + backup map (run BEFORE dedup).\n"
                    "  MARKET (--market): is an AREA complete across a season range, and which papers fill it.")
    ap.add_argument("--season", type=int, help="BATCH mode: the season just imported.")
    ap.add_argument("--batch-after",
                    help="BATCH mode: Date_Added cutoff for this batch, e.g. 2026-06-10.")
    ap.add_argument("--state", default="CA")
    ap.add_argument("--reference-season", type=int, default=None,
                    help="BATCH mode: a known-complete season to gauge the gap (e.g. 1968).")
    # market mode
    ap.add_argument("--market", action="store_true",
                    help="MARKET mode: ask 'is this AREA complete?' across a season range.")
    ap.add_argument("--cluster", default=None,
                    help="MARKET mode: limit to one market, e.g. \"Sacramento\" (default: all).")
    ap.add_argument("--season-range", type=int, nargs=2, metavar=("LO", "HI"),
                    help="MARKET mode: season range, e.g. --season-range 1958 1968.")
    args = ap.parse_args()

    import pyodbc

    if args.market:
        if not args.season_range:
            ap.error("--market requires --season-range LO HI")
        lo, hi = args.season_range
        if args.state.upper() not in NAMED_MARKETS:
            sys.exit(f"No NAMED_MARKETS for {args.state.upper()} in geo_gap_analysis.py.")
        print(f"Connecting... MARKET mode (state={args.state.upper()}, {lo}-{hi}"
              f"{', cluster=' + args.cluster if args.cluster else ''})")
        with pyodbc.connect(CONN_STR) as conn:
            market_completeness(conn, args.state.upper(), lo, hi, args.cluster)
            paper_within_market(conn, args.state.upper(), lo, hi, args.cluster)
        print("\nREAD-ONLY.")
        return

    # BATCH mode (default)
    if args.season is None or args.batch_after is None:
        ap.error("BATCH mode requires --season and --batch-after "
                 "(or use --market with --season-range).")
    print(f"Connecting... (season={args.season}, state={args.state}, "
          f"batch added after {args.batch_after})")
    print("REMINDER: run this BEFORE EXEC RemoveDuplicateGamesParameterized, "
          "or the backup map will be empty.")
    with pyodbc.connect(CONN_STR) as conn:
        completeness(conn, args.season, args.batch_after, args.state.upper(),
                     args.reference_season)
        per_paper_net_new(conn, args.season, args.batch_after, args.state.upper())
        backup_map(conn, args.season, args.batch_after, args.state.upper())
    print("\nREAD-ONLY: nothing changed in the database. "
          "Now you can run the dedup.")


if __name__ == "__main__":
    main()