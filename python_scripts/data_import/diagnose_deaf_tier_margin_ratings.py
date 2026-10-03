#!/usr/bin/env python3
"""
diagnose_deaf_tier_margin_ratings.py

PROTOTYPE / read-only. Tests whether a rating-differential-based expected
margin is a better Weak-tier (Deaf-opponent) mismatch check than the current
static --margin-threshold in mapping_conflict_audit.py's find_tier_mismatches().

Background: on 2026-09-10, all 59 open LA TierMismatch "Weak-tier margin
inconsistent" investigations turned out to be false positives -- Louisiana
School for the Deaf (and one Texas School for the Deaf game) were genuine,
competitive varsity peers for large stretches of the 20th century, not a
structurally weak tier. A season-final (Week=52) HS_Rankings pull across
EVERY %Deaf% team nationwide confirmed this isn't LA-specific: most Deaf
programs show a real, continuous decline from near-parity (sometimes
above-average -- Pennsylvania School for the Deaf was +42 to +66 in the
1890s-1900s, Texas School for the Deaf had 10+ positive seasons pre-1950)
to a structural gap that widens progressively into the 2000s-2020s (many
programs at -100 to -170 by then). This is a continuous trend, not a single
inflection year, so a static season cutoff (MIN_WEAK_TIER_SEASON=1930)
can't really capture it -- but a rating-differential check naturally can,
since it's season-specific by construction.

PART 1 -- season-level Deaf-cohort stats: average and stddev of Week=52
rating across ALL %Deaf% teams nationwide, per season. Purpose: see how
much spread exists WITHIN the Deaf cohort itself each year. If spread is
tight in a given era, a rating-based check is trustworthy; if it's wide
(small sample, noisy data), team-specific ratings may be unreliable and a
cohort average might be the more stable prior instead.

PART 2 -- re-scores every currently-known LA TierMismatch Weak-tier (Deaf
opponent) investigation (open AND the 59 already closed Verified-FalsePos)
using ExpectedMargin = Rating(Anchor, Season) - Rating(DeafOpponent, Season)
(both Week=52 season-final), against the ACTUAL game margin. Reports the
residual (actual - expected) so we can see whether this reproduces the same
verdict we reached manually (all false positives), or would have flagged a
smaller, more precise set instead.

Nothing here writes to HS_Mapping_Investigations. This is purely a
validation pass before deciding whether to build a real replacement check
into mapping_conflict_audit.py's find_tier_mismatches().

Usage:
  python diagnose_deaf_tier_margin_ratings.py --season-stats
  python diagnose_deaf_tier_margin_ratings.py --test-la
  python diagnose_deaf_tier_margin_ratings.py --season-stats --test-la
"""

import argparse
import logging

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

# Same rating formula used throughout the project's generate_*.py scripts
# (confirmed via generate_performance_streaks_json.py), Week=52 = season-final.
RATING_EXPR = "(0.958 * [Avg_Of_Avg_Of_Home_Modified_Score] + 2.791)"


def season_deaf_cohort_stats():
    df = pd.read_sql(text(f"""
        SELECT Season, {RATING_EXPR} AS Rating
        FROM HS_Rankings
        WHERE Week = 52
          AND Home LIKE '%Deaf%'
          AND [Avg_Of_Avg_Of_Home_Modified_Score] IS NOT NULL
    """), engine)

    stats = df.groupby('Season')['Rating'].agg(
        TeamCount='count', AvgRating='mean', StdDevRating='std'
    ).reset_index()
    stats = stats.round({'AvgRating': 2, 'StdDevRating': 2})
    print(f"\n=== Deaf-cohort season stats ({len(stats)} seasons) ===")
    print(stats.sort_values('Season').to_string(index=False))
    return stats


def fetch_la_deaf_tier_investigations():
    """Pull every LA TierMismatch investigation whose linked game(s) involve
    a Deaf-named opponent -- both the 59 closed Verified-FalsePos and any
    still open -- with the actual HS_Scores row and both teams' Week=52
    rating for that season."""
    return pd.read_sql(text(f"""
        SELECT
            i.InvestigationID, i.Status, i.AnchorTeam, i.Season,
            s.Home, s.Visitor, s.Home_Score, s.Visitor_Score, s.Date,
            r_anchor.Rating AS AnchorRating,
            r_opp.Rating AS OpponentRating
        FROM HS_Mapping_Investigations i
        JOIN HS_Mapping_Investigation_Games g ON g.InvestigationID = i.InvestigationID
        JOIN HS_Scores s ON s.ID = g.ScoresID
        OUTER APPLY (
            SELECT TOP 1 {RATING_EXPR} AS Rating
            FROM HS_Rankings r
            WHERE r.Week = 52 AND r.Season = i.Season AND r.Home = i.AnchorTeam
              AND r.[Avg_Of_Avg_Of_Home_Modified_Score] IS NOT NULL
        ) r_anchor
        OUTER APPLY (
            SELECT TOP 1 {RATING_EXPR} AS Rating
            FROM HS_Rankings r
            WHERE r.Week = 52 AND r.Season = i.Season
              AND r.Home = CASE WHEN s.Home = i.AnchorTeam THEN s.Visitor ELSE s.Home END
              AND r.[Avg_Of_Avg_Of_Home_Modified_Score] IS NOT NULL
        ) r_opp
        WHERE i.State = '(LA)' AND i.ConflictType = 'TierMismatch'
          AND i.Priority LIKE '%Medium%'
    """), engine)


def score_against_expected_margin(df):
    def actual_margin(row):
        if row['Home'] == row['AnchorTeam']:
            return row['Home_Score'] - row['Visitor_Score']
        return row['Visitor_Score'] - row['Home_Score']

    df = df.copy()
    df['ActualMargin'] = df.apply(actual_margin, axis=1)
    df['ExpectedMargin'] = df['AnchorRating'] - df['OpponentRating']
    df['Residual'] = df['ActualMargin'] - df['ExpectedMargin']
    df['HasBothRatings'] = df['AnchorRating'].notna() & df['OpponentRating'].notna()
    return df


def test_la_investigations():
    df = fetch_la_deaf_tier_investigations()
    logger.info(f"{len(df)} LA TierMismatch (Weak-margin, Deaf-opponent) investigation-game row(s) found.")

    scored = score_against_expected_margin(df)
    have_ratings = scored[scored['HasBothRatings']]
    missing_ratings = scored[~scored['HasBothRatings']]

    logger.info(f"  {len(have_ratings)} row(s) have a Week=52 rating for BOTH sides that season "
                f"(can be re-scored). {len(missing_ratings)} row(s) missing a rating on one or both "
                f"sides (sparse-era games, no verdict possible from this method alone).")

    if not have_ratings.empty:
        print(f"\n=== Re-scored ({len(have_ratings)} row(s) with both ratings) ===")
        cols = ['InvestigationID', 'Status', 'Season', 'AnchorTeam', 'Home', 'Visitor',
                'ActualMargin', 'ExpectedMargin', 'Residual']
        out = have_ratings[cols].round({'ActualMargin': 1, 'ExpectedMargin': 1, 'Residual': 1})
        print(out.sort_values('Residual', key=abs, ascending=False).to_string(index=False))
        logger.info(f"  Residual stats: mean={have_ratings['Residual'].mean():.1f}, "
                    f"median={have_ratings['Residual'].median():.1f}, "
                    f"std={have_ratings['Residual'].std():.1f}. "
                    f"A LARGE |Residual| means the game defied what the rating differential predicted -- "
                    f"that's the new candidate signal, not raw margin alone.")

    if not missing_ratings.empty:
        print(f"\n=== Missing rating on one or both sides ({len(missing_ratings)} row(s)) -- "
              f"no verdict from this method, would need to fall back to something else (or stay excluded) ===")
        print(missing_ratings[['InvestigationID', 'Status', 'Season', 'AnchorTeam', 'Home', 'Visitor']].to_string(index=False))

    return scored


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--season-stats', action='store_true', help="Run Part 1: Deaf-cohort season stats")
    parser.add_argument('--test-la', action='store_true', help="Run Part 2: re-score LA TierMismatch investigations")
    args = parser.parse_args()

    if not args.season_stats and not args.test_la:
        parser.error("Specify --season-stats, --test-la, or both.")

    if args.season_stats:
        season_deaf_cohort_stats()
    if args.test_la:
        test_la_investigations()


if __name__ == "__main__":
    main()