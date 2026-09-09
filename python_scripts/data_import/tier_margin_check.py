#!/usr/bin/env python3
"""
tier_margin_check.py

Re-prioritizes the GhostTeam "Low - possible multi-level scheduling"
queue using a team-tier classification derived from the opponent's
standardized name, cross-checked against the actual score margin.

Background: the Low-tier signal alone (same anchor team, two games 1-2
days apart, different opponents) doesn't distinguish a genuine
multi-level-scheduling week (varsity Thursday, JV/freshman Friday -- see
Edmond OCA) from a real mapping error (Marlow Central) or from ordinary,
harmless scheduling variance (Bishop McGuinness). This script adds a
second signal: does the SCORE MARGIN make sense given what the opponent's
name implies about its competitive tier?

Tier classification (from the opponent's standardized name):
  WEAK-TIER   -- contains "Deaf", OR ends in a sub-varsity suffix already
                 used as a naming convention in this DB ( JV/ B/ C/
                 Lightweight/ Freshmen/ Frosh before the state tag).
                 ERA-GATED: "Deaf" only counts as weak-tier for
                 Season >= 1930 -- pre-1930s deaf-school teams were often
                 genuinely competitive with mainstream programs, per
                 direct user knowledge of this era, so the assumption
                 does not hold further back.
  STRONG-TIER -- contains "College Frosh" or "College JV" specifically.
                 Deliberately narrower than just "College" anywhere in
                 the name, which would misfire on real high schools like
                 "___ College Prep" or "___ College High School". A
                 college's freshman/JV squad is a much more unambiguous
                 signal than the word "College" alone.
  (everything else is UNCLASSIFIED -- falls back to existing methods)

For each Low-tier investigation (a pair of games), the two opponents are
classified and the margin against any weak/strong-tier opponent is
checked for plausibility:
  ConsistentMultiLevel -- weak-tier opponent, anchor won by >= 20 points.
                          Looks like real multi-level scheduling, low
                          priority for manual review.
  InconsistentMargin   -- weak-tier opponent, but a close game or a loss.
                          The tier assumption doesn't hold up -- worth a
                          closer look.
  CollegeTierSuspect    -- opponent is a college frosh/JV team, any
                          margin. Always worth a look (same underlying
                          risk as the earlier college/HS collision work).
  Unclassified          -- neither opponent matches a known tier;
                          falls back to the existing "Low" priority
                          triage (repeat-offenders rollup, etc.)

This script is READ-ONLY -- it never modifies HS_Scores or
HS_Mapping_Investigations. It prints/exports an assessment report so you
can decide what (if anything) to do with each bucket, same as every other
review-first tool in this project.

Usage:
  python tier_margin_check.py --state OK                       # full report to console
  python tier_margin_check.py --state OK --output ok_tiers.csv # also write CSV
  python tier_margin_check.py --state OK --bucket InconsistentMargin  # only show one bucket
"""

import argparse
import re

import pandas as pd
from sqlalchemy import create_engine, text

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

WEAK_SUFFIX_RE = re.compile(r'\s(JV|B|C|Lightweight|Freshmen|Frosh)\s\([A-Z]{2}\)$')
DEAF_RE = re.compile(r'Deaf', re.IGNORECASE)
COLLEGE_FROSH_JV_RE = re.compile(r'College\s+(Frosh|JV)', re.IGNORECASE)

MIN_WEAK_TIER_SEASON = 1930


def classify_tier(name, season):
    if COLLEGE_FROSH_JV_RE.search(name):
        return 'strong'
    if DEAF_RE.search(name) and season >= MIN_WEAK_TIER_SEASON:
        return 'weak'
    if WEAK_SUFFIX_RE.search(name):
        return 'weak'
    return None


def fetch_low_tier_pairs(state):
    """Every Low-priority GhostTeam investigation's linked games, for
    pairing back up into (anchor, opponent, score) rows."""
    return pd.read_sql(text("""
        SELECT i.InvestigationID, i.AnchorTeam, i.Season,
               s.ID AS ScoresID, s.Date, s.Home, s.Home_Score, s.Visitor, s.Visitor_Score
        FROM HS_Mapping_Investigations i
        JOIN HS_Mapping_Investigation_Games g ON g.InvestigationID = i.InvestigationID
        JOIN HS_Scores s ON s.ID = g.ScoresID
        WHERE i.State = :state AND i.ConflictType = 'GhostTeam'
          AND i.Priority LIKE 'Low - possible multi-level%'
        ORDER BY i.InvestigationID, s.Date
    """), engine, params={'state': f"({state.strip('()').upper()})"})


def assess(df):
    results = []
    for inv_id, grp in df.groupby('InvestigationID'):
        anchor = grp.iloc[0]['AnchorTeam']
        season = int(grp.iloc[0]['Season'])
        bucket = 'Unclassified'
        detail_parts = []

        for _, row in grp.iterrows():
            is_home = (row['Home'] == anchor)
            opponent = row['Visitor'] if is_home else row['Home']
            our_score = row['Home_Score'] if is_home else row['Visitor_Score']
            their_score = row['Visitor_Score'] if is_home else row['Home_Score']
            margin = our_score - their_score

            tier = classify_tier(opponent, season)
            if tier == 'strong':
                bucket = 'CollegeTierSuspect'
                detail_parts.append(f"{opponent} (college frosh/JV) margin={margin:+d}")
            elif tier == 'weak':
                if margin >= 20:
                    if bucket == 'Unclassified':
                        bucket = 'ConsistentMultiLevel'
                else:
                    bucket = 'InconsistentMargin'  # overrides ConsistentMultiLevel if both present
                detail_parts.append(f"{opponent} (weak-tier) margin={margin:+d}")

        results.append({
            'InvestigationID': inv_id, 'AnchorTeam': anchor, 'Season': season,
            'Bucket': bucket, 'Detail': '; '.join(detail_parts) if detail_parts else '(no tier match)'
        })
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state', required=True)
    parser.add_argument('--bucket', default=None,
                         choices=['ConsistentMultiLevel', 'InconsistentMargin', 'CollegeTierSuspect', 'Unclassified'],
                         help="Only show this bucket")
    parser.add_argument('--output', default=None, help="Also write full results to this CSV path")
    args = parser.parse_args()

    df = fetch_low_tier_pairs(args.state)
    if df.empty:
        print(f"No Low-priority GhostTeam investigations found for {args.state}.")
        return

    assessed = assess(df)

    print(f"\n=== Tier/margin assessment for {args.state} Low-tier GhostTeam queue ===")
    print(assessed['Bucket'].value_counts().to_string())

    shown = assessed if args.bucket is None else assessed[assessed['Bucket'] == args.bucket]
    print(f"\n--- {'All buckets' if args.bucket is None else args.bucket} ({len(shown)} investigations) ---")
    print(shown.to_string(index=False))

    if args.output:
        assessed.to_csv(args.output, index=False, encoding='utf-8-sig')
        print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    main()