#!/usr/bin/env python3
"""
reconcile_2019_ambiguous.py

Final step of the 2019 MaxPreps date-truncation repair (see
maxpreps_2019_date_truncation_fix.py and rescrape_2019_ambiguous.py).
Matches each "Ambiguous" row (2+ equally-plausible Friday/Thu/Sat
candidates, couldn't be resolved from the stored data alone) against the
freshly-scraped, live 2019 schedule data pulled by
rescrape_2019_ambiguous.py, and applies the confirmed real date with full
audit logging.

MATCHING: freshly-scraped rows (Source LIKE '%/19-20/%', BatchID = the
rescrape batch) are matched to each ambiguous row by the UNORDERED pair of
team names (Home/Away can come out differently between the corrupted row
and the freshly-scraped one, since FinalizeMaxPrepsData assigns Home/Away
alphabetically when it can't tell from '@'/'vs', not necessarily matching
the original corrupted row's assignment) -- then the score pair is
cross-checked (also unordered) to confirm it's the same real game, not
some other meeting between the same two teams that season.

CONFIDENCE:
  Matched-ScoreConfirmed  -- exactly one freshly-scraped game between these
                             two teams, and its score matches (unordered)
                             the corrupted row's score. Auto-applies.
  Matched-DateNotInRange  -- matched and score-confirmed, but the real
                             date ISN'T one of the pre-computed Fri/Thu/Sat
                             candidates from maxpreps_2019_date_truncation_
                             fix.py -- unexpected, so this is reported but
                             NOT auto-applied without a look.
  Matched-ScoreMismatch   -- exactly one freshly-scraped game between
                             these teams, but the score doesn't match --
                             surfaced for review, not auto-applied.
  Ambiguous-MultipleGames -- 2+ freshly-scraped games between these teams
                             that season (rematch/playoff) and the score
                             doesn't narrow it to one. Not auto-applied.
  NoMatch                 -- no freshly-scraped game found between these
                             two teams at all (team wasn't in the matched
                             list, scrape found nothing, or the URL join
                             silently dropped it). Not auto-applied.

This script is READ-ONLY by default. --apply only ever touches
Matched-ScoreConfirmed rows (Date field only, ID-scoped, logged to
HS_Scores_Change_Log).

Usage:
  python reconcile_2019_ambiguous.py --input ok_2019_ambiguous.csv --batch-id 27
  python reconcile_2019_ambiguous.py --input ok_2019_ambiguous.csv --batch-id 27 --output ok_2019_reconciled.csv
  python reconcile_2019_ambiguous.py --input ok_2019_ambiguous.csv --batch-id 27 --apply
"""

import argparse
import logging
from datetime import date, datetime

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)


def fetch_scraped_games(batch_id):
    df = pd.read_sql(text("""
        SELECT ID, Date, Home, Visitor, Home_Score, Visitor_Score
        FROM HS_Scores
        WHERE BatchID = :batch_id AND Source LIKE '%/19-20/%'
    """), engine, params={'batch_id': batch_id})
    df['ID'] = df['ID'].astype(str)
    return df


def build_match_index(scraped_df):
    """team-pair (frozenset) -> list of scraped game rows."""
    index = {}
    for r in scraped_df.itertuples(index=False):
        key = frozenset([r.Home, r.Visitor])
        index.setdefault(key, []).append(r)
    return index


def parse_candidate_dates(candidate_str):
    """CandidateDates looks like '2019-10-11 (Fri), 2019-10-18 (Fri)' -- extract just the ISO dates."""
    if not isinstance(candidate_str, str) or not candidate_str.strip():
        return set()
    dates = set()
    for part in candidate_str.split(','):
        iso = part.strip().split(' ')[0]
        try:
            dates.add(datetime.strptime(iso, '%Y-%m-%d').date())
        except ValueError:
            pass
    return dates


def to_date(value):
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()


def reconcile(ambiguous_df, match_index):
    results = []
    for r in ambiguous_df.itertuples(index=False):
        key = frozenset([r.Home, r.Visitor])
        candidates = match_index.get(key, [])
        candidate_dates = parse_candidate_dates(r.CandidateDates)
        row_scores = {int(r.Home_Score), int(r.Visitor_Score)}

        base = {'ScoresID': r.ScoresID, 'CurrentDate': r.CurrentDate, 'Home': r.Home,
                'Visitor': r.Visitor, 'Home_Score': r.Home_Score, 'Visitor_Score': r.Visitor_Score}

        if not candidates:
            results.append({**base, 'RealDate': None, 'Status': 'NoMatch'})
            continue

        score_matched = [c for c in candidates if {int(c.Home_Score), int(c.Visitor_Score)} == row_scores]

        if len(score_matched) == 1:
            real_date = to_date(score_matched[0].Date)
            status = 'Matched-ScoreConfirmed' if (not candidate_dates or real_date in candidate_dates) else 'Matched-DateNotInRange'
            results.append({**base, 'RealDate': real_date, 'Status': status})
        elif len(candidates) == 1:
            real_date = to_date(candidates[0].Date)
            results.append({**base, 'RealDate': real_date, 'Status': 'Matched-ScoreMismatch'})
        else:
            results.append({**base, 'RealDate': None, 'Status': 'Ambiguous-MultipleGames'})
    return pd.DataFrame(results)


def apply_corrections(report_df, dry_run=True):
    fixable = report_df[report_df['Status'] == 'Matched-ScoreConfirmed']
    if fixable.empty:
        logger.info("No Matched-ScoreConfirmed rows to apply.")
        return

    if dry_run:
        logger.info(f"[DRY RUN] Would apply {len(fixable)} correction(s).")
        return

    applied = 0
    with engine.begin() as conn:
        for _, row in fixable.iterrows():
            reason = (f"2019 MaxPreps date-truncation bug: stored date {row['CurrentDate']} "
                      f"corrected to {row['RealDate']}, confirmed via live 2019 MaxPreps re-scrape "
                      f"(rescrape_2019_ambiguous.py) -- team pair + score both matched exactly one "
                      f"real game. See reconcile_2019_ambiguous.py.")
            conn.execute(text("""
                INSERT INTO HS_Scores_Change_Log
                    (ScoresID, FieldChanged, OldValue, NewValue, Reason, Script)
                VALUES (:id, 'Date', :old, :new, :reason, 'reconcile_2019_ambiguous.py')
            """), {'id': row['ScoresID'], 'old': str(row['CurrentDate']),
                   'new': str(row['RealDate']), 'reason': reason})
            conn.execute(text("UPDATE HS_Scores SET Date = :new WHERE ID = :id"),
                         {'new': row['RealDate'], 'id': row['ScoresID']})
            applied += 1
    logger.info(f"{applied} correction(s) applied and logged to HS_Scores_Change_Log.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', required=True, help="The original Ambiguous CSV from maxpreps_2019_date_truncation_fix.py")
    parser.add_argument('--batch-id', type=int, required=True, help="batch_id from rescrape_2019_ambiguous.py")
    parser.add_argument('--output', default=None)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    ambiguous_df = pd.read_csv(args.input, parse_dates=['CurrentDate'])
    ambiguous_df['CurrentDate'] = ambiguous_df['CurrentDate'].dt.date
    ambiguous_df = ambiguous_df[ambiguous_df['Confidence'] == 'Ambiguous-NeedsLiveCheck']
    logger.info(f"{len(ambiguous_df)} ambiguous row(s) loaded from {args.input}.")

    scraped_df = fetch_scraped_games(args.batch_id)
    logger.info(f"{len(scraped_df)} freshly-scraped game(s) loaded for batch_id {args.batch_id}.")

    match_index = build_match_index(scraped_df)
    report = reconcile(ambiguous_df, match_index)

    print("\n=== Reconciliation status breakdown ===")
    print(report['Status'].value_counts().to_string())
    print(f"\n{report.to_string(index=False)}")

    if args.output:
        report.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {args.output}")

    apply_corrections(report, dry_run=not args.apply)
    if not args.apply:
        print("\n(Review only -- no changes made. Re-run with --apply to fix Matched-ScoreConfirmed rows.)")


if __name__ == "__main__":
    main()
