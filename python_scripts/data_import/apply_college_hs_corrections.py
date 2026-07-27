#!/usr/bin/env python3
"""
apply_college_hs_corrections.py

Applies confirmed college/HS name corrections directly to HS_Scores.

Reads one or both review sheets produced by find_college_hs_mismatches.py
(College_HS_Mismatch_Review.csv) and find_hs_games_mislabeled_as_college.py
(HS_Mislabeled_As_College_Review.csv). For every row where you've filled in
BOTH "Your_Determination" and "Corrected_Name", it updates that one specific
game's team name in HS_Scores -- and only that one game, not every game
involving that team name, since the whole point of this pair of scripts is
that the SAME name can be right in five games and wrong in a sixth.

Each correction is matched on Season + Date + Home + Visitor + Home_Score +
Visitor_Score -- the full original row, not just the team name -- so a typo
or a coincidental duplicate can't cause the wrong row to get updated. If
that exact combination doesn't match exactly one row in HS_Scores, the
correction is skipped and logged as a warning rather than guessed at.

Naturally idempotent: once a row is corrected, its original name no longer
matches anything (it's been renamed), so re-running this script is safe --
already-applied rows just skip with a "0 rows matched" note instead of
double-applying or erroring.

Usage
-----
python apply_college_hs_corrections.py --dry-run          # preview every UPDATE, zero DB writes
python apply_college_hs_corrections.py                    # apply for real
python apply_college_hs_corrections.py --input College_HS_Mismatch_Review.csv   # just one sheet
"""

import os
import argparse
import logging
import csv
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUTS = [
    os.path.join(SCRIPT_DIR, 'College_HS_Mismatch_Review.csv'),
    os.path.join(SCRIPT_DIR, 'HS_Mislabeled_As_College_Review.csv'),
]
APPLIED_LOG = os.path.join(SCRIPT_DIR, 'College_HS_Corrections_Applied_Log.csv')

db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)


def extract_confirmed_rows(path):
    """
    Handles both review-sheet schemas:
      find_college_hs_mismatches.py:        Flagged_Team / Flagged_Team_Side / Flagged_Team_Score
      find_hs_games_mislabeled_as_college.py: Labeled_College_Team / Side / Team_Score
    Returns a list of dicts with a common shape, one per confirmed correction.
    """
    if not os.path.exists(path):
        logger.warning(f"  {path} not found -- skipping.")
        return []

    df = pd.read_csv(path, encoding='utf-8-sig')
    for col in ['Your_Determination', 'Corrected_Name']:
        if col not in df.columns:
            logger.warning(f"  {path} has no '{col}' column (was it generated before this feature was added? "
                            f"Re-run the generator script to pick up the new column.) -- skipping.")
            return []
        df[col] = df[col].fillna('').astype(str).str.strip()

    confirmed = df[(df['Your_Determination'] != '') & (df['Corrected_Name'] != '')]
    if confirmed.empty:
        return []

    if 'Flagged_Team' in df.columns:
        name_col, side_col, score_col = 'Flagged_Team', 'Flagged_Team_Side', 'Flagged_Team_Score'
    elif 'Labeled_College_Team' in df.columns:
        name_col, side_col, score_col = 'Labeled_College_Team', 'Side', 'Team_Score'
    else:
        logger.warning(f"  {path} doesn't match either known review-sheet schema -- skipping.")
        return []

    rows = []
    for _, r in confirmed.iterrows():
        original_name = str(r[name_col]).strip()
        corrected_name = str(r['Corrected_Name']).strip()
        if corrected_name == original_name:
            continue  # nothing to change
        side = str(r[side_col]).strip()
        season = int(r['Season'])
        date = str(r['Date'])
        opponent = str(r['Opponent']).strip()
        team_score = r[score_col]
        opp_score = r['Opponent_Score']

        if side == 'Home':
            home, visitor = original_name, opponent
            home_score, visitor_score = team_score, opp_score
        elif side == 'Visitor':
            home, visitor = opponent, original_name
            home_score, visitor_score = opp_score, team_score
        else:
            logger.warning(f"  Row for '{original_name}' has an unrecognized side value ({side!r}) -- skipping.")
            continue

        rows.append({
            'source_file': os.path.basename(path),
            'original_name': original_name,
            'corrected_name': corrected_name,
            'side': side,
            'season': season,
            'date': date,
            'home': home,
            'visitor': visitor,
            'home_score': home_score,
            'visitor_score': visitor_score,
            'determination': str(r['Your_Determination']).strip(),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Apply confirmed college/HS name corrections to HS_Scores.")
    parser.add_argument('--input', nargs='+', default=None,
                         help="Review CSV(s) to read. Default: both known review sheets, if present.")
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    inputs = args.input if args.input else DEFAULT_INPUTS

    all_rows = []
    for path in inputs:
        rows = extract_confirmed_rows(path)
        logger.info(f"{path}: {len(rows)} confirmed correction(s) found.")
        all_rows.extend(rows)

    if not all_rows:
        logger.info("Nothing to apply.")
        return

    logger.info(f"\n{'[DRY RUN] Would apply' if args.dry_run else 'Applying'} {len(all_rows)} correction(s):\n")

    if args.dry_run:
        # Zero DB interaction in dry-run -- don't even open a connection.
        for row in all_rows:
            update_col = 'Home' if row['side'] == 'Home' else 'Visitor'
            preview = (f"  {row['season']} {row['date']}: {row['home']} vs {row['visitor']} "
                       f"({row['home_score']}-{row['visitor_score']}) -- "
                       f"SET {update_col} = '{row['corrected_name']}' (was '{row['original_name']}')")
            logger.info(preview)
        logger.info(f"\n[DRY RUN] Nothing written. {len(all_rows)} correction(s) previewed above.")
        return

    applied_log_rows = []
    applied_count = 0
    skipped_count = 0

    with engine.begin() as connection:
        for row in all_rows:
            update_col = 'Home' if row['side'] == 'Home' else 'Visitor'
            preview = (f"  {row['season']} {row['date']}: {row['home']} vs {row['visitor']} "
                       f"({row['home_score']}-{row['visitor_score']}) -- "
                       f"SET {update_col} = '{row['corrected_name']}' (was '{row['original_name']}')")

            query = text(f"""
                UPDATE HS_Scores
                SET {update_col} = :corrected_name
                WHERE Season = :season AND Date = :date
                  AND Home = :home AND Visitor = :visitor
                  AND Home_Score = :home_score AND Visitor_Score = :visitor_score
            """)
            result = connection.execute(query, {
                'corrected_name': row['corrected_name'],
                'season': row['season'], 'date': row['date'],
                'home': row['home'], 'visitor': row['visitor'],
                'home_score': row['home_score'], 'visitor_score': row['visitor_score'],
            })

            if result.rowcount == 1:
                logger.info(f"✅ {preview}")
                applied_count += 1
                applied_log_rows.append({**row, 'applied_at': datetime.now().isoformat(), 'status': 'applied'})
            elif result.rowcount == 0:
                logger.warning(f"⚠️  No matching row found (already corrected, or the original data has since "
                                f"changed) -- skipped: {preview}")
                skipped_count += 1
            else:
                # Should be structurally impossible given how specific the WHERE clause
                # is, but never silently rename more rows than you reviewed.
                logger.error(f"❌ Matched {result.rowcount} rows (expected exactly 1) -- skipped to avoid an "
                              f"unintended bulk rename: {preview}")
                skipped_count += 1

    logger.info(f"\nDone. {applied_count} correction(s) applied, {skipped_count} skipped.")

    if applied_log_rows:
        log_exists = os.path.exists(APPLIED_LOG)
        with open(APPLIED_LOG, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=list(applied_log_rows[0].keys()))
            if not log_exists:
                writer.writeheader()
            writer.writerows(applied_log_rows)
        logger.info(f"Logged to {APPLIED_LOG} for your records.")


if __name__ == "__main__":
    main()
