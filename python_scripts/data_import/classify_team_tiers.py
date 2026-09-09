#!/usr/bin/env python3
"""
classify_team_tiers.py

Builds/refreshes a NATIONWIDE reference table, HS_Team_Tier_Classification,
that labels teams as belonging to a structurally weaker or stronger
competitive tier than ordinary varsity play -- the foundation for the
year-long, state-by-state "suspicious game" review process.

Two-stage classification:

  STAGE 1 -- Name-seed (unambiguous, from the standardized name itself):
    WEAK seed   -- "Deaf" in the name (ERA-GATED: only for Season >= 1930;
                   pre-1930s deaf-school teams were often genuinely
                   competitive with mainstream programs, so the weak-tier
                   assumption does not hold further back), OR a
                   sub-varsity suffix already used as a naming convention
                   in this DB ( JV / B / C / Lightweight / Freshmen /
                   Frosh immediately before the state tag).
    STRONG seed -- "College Frosh" or "College JV" specifically.
                   Deliberately narrower than "College" alone, which would
                   misfire on real high schools like "___ College Prep."

  STAGE 2 -- One-hop propagation (for teams with no distinguishing name):
    A team is labeled PROPAGATED-WEAK if, across its ENTIRE game history,
    at least --threshold (default 65%) of its games are against
    Stage-1 WEAK-seed opponents, AND it has played at least --min-games
    (default 5) total games (small samples are too noisy to trust).
    Propagation stops here -- a team that mostly plays PROPAGATED-weak
    teams does NOT itself get propagated further. This is a deliberate,
    conservative choice: rural leagues (8-man Oklahoma football, for
    example) are naturally dense, tightly-connected clusters of small
    schools playing each other repeatedly. That's a real, legitimate
    league, not evidence of anything wrong -- letting the weak-tier label
    chain through multiple hops would risk mislabeling an entire normal
    small-town league just because of its schedule's connectivity, not
    because of any actual competitive mismatch. Anchoring propagation to
    one hop from an unambiguous name-seed keeps the classification honest.

  Teams that don't hit either the Stage-1 or Stage-2 bar are NOT stored
  in the table at all (kept small; absence = implicitly "Normal" tier at
  query time).

This script only WRITES to HS_Team_Tier_Classification -- it never
touches HS_Scores or HS_Mapping_Investigations. Run it once to build the
table, then periodically to refresh it as more data is fixed/imported.
Actual game-level flagging happens separately, in
`mapping_conflict_audit.py detect-tier-mismatch --state XX`, which reads
this table.

Usage:
  python classify_team_tiers.py                          # build/refresh nationwide, default thresholds
  python classify_team_tiers.py --threshold 0.7 --min-games 8   # stricter propagation
  python classify_team_tiers.py --dry-run                # show counts only, don't write
"""

import argparse
import logging
import re
from collections import defaultdict

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

WEAK_SUFFIX_RE = re.compile(r'\s(JV|B|C|Lightweight|Freshmen|Frosh)\s\([A-Za-z]{2}\)$')
DEAF_RE = re.compile(r'Deaf', re.IGNORECASE)
COLLEGE_FROSH_JV_RE = re.compile(r'College\s+(Frosh|JV)', re.IGNORECASE)
MIN_WEAK_TIER_SEASON = 1930

DDL = """
IF OBJECT_ID('dbo.HS_Team_Tier_Classification', 'U') IS NULL
CREATE TABLE HS_Team_Tier_Classification (
    TeamName VARCHAR(150) NOT NULL PRIMARY KEY,
    Tier VARCHAR(20) NOT NULL,          -- 'Weak' or 'Strong'
    Basis VARCHAR(20) NOT NULL,         -- 'NameSeed' or 'Propagated'
    Confidence FLOAT NULL,              -- Propagated only: fraction of games against seed-tier opponents
    GamesConsidered INT NULL,
    ComputedAt DATETIME DEFAULT GETDATE()
)
"""


def ensure_schema():
    with engine.begin() as conn:
        conn.execute(text(DDL))


def name_seed_tier(name, season):
    if COLLEGE_FROSH_JV_RE.search(name):
        return 'Strong'
    if DEAF_RE.search(name) and season >= MIN_WEAK_TIER_SEASON:
        return 'Weak'
    if WEAK_SUFFIX_RE.search(name):
        return 'Weak'
    return None


def fetch_all_games():
    logger.info("Fetching all Home/Visitor/Season rows from HS_Scores (this is the full table, may take a moment)...")
    df = pd.read_sql(text("SELECT Home, Visitor, Season FROM HS_Scores"), engine)
    logger.info(f"{len(df)} games fetched.")
    return df


def build_classification(df, threshold, min_games):
    # Stage 1: name-seed classification, evaluated per (name, season) since
    # the Deaf rule is era-gated -- the same name can be seed-weak in one
    # season and unclassified in an earlier one.
    logger.info("Stage 1: name-seed classification...")
    all_names = pd.unique(pd.concat([df['Home'], df['Visitor']]))
    static_seed = {}  # names whose seed status doesn't depend on season (suffix/college rules)
    for name in all_names:
        if COLLEGE_FROSH_JV_RE.search(name):
            static_seed[name] = 'Strong'
        elif WEAK_SUFFIX_RE.search(name):
            static_seed[name] = 'Weak'
    logger.info(f"  {len(static_seed)} teams seeded by name pattern "
                f"({sum(1 for v in static_seed.values() if v == 'Weak')} weak, "
                f"{sum(1 for v in static_seed.values() if v == 'Strong')} strong).")

    # Stage 2: one-hop propagation. For every team NOT already a static
    # seed, count its games against a weak-seed opponent (name-suffix seed,
    # OR a Deaf-named opponent in a season >= 1930) versus its total games.
    logger.info("Stage 2: one-hop propagation (this walks every game row once)...")
    total_games = defaultdict(int)
    weak_opp_games = defaultdict(int)

    for row in df.itertuples(index=False):
        home, visitor, season = row.Home, row.Visitor, row.Season
        home_opp_is_weak = static_seed.get(visitor) == 'Weak' or (DEAF_RE.search(visitor) and season >= MIN_WEAK_TIER_SEASON)
        visitor_opp_is_weak = static_seed.get(home) == 'Weak' or (DEAF_RE.search(home) and season >= MIN_WEAK_TIER_SEASON)

        total_games[home] += 1
        total_games[visitor] += 1
        if home_opp_is_weak:
            weak_opp_games[home] += 1
        if visitor_opp_is_weak:
            weak_opp_games[visitor] += 1

    propagated = {}
    for team, games in total_games.items():
        if team in static_seed:
            continue
        if games < min_games:
            continue
        pct = weak_opp_games.get(team, 0) / games
        if pct >= threshold:
            propagated[team] = (pct, games)

    logger.info(f"  {len(propagated)} additional teams propagated to Weak tier "
                f"(>= {threshold:.0%} of >= {min_games} games against a seed-weak opponent).")

    return static_seed, propagated


def dedupe_case_insensitive(rows):
    """SQL Server's default collation is case/whitespace-insensitive, so two
    Python strings that pd.unique() treats as distinct (e.g. differing only
    in case, or a trailing space) can still collide on the TeamName primary
    key and abort the whole insert loop partway through. Collapse to one
    row per normalized (stripped+uppercased) name before writing, keeping
    the first occurrence -- same defensive idea as the rest of this
    project's "verify before you trust a name string" pattern."""
    seen = set()
    deduped = []
    for row in rows:
        key = row[0].strip().upper()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def write_table(static_seed, propagated, dry_run=True):
    if dry_run:
        logger.info(f"[DRY RUN] Would write {len(static_seed)} name-seed rows + {len(propagated)} propagated rows "
                     f"= {len(static_seed) + len(propagated)} total to HS_Team_Tier_Classification.")
        return

    seed_rows = dedupe_case_insensitive(list(static_seed.items()))
    prop_rows = dedupe_case_insensitive([(name, pct, games) for name, (pct, games) in propagated.items()])
    dropped = (len(static_seed) - len(seed_rows)) + (len(propagated) - len(prop_rows))
    if dropped:
        logger.info(f"  {dropped} row(s) dropped as case/whitespace-insensitive duplicates of another name.")

    ensure_schema()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM HS_Team_Tier_Classification"))
        for name, tier in seed_rows:
            conn.execute(text("""
                INSERT INTO HS_Team_Tier_Classification (TeamName, Tier, Basis, Confidence, GamesConsidered)
                VALUES (:name, :tier, 'NameSeed', NULL, NULL)
            """), {'name': name, 'tier': tier})
        for name, pct, games in prop_rows:
            conn.execute(text("""
                INSERT INTO HS_Team_Tier_Classification (TeamName, Tier, Basis, Confidence, GamesConsidered)
                VALUES (:name, 'Weak', 'Propagated', :pct, :games)
            """), {'name': name, 'pct': pct, 'games': games})
    logger.info(f"Wrote {len(seed_rows) + len(prop_rows)} rows to HS_Team_Tier_Classification.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--threshold', type=float, default=0.65, help="Min fraction of games against seed-weak opponents to propagate (default 0.65)")
    parser.add_argument('--min-games', type=int, default=5, help="Min total games a team must have to be eligible for propagation (default 5)")
    parser.add_argument('--dry-run', action='store_true', help="Compute and report counts only, don't write to the DB")
    args = parser.parse_args()

    df = fetch_all_games()
    static_seed, propagated = build_classification(df, args.threshold, args.min_games)
    write_table(static_seed, propagated, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
