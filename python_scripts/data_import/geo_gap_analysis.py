"""
geo_gap_analysis.py
===================================================================
Geographic coverage-gap analysis for the HS_Scores database.

PURPOSE
-------
Find WHERE and WHEN game-score collection is thin, so newspaper-OCR
effort can be aimed at the highest-ROI markets/eras. Works state-by-
state in time blocks (default 10 yr). READ-ONLY: writes CSVs + an
interactive map; persists nothing back to SQL.

CORE IDEA (see conversation notes)
----------------------------------
We measure in TEAM-APPEARANCES, not games: each game contributes one
appearance to EACH of its two teams. Per (cluster, block) we derive
"appearances per active team" -- a metric that is ~schedule-length
(8-10) regardless of era or how many schools existed, so it separates
a genuine collection gap (low appearances/team) from genuine historical
absence (few teams ever existed).

THREE DATA CATEGORIES (geocoding is a WIP, so we never hide this):
  1. Geocoded appearances        -> clustered + measured
  2. Un-geocoded appearances     -> counted as a coverage caveat (pct_geocoded)
  3. Names not in HS_Team_Names  -> reported as an unmatched-names list (alias work)

USAGE
-----
    cd C:\\Users\\demck\\OneDrive\\Football_2024\\static-football-rankings\\python_scripts\\data_import
    # activate venv first
    python geo_gap_analysis.py --state CA --block-size 10 --start 1940 --end 2003
    python geo_gap_analysis.py --state CA --discover     # add HDBSCAN discovery layer

DEPENDENCIES
------------
    pip install pandas numpy pyodbc plotly scikit-learn
    # optional (discovery layer): pip install hdbscan
"""

import argparse
import os
import sys
import math
import datetime as dt

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG  -- mirrors your other scripts (geo_locator.py, pull_sheets_to_sql.py)
# ---------------------------------------------------------------------------
CONN_STR = (
    r"DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=McKnights-PC\SQLEXPRESS01;"
    r"DATABASE=hs_football_database;"
    r"Trusted_Connection=yes;"
)

# Baseline window: post-MaxPreps, pre-Canadian-scores -- your "known complete" era.
BASELINE_START = 2004
BASELINE_END = 2011

# Earth radius (km) for haversine.
EARTH_KM = 6371.0088

# Default named newspaper markets per state. Each team is snapped to the
# NEAREST of these (a Voronoi assignment) -> maps directly to "which paper".
# CA list expanded past your hand list: Fresno, Stockton/Modesto, Inland
# Empire, far-north markets were missing. Edit freely; (lat, lon).
NAMED_MARKETS = {
    "CA": {
        "San Diego":       (32.7157, -117.1611),
        "Los Angeles":     (34.0522, -118.2437),
        "Inland Empire":   (34.0556, -117.1825),   # Riverside/San Bernardino
        "Bakersfield":     (35.3733, -119.0187),
        "Salinas":         (36.6777, -121.6555),
        "Fresno":          (36.7378, -119.7871),
        "San Jose":        (37.3382, -121.8863),
        "San Francisco":   (37.7749, -122.4194),
        "Stockton":        (37.9577, -121.2908),
        "Sacramento":      (38.5816, -121.4944),
        "Redding":         (40.5865, -122.3917),   # far north
        "Eureka":          (40.8021, -124.1637),   # north coast
    },
    # Add other states' market dicts here as you expand (TX, NE priority).
}

OUT_DIR = os.path.join(os.getcwd(), "geo_gap_output")


# ---------------------------------------------------------------------------
# 1. DATA PULL  (read-only)
# ---------------------------------------------------------------------------
def pull_scores(state, start, end):
    """
    Return a DataFrame of one row per (game, side) -- i.e. team-APPEARANCES --
    for the given state across [start, baseline_end]. We pull the baseline
    window too so each cluster can use its OWN baseline appearances/team.

    A game qualifies for the state if EITHER side's team-name ends in (ST).
    We then keep only the appearances belonging to that state's teams, so a
    cross-state game contributes only its in-state side.
    """
    import pyodbc

    state_tag = f"%({state})"  # matches "... (CA)"

    # One row per side. Latitude/Longitude may be NULL (geocoding WIP) and
    # tn.ID may be NULL (name not yet in HS_Team_Names -> alias work).
    query = f"""
    WITH game_sides AS (
        SELECT s.ID AS game_id, s.Season, s.Date AS game_date, s.Home AS team_name
        FROM dbo.HS_Scores s
        WHERE (s.Future_Game = 0 OR s.Future_Game IS NULL)
          AND s.Season BETWEEN ? AND ?
          AND s.Home LIKE ?
        UNION ALL
        SELECT s.ID AS game_id, s.Season, s.Date AS game_date, s.Visitor AS team_name
        FROM dbo.HS_Scores s
        WHERE (s.Future_Game = 0 OR s.Future_Game IS NULL)
          AND s.Season BETWEEN ? AND ?
          AND s.Visitor LIKE ?
    )
    SELECT g.game_id,
           g.Season,
           g.game_date,
           g.team_name,
           tn.ID        AS team_id,
           tn.Latitude  AS lat,
           tn.Longitude AS lon
    FROM game_sides g
    LEFT JOIN dbo.HS_Team_Names tn
           ON tn.Team_Name = g.team_name
    """

    # NOTE: explicit NULL handling on Future_Game above -- SQL Server silently
    # excludes NULLs from comparisons, so "= 0 OR IS NULL" is required.
    pull_end = max(end, BASELINE_END)
    params = [start, pull_end, state_tag, start, pull_end, state_tag]

    print(f"Connecting to SQL Server... (state={state}, {start}-{pull_end})")
    with pyodbc.connect(CONN_STR) as conn:
        df = pd.read_sql(query, conn, params=params)

    print(f"  Pulled {len(df):,} team-appearances "
          f"({df['game_id'].nunique():,} distinct games).")
    return df


# ---------------------------------------------------------------------------
# 2. CLUSTERING
# ---------------------------------------------------------------------------
def assign_named_markets(df_geo, markets):
    """
    Snap each geocoded appearance to the NEAREST named market (Voronoi),
    using haversine distance so we don't get the lat/lon east-west stretch.
    Clusters ONCE over pooled points -- geography is stable, so cluster IDs
    stay comparable across seasons. Returns df with 'cluster' + 'dist_km'.
    """
    names = list(markets.keys())
    m_lat = np.radians(np.array([markets[n][0] for n in names]))
    m_lon = np.radians(np.array([markets[n][1] for n in names]))

    t_lat = np.radians(df_geo["lat"].to_numpy(dtype=float))
    t_lon = np.radians(df_geo["lon"].to_numpy(dtype=float))

    # Vectorised haversine: teams (rows) x markets (cols).
    dlat = t_lat[:, None] - m_lat[None, :]
    dlon = t_lon[:, None] - m_lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(t_lat)[:, None] * np.cos(m_lat)[None, :] * np.sin(dlon / 2) ** 2
    dist_km = 2 * EARTH_KM * np.arcsin(np.sqrt(a))

    idx = np.argmin(dist_km, axis=1)
    out = df_geo.copy()
    out["cluster"] = [names[i] for i in idx]
    out["dist_km"] = dist_km[np.arange(len(idx)), idx]
    return out


def discover_clusters(df_geo, eps_km=40.0, min_samples=5):
    """
    OPTIONAL discovery layer. Runs HDBSCAN (fallback DBSCAN) once over the
    pooled UNIQUE team locations using haversine, to surface density centers
    your named-market list may be missing. Prints centroids; does NOT change
    the actionable assignment. Run with --discover.
    """
    pts = (df_geo[["team_name", "lat", "lon"]]
           .dropna()
           .drop_duplicates("team_name"))
    coords = np.radians(pts[["lat", "lon"]].to_numpy(dtype=float))
    eps_rad = eps_km / EARTH_KM

    labels = None
    try:
        import hdbscan
        clu = hdbscan.HDBSCAN(min_cluster_size=min_samples, metric="haversine")
        labels = clu.fit_predict(coords)
        algo = "HDBSCAN"
    except ImportError:
        from sklearn.cluster import DBSCAN
        clu = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine")
        labels = clu.fit_predict(coords)
        algo = "DBSCAN (hdbscan not installed)"

    pts = pts.assign(label=labels)
    print(f"\n--- DISCOVERY LAYER ({algo}) ---")
    n_noise = int((labels == -1).sum())
    print(f"  {pts['label'].nunique() - (1 if n_noise else 0)} density clusters, "
          f"{n_noise} noise points.")
    for lab, grp in pts[pts.label != -1].groupby("label"):
        print(f"  cluster {lab:>3}: n={len(grp):>4}  "
              f"centroid=({grp.lat.mean():.3f}, {grp.lon.mean():.3f})  "
              f"e.g. {', '.join(grp.team_name.head(3))}")
    print("  -> Compare these centroids to NAMED_MARKETS; add any you're missing.\n")
    return pts


# ---------------------------------------------------------------------------
# 3. METRICS
# ---------------------------------------------------------------------------
def block_label(season, block_size, start):
    """Return the inclusive block label, e.g. '1940-1949'."""
    offset = (season - start) // block_size
    b0 = start + offset * block_size
    b1 = b0 + block_size - 1
    return f"{b0}-{b1}"


def compute_metrics(df_assigned, block_size, start, end):
    """
    Build the per-(cluster, block) gap table.

    EVERYTHING IS PER-SEASON. A team plays ~9 games/season, so each team
    accrues ~9 APPEARANCES per season at full coverage -- i.e. per-season
    appearances/active-team lands near schedule length REGARDLESS of era or
    block length. This is what makes blocks of different lengths (and partial
    final blocks) comparable, and it's the normalization the first version
    dropped (it summed appearances over whole windows, so "expected" came out
    ~74 = 9 x 8 baseline-years instead of ~9).

    Per (cluster, season):
        apt_s = appearances_s / active_teams_s          (~9 when complete)
    expected_apt : baseline (2004-2011) mean of apt_s for that cluster.
                   Mean-of-per-season (not total/total) so the union-of-teams
                   inflation across years doesn't depress it.
    Block-level:
        actual_apt        = sum(appearances_s) / sum(active_teams_s)   (per-season)
        est_missing        = SUM over seasons [ teams_s * max(expected_apt - apt_s, 0) ]
        completeness       = appearances / (appearances + est_missing)   (0..1)
        est_missing_per_season = est_missing / intended_seasons  (fair cross-block compare)

    NOTE: est_missing only counts seasons that have >=1 game. A season with
    ZERO collected games contributes nothing here -- detecting a wholly-absent
    season is the separate "roster gap" / temporal-anomaly problem (imputing an
    expected team count for an absent season is the hard denominator I flagged).
    """
    df = df_assigned.copy()

    # --- per (cluster, season) appearances & active teams ---
    cs = (df.groupby(["cluster", "Season"])
            .agg(apps=("game_id", "size"),
                 teams=("team_name", "nunique"))
            .reset_index())
    cs["apt"] = cs["apps"] / cs["teams"].replace(0, np.nan)

    # --- expected per-season rate per cluster (baseline mean of apt_s) ---
    base = cs[(cs.Season >= BASELINE_START) & (cs.Season <= BASELINE_END)]
    base_g = (base.groupby("cluster")
                  .agg(expected_apt=("apt", "mean"),
                       baseline_seasons=("Season", "nunique"),
                       baseline_peak_teams=("teams", "max")))

    # --- historical seasons, tagged to blocks ---
    hist = cs[(cs.Season >= start) & (cs.Season <= end)].copy()
    hist["block"] = hist["Season"].apply(lambda s: block_label(s, block_size, start))
    hist = hist.merge(base_g[["expected_apt"]], on="cluster", how="left")

    # per-season missing appearances
    hist["missing_s"] = (hist["teams"] *
                         (hist["expected_apt"] - hist["apt"]).clip(lower=0))

    grp = (hist.groupby(["cluster", "block"])
               .agg(appearances=("apps", "sum"),
                    team_seasons=("teams", "sum"),
                    peak_teams=("teams", "max"),
                    seasons_present=("Season", "nunique"),
                    est_missing_appearances=("missing_s", "sum"),
                    expected_apt=("expected_apt", "first"))
               .reset_index())

    # intended season span of each block within [start, end]
    def intended(block):
        b0 = int(block.split("-")[0])
        b1 = min(b0 + block_size - 1, end)
        return b1 - max(b0, start) + 1
    grp["intended_seasons"] = grp["block"].apply(intended)

    grp["actual_apt"] = grp["appearances"] / grp["team_seasons"].replace(0, np.nan)
    grp["completeness"] = (grp["appearances"] /
                           (grp["appearances"] + grp["est_missing_appearances"]))
    # pct_new = expected fraction of a representative paper's games that are NOT
    # already in the DB == your per-scan yield == 1 - duplicate_rate.
    grp["pct_new"] = (1 - grp["completeness"])
    grp["est_missing_appearances"] = grp["est_missing_appearances"].round(0)
    grp["est_missing_per_season"] = (grp["est_missing_appearances"] /
                                     grp["intended_seasons"]).round(0)

    cols = ["cluster", "block", "appearances", "peak_teams",
            "seasons_present", "intended_seasons",
            "expected_apt", "actual_apt", "completeness", "pct_new",
            "est_missing_appearances", "est_missing_per_season"]
    grp = grp[cols].sort_values("est_missing_appearances", ascending=False)
    grp[["expected_apt", "actual_apt", "completeness", "pct_new"]] = \
        grp[["expected_apt", "actual_apt", "completeness", "pct_new"]].round(2)
    return grp, base_g


def coverage_caveats(df_all, df_assigned, block_size, start, end):
    """
    Per (state-block) honesty report:
      pct_geocoded   = geocoded appearances / total matched appearances
      unmatched_pct  = appearances with no HS_Team_Names row (alias work)
    A gap table is only trustworthy where pct_geocoded is high.
    """
    d = df_all[(df_all.Season >= start) & (df_all.Season <= end)].copy()
    d["block"] = d["Season"].apply(lambda s: block_label(s, block_size, start))
    d["is_geocoded"] = d["lat"].notna() & d["lon"].notna()
    d["is_unmatched"] = d["team_id"].isna()

    cov = (d.groupby("block")
             .agg(total_appearances=("game_id", "size"),
                  geocoded=("is_geocoded", "sum"),
                  unmatched=("is_unmatched", "sum"))
             .reset_index())
    cov["pct_geocoded"] = (100 * cov["geocoded"] / cov["total_appearances"]).round(1)
    cov["pct_unmatched"] = (100 * cov["unmatched"] / cov["total_appearances"]).round(1)
    return cov


# ---------------------------------------------------------------------------
# 3b. DUPLICATE-RATE PROBE  (de-blinds your newspapers.com visual inspection)
# ---------------------------------------------------------------------------
def probe_season(df_assigned, cluster, season, top_n=15):
    """
    For a (cluster, season): print the games you ALREADY hold, broken out by
    date, busiest dates first. You pick one of these dates to inspect on
    newspapers.com; the count tells you how many you already have for that
    weekend, so paper_count - held_count is your floor on NEW games for that
    date. Use --probe-date to get the exact matchups to tick off.
    """
    d = df_assigned[(df_assigned.cluster == cluster) & (df_assigned.Season == season)]
    games = d.drop_duplicates("game_id")
    if games.empty:
        print(f"\n[PROBE] {cluster} {season}: no games currently held.")
        return

    by_date = (games.groupby("game_date").size()
                    .sort_values(ascending=False)
                    .rename("held_games").reset_index())
    print(f"\n[PROBE] {cluster} {season}: {len(games)} games currently held "
          f"across {by_date.shape[0]} dates.")
    print("  Busiest dates already in the DB (inspect one of these on newspapers.com;")
    print("  any matchup in the paper NOT counted here is a NEW game):")
    print(by_date.head(top_n).to_string(index=False))
    print("  -> For a chosen date, re-run with --probe-date YYYY-MM-DD "
          "to list the exact held matchups.")


def probe_date(state, cluster_team_names, probe_date_str):
    """
    Dump the EXACT held matchups for the cluster's teams on a specific date,
    pulled straight from HS_Scores (read-only). Open the paper to this date and
    every game NOT on this list is a new game. This is the measured (not
    guessed) duplicate check.
    """
    import pyodbc

    if not cluster_team_names:
        print(f"\n[PROBE-DATE] No teams for that cluster; nothing to check.")
        return

    # Build a parameterized IN-list over the cluster's team names (covers both
    # Home and Visitor sides).
    placeholders = ",".join("?" for _ in cluster_team_names)
    q = f"""
        SELECT s.Date, s.Home, s.Visitor, s.Home_Score, s.Visitor_Score, s.Source
        FROM dbo.HS_Scores s
        WHERE s.Date = ?
          AND ( s.Home IN ({placeholders}) OR s.Visitor IN ({placeholders}) )
        ORDER BY s.Home
    """
    params = [probe_date_str] + list(cluster_team_names) + list(cluster_team_names)
    with pyodbc.connect(CONN_STR) as conn:
        held = pd.read_sql(q, conn, params=params)

    print(f"\n[PROBE-DATE] {probe_date_str}: {len(held)} games already held "
          f"for this cluster's teams.")
    if held.empty:
        print("  Nothing held for this date -> every game in the paper is NEW.")
        return
    for _, r in held.iterrows():
        src = f"  [{r.Source}]" if pd.notna(r.Source) else ""
        print(f"  {r.Home} {int(r.Home_Score) if pd.notna(r.Home_Score) else '?'}"
              f" - {int(r.Visitor_Score) if pd.notna(r.Visitor_Score) else '?'} "
              f"{r.Visitor}{src}")
    print("  -> Open the paper to this date; any matchup above = duplicate, "
          "anything else = new.")


# ---------------------------------------------------------------------------
# 4. MAP  (faceted small-multiples, one per block)
# ---------------------------------------------------------------------------
def build_map(grp, markets, state, out_html):
    """
    Faceted scatter_geo: one facet per block, bubbles sized by
    est_missing_appearances, colored by intensity_completeness. This is the
    artifact you stare at to pick the next newspaper target.
    """
    import plotly.express as px

    g = grp.copy()
    g["lat"] = g["cluster"].map(lambda c: markets[c][0])
    g["lon"] = g["cluster"].map(lambda c: markets[c][1])
    g = g[g["est_missing_appearances"] > 0]
    if g.empty:
        print("  (No positive-gap rows to map.)")
        return

    fig = px.scatter_geo(
        g, lat="lat", lon="lon",
        size="est_missing_appearances",
        color="completeness",
        color_continuous_scale="RdYlGn",
        range_color=(0, 1),
        facet_col="block", facet_col_wrap=3,
        hover_name="cluster",
        hover_data={"appearances": True, "peak_teams": True,
                    "actual_apt": ":.1f", "expected_apt": ":.1f",
                    "completeness": ":.0%",
                    "est_missing_appearances": ":.0f",
                    "lat": False, "lon": False},
        scope="usa",
        title=f"{state}: estimated missing team-appearances by market & era "
              f"(bubble=missing, red=low coverage)",
    )
    fig.update_geos(fitbounds="locations", visible=True)
    fig.write_html(out_html)
    print(f"  Map written: {out_html}")


# ---------------------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Geographic coverage-gap analysis for HS_Scores.")
    ap.add_argument("--state", required=True, help="State code, e.g. CA")
    ap.add_argument("--block-size", type=int, default=10, help="Years per block (5 or 10).")
    ap.add_argument("--start", type=int, default=1940)
    ap.add_argument("--end", type=int, default=2003)
    ap.add_argument("--discover", action="store_true",
                    help="Run HDBSCAN discovery layer to find missing markets.")
    ap.add_argument("--probe-cluster", default=None,
                    help="Cluster/market name to probe for duplicate rate, e.g. \"Los Angeles\".")
    ap.add_argument("--probe-season", type=int, default=None,
                    help="Season to probe (with --probe-cluster).")
    ap.add_argument("--probe-date", default=None,
                    help="Specific date YYYY-MM-DD to dump exact held matchups (with --probe-cluster).")
    args = ap.parse_args()

    state = args.state.upper()
    if state not in NAMED_MARKETS:
        sys.exit(f"No NAMED_MARKETS defined for {state}. Add a market dict and re-run.")
    markets = NAMED_MARKETS[state]

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- pull ---
    df_all = pull_scores(state, args.start, args.end)
    if df_all.empty:
        sys.exit("No rows returned. Check state code / season range.")

    # --- split the three categories ---
    df_geo = df_all[df_all["lat"].notna() & df_all["lon"].notna()].copy()
    n_ungeo = int((df_all["lat"].isna()).sum())
    n_unmatched = int(df_all["team_id"].isna().sum())
    print(f"  Geocoded: {len(df_geo):,} | un-geocoded: {n_ungeo:,} | "
          f"unmatched-name: {n_unmatched:,}")

    # --- discovery (optional, doesn't affect actionable assignment) ---
    if args.discover:
        discover_clusters(df_geo)

    # --- actionable clustering + metrics ---
    df_assigned = assign_named_markets(df_geo, markets)
    grp, base_g = compute_metrics(df_assigned, args.block_size, args.start, args.end)
    cov = coverage_caveats(df_all, df_assigned, args.block_size, args.start, args.end)

    # --- unmatched names (alias work, separate from geo) ---
    unmatched = (df_all[df_all["team_id"].isna()]
                 .groupby("team_name").size()
                 .sort_values(ascending=False)
                 .rename("appearances").reset_index())

    # --- PREVIEW to console (data-first: look before acting) ---
    pd.set_option("display.max_rows", 40)
    print("\n=== TOP GAPS (by estimated missing team-appearances) ===")
    print(grp.head(25).to_string(index=False))
    print("\n=== COVERAGE CAVEATS (trust gaps only where pct_geocoded is high) ===")
    print(cov.to_string(index=False))
    if not unmatched.empty:
        print(f"\n=== UNMATCHED NAMES (top 15 of {len(unmatched)}; -> alias work) ===")
        print(unmatched.head(15).to_string(index=False))

    # --- write CSVs + map ---
    gap_csv = os.path.join(OUT_DIR, f"{state}_gaps_{stamp}.csv")
    cov_csv = os.path.join(OUT_DIR, f"{state}_coverage_{stamp}.csv")
    unm_csv = os.path.join(OUT_DIR, f"{state}_unmatched_{stamp}.csv")
    map_html = os.path.join(OUT_DIR, f"{state}_gap_map_{stamp}.html")

    grp.to_csv(gap_csv, index=False)
    cov.to_csv(cov_csv, index=False)
    unmatched.to_csv(unm_csv, index=False)
    build_map(grp, markets, state, map_html)

    print(f"\nWrote:\n  {gap_csv}\n  {cov_csv}\n  {unm_csv}")
    print("READ-ONLY: nothing persisted to SQL.")

    # --- duplicate-rate probe (optional) ---
    if args.probe_cluster:
        pc = args.probe_cluster
        if pc not in markets:
            print(f"\n[PROBE] '{pc}' is not a named market. Options: {', '.join(markets)}")
        else:
            if args.probe_season:
                probe_season(df_assigned, pc, args.probe_season)
            if args.probe_date:
                team_names = sorted(df_assigned.loc[df_assigned.cluster == pc,
                                                    "team_name"].unique().tolist())
                probe_date(state, team_names, args.probe_date)
            if not args.probe_season and not args.probe_date:
                print("\n[PROBE] Add --probe-season YYYY (busiest held dates) "
                      "and/or --probe-date YYYY-MM-DD (exact held matchups).")


if __name__ == "__main__":
    main()