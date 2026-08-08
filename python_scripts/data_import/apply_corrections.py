# apply_corrections.py - v3.1
# IMPROVEMENTS:
# 1. Now reads from the correct 'New_Alias_Suggestions.csv' file.
# 2. Connects directly to the DB to apply aliases automatically.
# 3. NEW: Rule_Type = 'Ignore' support for one-off, unresolvable names.
#    - Ignore rows are only committed to the DB when you pass --final.
#      Without --final they're left completely alone (no DB write), so you
#      can keep marking/unmarking them across multiple interim runs while
#      fuzzy-match suggestions keep improving, with nothing locked in yet.
#    - Even with --final, an Ignore row is only committed if it's a genuine
#      one-off: Source_Files and Opponents_Played must NOT contain a comma
#      (i.e. it appears in exactly one clipping against exactly one
#      opponent). Recurring names are refused with a warning instead of
#      being silently suppressed everywhere.
#    - Committed Ignore rows map the alias to the sentinel standardized
#      name '[IGNORED]'. master_scores_importer.py recognizes this sentinel
#      and drops just that game from the batch instead of importing a
#      garbage team name or blocking the whole batch.

import os
import re
import argparse
import pandas as pd
import logging
from sqlalchemy import create_engine, text

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
# CORRECTED FILENAME
SUGGESTION_CSV = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv')
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
GLOBAL_ALIAS_REGION = "*Global*"
IGNORE_SENTINEL = "[IGNORED]"
# Every standardized team name must end in a space, an open paren, exactly
# two letters, and a close paren -- e.g. "Marietta College (OH)". This is
# deliberately just a STRUCTURAL check (any two letters), not a validated
# list of real state/province codes, since a handful of standardized names
# legitimately end in a non-US code (Canadian provinces, etc.). It's here to
# catch typos/mangling in Final_Proper_Name -- missing space, wrong number
# of letters, missing/extra parens, stray characters -- before they get
# written into HS_Team_Aliases and start propagating into every future
# import that matches this alias.
STATE_SUFFIX_RE = re.compile(r' \([A-Z]{2}\)$')
# =================================================

# --- Boilerplate Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
# Engine is created lazily (only in get_engine()) so --dry-run never needs
# pyodbc/the ODBC driver installed at all, let alone a live connection.
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(db_connection_str)
    return _engine
# === End Setup ===


def is_one_off(source_files, opponents_played):
    """A row is a genuine one-off only if it has a single source clipping
    and a single opponent -- i.e. no commas in either column."""
    return (',' not in str(source_files)) and (',' not in str(opponents_played))


def bad_state_suffix_reason(proper_name):
    """Returns a human-readable reason if proper_name's state/province suffix
    is malformed, or None if it looks fine. Structural check only (any two
    letters) -- not validated against a real state/province list, since a
    few standardized names legitimately end in a non-US code."""
    if STATE_SUFFIX_RE.search(proper_name):
        return None
    tail = proper_name[-6:] if len(proper_name) >= 6 else proper_name
    return (f"expected the name to end in ' (XX)' (space, open paren, exactly two "
            f"letters, close paren) -- got '...{tail}' instead")


def apply_normal_rule(connection, row, dry_run=False):
    alias_name = str(row.get('Unrecognized_Alias', '')).replace("'", "''")
    proper_name = str(row.get('Final_Proper_Name', '')).replace("'", "''")
    scope = str(row.get('Alias_Scope', 'Regional'))
    region = str(row.get('Newspaper_Region', '')).replace("'", "''")
    rule_type = str(row.get('Rule_Type', 'Alias')).strip().lower()

    if not alias_name or not proper_name:
        return 'skipped_missing'

    suffix_problem = bad_state_suffix_reason(proper_name)
    if suffix_problem:
        logger.warning(f"{'[DRY RUN] ' if dry_run else ''}SKIPPED '{alias_name}' -> '{proper_name}': {suffix_problem}. "
                        f"Fix Final_Proper_Name in the sheet and re-run.")
        return 'skipped_bad_suffix'

    target_region = GLOBAL_ALIAS_REGION if scope.lower() == 'global' else region

    if rule_type == 'abbreviation':
        action = f"Applying ABBREVIATION rule: '{alias_name}' -> '{proper_name}' for region '{target_region}'"
        sql_str = f"MERGE INTO dbo.HS_Team_Abbreviations AS T USING (SELECT '{alias_name}' AS A, '{proper_name}' AS S, '{target_region}' AS R) AS S ON T.Abbreviation = S.A AND T.Newspaper_Region = S.R WHEN NOT MATCHED THEN INSERT (Abbreviation, Standardized_Name, Newspaper_Region) VALUES (S.A, S.S, S.R);"
    else:  # Default to creating a standard alias
        action = f"Applying ALIAS rule: '{alias_name}' -> '{proper_name}' for region '{target_region}'"
        sql_str = f"EXEC sp_AddTeamAlias @AliasName = '{alias_name}', @StandardizedName = '{proper_name}', @NewspaperRegion = '{target_region}';"

    if dry_run:
        logger.info(f"[DRY RUN] Would execute -- {action}")
        logger.info(f"[DRY RUN]   SQL: {sql_str}")
    else:
        logger.info(action)
        connection.execute(text(sql_str))
    return 'applied'


def apply_ignore_rule(connection, row, final, dry_run=False):
    alias_name = str(row.get('Unrecognized_Alias', '')).strip()
    if not alias_name:
        return 'skipped'

    source_files = row.get('Source_Files', '')
    opponents = row.get('Opponents_Played', '')

    if not final:
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Ignore rule staged for '{alias_name}' but --final not passed -- leaving it open for further review.")
        return 'not_final'

    if not is_one_off(source_files, opponents):
        logger.warning(f"{'[DRY RUN] ' if dry_run else ''}Ignore rule for '{alias_name}' {'would be' if dry_run else ''} SKIPPED: it appears across multiple clippings/opponents "
                        f"(Source_Files or Opponents_Played contains a comma), so it isn't a true one-off. "
                        f"Give it a real Final_Proper_Name instead of Ignore.")
        return 'recurring'

    scope = str(row.get('Alias_Scope', 'Regional'))
    region = str(row.get('Newspaper_Region', '')).replace("'", "''")
    target_region = GLOBAL_ALIAS_REGION if scope.lower() == 'global' else region
    escaped_alias = alias_name.replace("'", "''")

    action = f"Committing IGNORE rule: '{alias_name}' -> {IGNORE_SENTINEL} for region '{target_region}'"
    sql_str = f"EXEC sp_AddTeamAlias @AliasName = '{escaped_alias}', @StandardizedName = '{IGNORE_SENTINEL}', @NewspaperRegion = '{target_region}';"

    if dry_run:
        logger.info(f"[DRY RUN] Would execute -- {action}")
        logger.info(f"[DRY RUN]   SQL: {sql_str}")
    else:
        logger.info(action)
        connection.execute(text(sql_str))
    return 'applied'


def main():
    parser = argparse.ArgumentParser(description="Apply Alias/Abbreviation/Ignore rules from the correction sheet to the database.")
    parser.add_argument('--final', action='store_true',
                         help="Commit Rule_Type='Ignore' rows to the database (as genuine one-offs only). "
                              "Without this flag, Ignore rows are read but not written -- safe to leave in the "
                              "sheet across multiple interim runs.")
    parser.add_argument('--dry-run', action='store_true',
                         help="Preview mode. Does NOT connect to the database at all -- just reads the sheet and "
                              "prints every SQL statement that would run (for both normal rules and, if combined "
                              "with --final, Ignore rules). Nothing is written anywhere.")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("=== DRY RUN: no database connection will be made, nothing will be written ===")

    logger.info(f"Reading completed correction sheet from: {SUGGESTION_CSV}")

    try:
        df = pd.read_csv(SUGGESTION_CSV, encoding='utf-8-sig')
    except FileNotFoundError:
        logger.error(f"FATAL: Suggestion sheet not found at {SUGGESTION_CSV}")
        return

    df['Final_Proper_Name'] = df['Final_Proper_Name'].fillna('')
    df['Rule_Type'] = df['Rule_Type'].fillna('Alias')

    is_ignore_mask = df['Rule_Type'].str.strip().str.lower() == 'ignore'
    normal_df = df[~is_ignore_mask].copy()
    normal_df = normal_df[normal_df['Final_Proper_Name'].str.strip() != '']
    ignore_df = df[is_ignore_mask].copy()

    if normal_df.empty and ignore_df.empty:
        logger.warning("No completed rows (Final_Proper_Name or Rule_Type=Ignore) found. Nothing to do.")
        return

    logger.info(f"Found {len(normal_df)} completed alias/abbreviation row(s) and {len(ignore_df)} Ignore row(s).")

    applied = 0
    skipped_bad_suffix = 0
    ignore_applied = 0
    ignore_deferred = 0
    ignore_refused_recurring = 0

    def run_all(connection):
        nonlocal applied, skipped_bad_suffix, ignore_applied, ignore_deferred, ignore_refused_recurring
        for _, row in normal_df.iterrows():
            result = apply_normal_rule(connection, row, dry_run=args.dry_run)
            if result == 'applied':
                applied += 1
            elif result == 'skipped_bad_suffix':
                skipped_bad_suffix += 1

        for _, row in ignore_df.iterrows():
            result = apply_ignore_rule(connection, row, args.final, dry_run=args.dry_run)
            if result == 'applied':
                ignore_applied += 1
            elif result == 'not_final':
                ignore_deferred += 1
            elif result == 'recurring':
                ignore_refused_recurring += 1

    try:
        if args.dry_run:
            # No engine, no connection, no pyodbc/ODBC driver needed at all --
            # everything below just logs what would happen.
            run_all(None)
        else:
            with get_engine().begin() as connection:
                logger.info("Successfully connected to the database to apply new rules.")
                run_all(connection)

        verb = "Would apply" if args.dry_run else "Successfully applied"
        logger.info(f"{'🔍' if args.dry_run else '✅'} {verb} {applied} alias/abbreviation rule(s) and {ignore_applied} Ignore rule(s).")
        if ignore_deferred:
            logger.info(f"⏸  {ignore_deferred} Ignore row(s) left uncommitted -- {'would need' if args.dry_run else 're-run with'} --final {'to commit them' if args.dry_run else 'when you are done reviewing this batch'}.")
        if ignore_refused_recurring:
            logger.warning(f"⚠️  {ignore_refused_recurring} Ignore row(s) {'would be' if args.dry_run else ''} refused because they recur across multiple clippings -- resolve these with a real name instead.")
        if skipped_bad_suffix:
            logger.warning(f"⚠️  {skipped_bad_suffix} row(s) {'would be' if args.dry_run else ''} skipped -- Final_Proper_Name doesn't end in a clean ' (XX)' state/province suffix. See warnings above, fix the sheet, and re-run.")
        if not args.dry_run:
            logger.info("You can now re-run 'master_scores_importer.py' to complete the import.")
        else:
            logger.info("Re-run without --dry-run (add --final if you're ready to commit Ignore rows) to actually apply these.")

    except Exception as e:
        logger.exception(f"FATAL: An error occurred while applying corrections to the database: {e}")


if __name__ == "__main__":
    main()
