"""
source_history.py
===================================================================
Collection-REGIME mapping for the HS_Scores database. Answers:
  1. WHAT sources make up each market/era (yearbook vs newspaper vs MaxPreps)?
  2. WHEN did newspaper sourcing switch on, per market? (the ~1959/60 question)
  3. WHEN does each team first appear in the data (first-appearance cliff)?

IMPORTANT FRAMING (per project scope)
-------------------------------------
This script is DESCRIPTIVE, not prescriptive. "Yearbook-only" or "no newspaper
source" is NOT flagged as a gap: for many school/era combinations a yearbook or
MaxPreps is the best or ONLY source, and the project deliberately concentrates
on the biggest programs (rating-site priority). The tool surfaces source
composition so YOU can judge whether a cell is "worth a newspaper pass" or
"already as complete as feasible". It cannot distinguish a deliberately
yearbook-only big school from an uncovered small one -- no enrollment data
exists for that. It only shows the mix.

Shares clustering + market definitions with geo_gap_analysis.py (single source
of truth). READ-ONLY: writes CSVs (+ optional chart); persists nothing.

USAGE
-----
    cd C:\\Users\\demck\\OneDrive\\Football_2024\\static-football-rankings\\python_scripts\\data_import
    python source_history.py --state CA --block-size 5
    python source_history.py --state CA --inventory-only   # just dump Source types

DEPENDENCIES: pandas, numpy, pyodbc (+ plotly optional)
"""

import argparse
import os
import re
import sys
import datetime as dt

import numpy as np
import pandas as pd

# Reuse config + clustering from the gap script (same directory).
from geo_gap_analysis import (
    CONN_STR, BASELINE_START, BASELINE_END, NAMED_MARKETS,
    assign_named_markets, block_label, OUT_DIR,
)

# ---------------------------------------------------------------------------
# SOURCE CLASSIFICATION  -- EDIT THESE RULES to match your Source conventions.
# Ordered: FIRST MATCH WINS (so put specific rules before generic ones).
# Anything unmatched -> 'other' (NOT assumed to be a newspaper; excluded from
# the newspaper-onset share). Verify the 'other' bucket via --inventory-only.
#
# GENERAL rules (apply to any state): yearbook, maxpreps, newspaper(=newspapers.com),
#   lonestar, wikipedia, generic school sites.
# STATE-SPECIFIC compiled/secondary sources (add your own per state as you go):
#   CA -> calpreps, partleton, askeland, cif_records.
# Compiled/secondary sources (aggregators, private collections, record books)
# are kept as their OWN buckets, NOT folded into 'newspaper', because they are
# prior research rather than date-by-date primaries.
# ---------------------------------------------------------------------------
SOURCE_RULES = [
    # --- general ---
    ("yearbook",    re.compile(r"classmates\.com|yearbook", re.I)),
    ("maxpreps",    re.compile(r"maxpreps", re.I)),
    ("newspaper",   re.compile(r"newspapers\.com", re.I)),      # primary (hand-typed or OCR)
    ("lonestar",    re.compile(r"lonestar", re.I)),
    ("wikipedia",   re.compile(r"wikipedia|wiki", re.I)),
    # --- CA-specific compiled/secondary (move/extend per state) ---
    ("calpreps",    re.compile(r"calpreps", re.I)),
    ("partleton",   re.compile(r"partletonsports", re.I)),
    ("askeland",    re.compile(r"Askeland", re.I)),
    ("cif_records", re.compile(r"cifccs\.org|cifncs\.org|beasport|cif.*history", re.I)),
    # --- generic school/program sites (LAST: loosest pattern, catches leftovers) ---
    # NOTE: this is deliberately broad; check it against --inventory-only output
    # and tighten if it grabs something it shouldn't.
    ("school_site", re.compile(r"\.k12\.|materdei|sangerhigh|bmhs-la|thswarriors|garces|\.org/", re.I)),
]
# Only these count as "newspaper" for the onset analysis. Compiled secondary
# sources and 'other' are intentionally excluded.
NEWSPAPER_LIKE = {"newspaper"}


def classify_source(src):
    if src is None or (isinstance(src, float) and np.isnan(src)):
        return "unknown"
    for label, rx in SOURCE_RULES:
        if rx.search(str(src)):
            return label
    return "other"


# ---------------------------------------------------------------------------
# DATA PULL  (read-only) -- one row per team-APPEARANCE, carrying Source.
# ---------------------------------------------------------------------------
def pull_with_source(state, start, end):
    import pyodbc
    state_tag = f"%({state})"
    pull_end = max(end, BASELINE_END)
    query = f"""
    WITH game_sides AS (
        SELECT s.ID AS game_id, s.Season, s.Source, s.Home AS team_name
        FROM dbo.HS_Scores s
        WHERE (s.Future_Game = 0 OR s.Future_Game IS NULL)
          AND s.Season BETWEEN ? AND ? AND s.Home LIKE ?
        UNION ALL
        SELECT s.ID AS game_id, s.Season, s.Source, s.Visitor AS team_name
        FROM dbo.HS_Scores s
        WHERE (s.Future_Game = 0 OR s.Future_Game IS NULL)
          AND s.Season BETWEEN ? AND ? AND s.Visitor LIKE ?
    )
    SELECT g.game_id, g.Season, g.Source, g.team_name,
           tn.ID AS team_id, tn.Latitude AS lat, tn.Longitude AS lon
    FROM game_sides g
    LEFT JOIN dbo.HS_Team_Names tn ON tn.Team_Name = g.team_name
    """
    params = [start, pull_end, state_tag, start, pull_end, state_tag]
    print(f"Connecting to SQL Server... (state={state}, {start}-{pull_end})")
    with pyodbc.connect(CONN_STR) as conn:
        df = pd.read_sql(query, conn, params=params)
    df["src_type"] = df["Source"].apply(classify_source)
    print(f"  Pulled {len(df):,} appearances ({df['game_id'].nunique():,} games).")
    return df


# ---------------------------------------------------------------------------
# 1. SOURCE INVENTORY  (data-first verification: SEE what's there)
# ---------------------------------------------------------------------------
def source_inventory(df):
    games = df.drop_duplicates("game_id")
    by_type = (games.groupby("src_type").size()
                    .sort_values(ascending=False)
                    .rename("games").reset_index())
    by_type["pct"] = (100 * by_type["games"] / by_type["games"].sum()).round(1)

    # also show the most common raw Source prefixes within the catch-all bucket,
    # so you can confirm what 'other' contains and add rules to reclassify it.
    other = games[games.src_type == "other"].copy()
    other["prefix"] = (other["Source"].astype(str)
                       .str.replace(r"\s*\d.*$", "", regex=True)   # strip trailing dates
                       .str.slice(0, 40))
    top_other = (other.groupby("prefix").size()
                      .sort_values(ascending=False).head(20)
                      .rename("games").reset_index())
    return by_type, top_other


# ---------------------------------------------------------------------------
# 2. SOURCE MIX BY BLOCK + NEWSPAPER ONSET  (the ~1959/60 question)
# ---------------------------------------------------------------------------
def source_mix(df_assigned, block_size, start, end):
    """
    Per (cluster, block): game counts by source type and the newspaper SHARE.
    'onset' = first block where newspaper share exceeds ONSET_THRESHOLD -- the
    market's switch from yearbook-era to newspaper-era collection.
    """
    ONSET_THRESHOLD = 0.25  # >25% of a block's games newspaper-sourced = "switched on"

    d = df_assigned[(df_assigned.Season >= start) & (df_assigned.Season <= end)].copy()
    # one row per (cluster, game) so a game counts once per cluster it touches
    d = d.drop_duplicates(["cluster", "game_id"])
    d["block"] = d["Season"].apply(lambda s: block_label(s, block_size, start))
    d["is_news"] = d["src_type"].isin(NEWSPAPER_LIKE)

    mix = (d.groupby(["cluster", "block"])
             .agg(games=("game_id", "size"),
                  newspaper_games=("is_news", "sum"))
             .reset_index())
    mix["newspaper_share"] = (mix["newspaper_games"] / mix["games"]).round(2)

    # onset block per cluster
    onset_rows = []
    for clu, grp in mix.sort_values("block").groupby("cluster"):
        hit = grp[grp["newspaper_share"] >= ONSET_THRESHOLD]
        onset_rows.append({"cluster": clu,
                           "newspaper_onset_block": hit["block"].iloc[0] if len(hit) else "none",
                           "max_newspaper_share": grp["newspaper_share"].max()})
    onset = pd.DataFrame(onset_rows).sort_values("newspaper_onset_block")
    return mix, onset


# ---------------------------------------------------------------------------
# 3. FIRST-APPEARANCE CLIFF  (when teams enter the data, per cluster)
# ---------------------------------------------------------------------------
def first_appearance(df_assigned, block_size, start, end):
    """
    For each team: earliest season overall, and earliest NEWSPAPER-sourced
    season. Histogram by cluster+block of how many teams first appear there.
    A spike of many teams all first-appearing in one block usually means a
    source (a paper, a yearbook batch) was digitized starting then -- not that
    the schools were founded then.
    """
    d = df_assigned.copy()
    first_any = (d.groupby(["cluster", "team_name"])["Season"].min()
                  .rename("first_season").reset_index())

    news = d[d["src_type"].isin(NEWSPAPER_LIKE)]
    first_news = (news.groupby(["cluster", "team_name"])["Season"].min()
                     .rename("first_news_season").reset_index())
    first = first_any.merge(first_news, on=["cluster", "team_name"], how="left")

    f = first[(first.first_season >= start) & (first.first_season <= end)].copy()
    f["first_block"] = f["first_season"].apply(lambda s: block_label(s, block_size, start))
    cliff = (f.groupby(["cluster", "first_block"])
               .agg(teams_first_seen=("team_name", "size"))
               .reset_index()
               .sort_values(["cluster", "first_block"]))
    return first, cliff


# ---------------------------------------------------------------------------
# OPTIONAL CHART: statewide source mix by block (stacked area)
# ---------------------------------------------------------------------------
def build_mix_chart(df_assigned, block_size, start, end, state, out_html):
    try:
        import plotly.express as px
    except ImportError:
        print("  (plotly not installed; skipping chart.)")
        return
    d = df_assigned[(df_assigned.Season >= start) & (df_assigned.Season <= end)].copy()
    d = d.drop_duplicates(["game_id"])  # statewide: count each game once
    d["block"] = d["Season"].apply(lambda s: block_label(s, block_size, start))
    agg = (d.groupby(["block", "src_type"]).size().rename("games").reset_index())
    fig = px.area(agg, x="block", y="games", color="src_type",
                  title=f"{state}: source composition by block "
                        f"(shows when newspaper sourcing switched on)")
    fig.write_html(out_html)
    print(f"  Chart written: {out_html}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Collection-regime mapping for HS_Scores.")
    ap.add_argument("--state", required=True)
    ap.add_argument("--block-size", type=int, default=5)
    ap.add_argument("--start", type=int, default=1940)
    ap.add_argument("--end", type=int, default=2003)
    ap.add_argument("--inventory-only", action="store_true",
                    help="Just print the Source-type inventory and exit (verify classification).")
    args = ap.parse_args()

    state = args.state.upper()
    if state not in NAMED_MARKETS:
        sys.exit(f"No NAMED_MARKETS defined for {state}. Add it in geo_gap_analysis.py.")
    markets = NAMED_MARKETS[state]
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    df = pull_with_source(state, args.start, args.end)
    if df.empty:
        sys.exit("No rows returned.")

    # --- inventory FIRST (data-first verification) ---
    by_type, top_other = source_inventory(df)
    print("\n=== SOURCE INVENTORY (verify the classification before trusting onset) ===")
    print(by_type.to_string(index=False))
    if not top_other.empty:
        print("\n  Top raw prefixes still in 'other' (unclassified; EXCLUDED from")
        print("  newspaper onset -- add a SOURCE_RULES entry for any you want named):")
        print(top_other.to_string(index=False))
    if args.inventory_only:
        return

    # --- cluster, then regime analyses ---
    df_geo = df[df["lat"].notna() & df["lon"].notna()].copy()
    df_assigned = assign_named_markets(df_geo, markets)

    mix, onset = source_mix(df_assigned, args.block_size, args.start, args.end)
    first, cliff = first_appearance(df_assigned, args.block_size, args.start, args.end)

    print("\n=== NEWSPAPER ONSET BY MARKET (first block >25% newspaper-sourced) ===")
    print("    (DESCRIPTIVE: 'none' or late onset is fine where yearbooks are the")
    print("     best/only source -- not necessarily a gap to fill.)")
    print(onset.to_string(index=False))

    print("\n=== SOURCE MIX BY BLOCK (newspaper_share) -- a few busiest markets ===")
    busy = mix.groupby("cluster")["games"].sum().nlargest(4).index.tolist()
    print(mix[mix.cluster.isin(busy)].to_string(index=False))

    # --- write CSVs + chart ---
    paths = {
        "inventory": os.path.join(OUT_DIR, f"{state}_source_inventory_{stamp}.csv"),
        "mix":       os.path.join(OUT_DIR, f"{state}_source_mix_{stamp}.csv"),
        "onset":     os.path.join(OUT_DIR, f"{state}_newspaper_onset_{stamp}.csv"),
        "cliff":     os.path.join(OUT_DIR, f"{state}_first_appearance_{stamp}.csv"),
        "first":     os.path.join(OUT_DIR, f"{state}_team_first_seen_{stamp}.csv"),
    }
    by_type.to_csv(paths["inventory"], index=False)
    mix.to_csv(paths["mix"], index=False)
    onset.to_csv(paths["onset"], index=False)
    cliff.to_csv(paths["cliff"], index=False)
    first.to_csv(paths["first"], index=False)
    chart = os.path.join(OUT_DIR, f"{state}_source_mix_{stamp}.html")
    build_mix_chart(df_assigned, args.block_size, args.start, args.end, state, chart)

    print("\nWrote:")
    for p in paths.values():
        print(f"  {p}")
    print("READ-ONLY: nothing persisted to SQL.")


if __name__ == "__main__":
    main()