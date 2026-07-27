#!/usr/bin/env python3
"""
check_source_clipping.py

READ-ONLY. Pulls every HS_Scores row that came from one specific source
file (one newspaper clipping/page). Useful when a clipping like an "OHIO
COLLEGIATE" scoreboard lists a bunch of games at once -- if one team from
that clipping got imported with a missing "College"/"University" qualifier
(caught by find_college_hs_mismatches.py), the others from the SAME
clipping are worth a quick look too, since whatever caused the one miss
(a bare town name in the original text, no explicit "College" spelled out)
could easily have affected its neighbors in the same clipping.

Usage
-----
python check_source_clipping.py --source The_Plain_Dealer_1934_11_11_32.csv
"""

import argparse
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)


def main():
    parser = argparse.ArgumentParser(description="Read-only: list every HS_Scores game from one source file.")
    parser.add_argument('--source', required=True, help="Exact Source filename, e.g. The_Plain_Dealer_1934_11_11_32.csv")
    args = parser.parse_args()

    query = text("""
        SELECT ID, Season, Date, Home, Visitor, Home_Score, Visitor_Score, Forfeit, Source
        FROM HS_Scores
        WHERE Source = :source
        ORDER BY Home, Visitor
    """)
    df = pd.read_sql(query, engine, params={'source': args.source})

    if df.empty:
        logger.info(f"No HS_Scores rows found with Source = '{args.source}'.")
        return

    logger.info(f"{len(df)} game(s) imported from '{args.source}':\n")
    for _, r in df.iterrows():
        print(f"  [{r['ID']}] {r['Season']} {r['Date']}: {r['Home']} {r['Home_Score']} - "
              f"{r['Visitor_Score']} {r['Visitor']}")


if __name__ == "__main__":
    main()
