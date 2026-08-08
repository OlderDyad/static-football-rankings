#!/usr/bin/env python3
"""
find_mangled_state_suffixes.py

READ-ONLY. Scans every distinct team name currently in HS_Scores (Home and
Visitor combined) and flags any name whose last five characters don't match
the clean ' (XX)' state/province suffix format -- a space, an open paren,
exactly two UPPERCASE letters, and a close paren. Uses the exact same check
apply_corrections.py now enforces going forward for brand-new aliases; this
script finds the ones that got into HS_Scores before that check existed.

Prompted by a cross-tab query that surfaced a handful of mangled suffixes
mixed in with ~60 clean ones, e.g. '(TN(', 'IA )', 'L) B', ' (KY', ' (SC',
' (SD', 'NC)'.

Only checks HS_Scores, not any alias table -- ratings get corrected the
next time the ratings calculator runs off cleaned-up HS_Scores, and a
mangled alias that never gets used just sits there unused going forward.

Usage
-----
python find_mangled_state_suffixes.py
python find_mangled_state_suffixes.py --output Mangled_State_Suffixes.csv
"""

import os
import argparse
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from apply_corrections import bad_state_suffix_reason, IGNORE_SENTINEL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, 'Mangled_State_Suffixes.csv')

db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)


def fetch_distinct_scores_names():
    """Every distinct Home/Visitor name in HS_Scores, with a game count."""
    query = text("""
        SELECT Name, SUM(Cnt) AS Game_Count FROM (
            SELECT Home AS Name, COUNT(*) AS Cnt FROM HS_Scores GROUP BY Home
            UNION ALL
            SELECT Visitor AS Name, COUNT(*) AS Cnt FROM HS_Scores GROUP BY Visitor
        ) t
        GROUP BY Name
    """)
    logger.info("Querying HS_Scores for every distinct Home/Visitor team name... (read-only)")
    return pd.read_sql(query, engine)


def main():
    parser = argparse.ArgumentParser(description="Read-only: find HS_Scores team names with a malformed state/province suffix.")
    parser.add_argument('--output', default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    scores_df = fetch_distinct_scores_names()
    logger.info(f"  {len(scores_df)} distinct team name(s) found in HS_Scores.")
    scores_df = scores_df[scores_df['Name'] != IGNORE_SENTINEL].copy()  # shouldn't appear here, but be defensive
    scores_df['Suffix_Problem'] = scores_df['Name'].apply(lambda n: bad_state_suffix_reason(str(n)))
    mangled = scores_df[scores_df['Suffix_Problem'].notna()].copy()

    if mangled.empty:
        logger.info("No malformed state suffixes found in HS_Scores. Everything's clean.")
        return

    mangled = mangled.sort_values(by='Game_Count', ascending=False)
    tmp = args.output + '.tmp'
    mangled[['Name', 'Game_Count', 'Suffix_Problem']].to_csv(tmp, index=False, encoding='utf-8-sig')
    os.replace(tmp, args.output)

    logger.info(f"{len(mangled)} mangled name(s) found, written to {args.output} for your review:\n")
    for _, r in mangled.iterrows():
        print(f"  [{r['Game_Count']} row(s)] {r['Name']!r} -- {r['Suffix_Problem']}")


if __name__ == "__main__":
    main()
