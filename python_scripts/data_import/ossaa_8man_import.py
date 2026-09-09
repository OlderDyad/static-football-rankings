#!/usr/bin/env python3
"""
ossaa_8man_import.py

Seeds HS_Team_Level_History / HS_Team_Conference_History with Oklahoma's
CURRENT (2025-26) 8-man classification, sourced directly from OSSAA's
official Football 2025-26 Manual (Class B-I / B-II / C rosters -- Classes
B and C are OSSAA's entire 8-man tier; there is currently no separate
6-man division in their structure). This is ground truth from the
governing body, not inference -- a much stronger foundation than guessing
8-man status from game networks or team names.

WHY A TRANSITION SPLIT, NOT AN OVERWRITE: every OK team currently sits at
a single default row (PlayerLevel=11, Season_Begin=1970, Season_End=9999,
Is_Verified=0) -- nobody has done the historical "which year did this
team switch to 8-man" work yet (that's Part 2 of the established
onboarding workflow). This script only knows the CURRENT classification
for certain, so for each matched team it:
  1. Closes out the existing 11-man default row's Season_End to 2024
     (still Is_Verified=0 -- we're not claiming to know they were 11-man
     the whole 1970-2024 span, just leaving that unresolved default in
     place until the real historical work happens).
  2. Inserts a NEW row: PlayerLevel=8, Season_Begin=2025, Season_End=9999,
     Is_Verified=1 (this part IS verified -- straight from the official
     2025-26 OSSAA manual).
Same split pattern for HS_Team_Conference_History (Faux_Conference
'OK - 8-Man' vs the existing 'OK - Statewide' default).

MATCHING: OSSAA's roster uses short, sometimes differently-formatted
names ("Sharon-Mutual/Taloga" vs. this DB's "Mutual Sharon-Mutual (OK)",
"Deer Creek-Lamont" vs. "Deer Creek-Lamont-Billings (OK)", "Texhoma/
Goodwell" vs. whatever this DB calls that co-op). Exact-after-
normalization matches are auto-confident; everything else is a fuzzy
suggestion that needs a human pick before anything is written --
consistent with every other name-matching step in this project. This
script is READ-ONLY by default (produces a review CSV); --apply only
writes rows CONFIRMED in that reviewed CSV (a Confirmed=1/0 column you
edit by hand), never fuzzy guesses automatically.

Usage:
  python ossaa_8man_import.py --output ossaa_8man_match_review.csv   # produce the review CSV
  # ... open the CSV, review/correct the MatchedDBName column, set Confirmed=1 for rows to apply ...
  python ossaa_8man_import.py --input ossaa_8man_match_review.csv --apply
"""

import argparse
import difflib
import logging
import re

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

CURRENT_SEASON_BEGIN = 2025
PRIOR_SEASON_END = 2024

# (OSSAA name, Division) -- transcribed from the OSSAA Football 2025-26 Manual, Class B/C rosters.
OSSAA_8MAN = [
    # Class B-I
    ("Garber", "B-I"), ("Laverne", "B-I"), ("OK Bible Academy", "B-I"),
    ("Pioneer-Pleasant Vale", "B-I"), ("Pond Creek-Hunter", "B-I"), ("Turpin", "B-I"),
    ("Burns Flat-Dill City", "B-I"), ("Central High", "B-I"), ("Empire", "B-I"),
    ("Hollis", "B-I"), ("Snyder", "B-I"), ("Waurika", "B-I"),
    ("Cave Springs", "B-I"), ("Depew", "B-I"), ("Drumright", "B-I"),
    ("Foyil", "B-I"), ("Porum", "B-I"), ("Yale", "B-I"),
    ("Caddo", "B-I"), ("Canadian", "B-I"), ("Dewar", "B-I"),
    ("Keota", "B-I"), ("Quinton", "B-I"), ("Savanna", "B-I"),
    # Class B-II
    ("Boise City", "B-II"), ("Canton", "B-II"), ("Okeene", "B-II"),
    ("Ringwood", "B-II"), ("Seiling", "B-II"), ("Shattuck", "B-II"),
    ("Alex", "B-II"), ("Cyril", "B-II"), ("Strother", "B-II"),
    ("Thackerville", "B-II"), ("Weleetka", "B-II"), ("Wetumka", "B-II"),
    ("Cherokee", "B-II"), ("Covington-Douglas", "B-II"), ("Coyle", "B-II"),
    ("Davenport", "B-II"), ("Olive", "B-II"), ("Waukomis", "B-II"),
    ("Arkoma", "B-II"), ("Copan", "B-II"), ("Gans", "B-II"),
    ("Webbers Falls", "B-II"), ("Wesleyan Christian", "B-II"), ("Wilson (Henryetta)", "B-II"),
    # Class C
    ("Balko/Forgan", "C"), ("Beaver", "C"), ("Buffalo", "C"),
    ("Kremlin-Hillsdale", "C"), ("Sharon-Mutual/Taloga", "C"), ("Timberlake", "C"),
    ("Tyrone", "C"), ("Waynoka", "C"),
    ("Bray-Doyle", "C"), ("Corn Bible Academy", "C"), ("Geary", "C"),
    ("Grandfield", "C"), ("Mountain View-Gotebo", "C"), ("Ryan", "C"),
    ("Temple", "C"), ("Tipton", "C"),
    ("Billings", "C"), ("Bluejacket", "C"), ("Deer Creek-Lamont", "C"),
    ("Medford", "C"), ("Oaks Mission", "C"), ("South Coffeyville", "C"),
    ("Watts", "C"), ("Welch", "C"),
    ("Bowlegs", "C"), ("Fox", "C"), ("Graham-Dustin", "C"),
    ("Maud", "C"), ("Maysville", "C"), ("Midway", "C"), ("Paoli", "C"), ("Sasakwa", "C"),
]


def normalize(name):
    """Lowercase, strip state tag/punctuation, split hyphens/slashes into
    space-separated tokens so 'Sharon-Mutual/Taloga' and 'Mutual
    Sharon-Mutual (OK)' both reduce to comparable token sets."""
    name = re.sub(r'\(OK\)\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[/\-.]', ' ', name)
    name = re.sub(r'[^a-z0-9\s]', '', name.lower())
    return re.sub(r'\s+', ' ', name).strip()


def fetch_ok_teams():
    df = pd.read_sql(text("""
        SELECT TeamName, PlayerLevel, Season_Begin, Season_End, Is_Verified
        FROM HS_Team_Level_History
        WHERE TeamName LIKE '%(OK)'
    """), engine)
    return df


def match_teams(ok_teams_df):
    db_names = ok_teams_df['TeamName'].tolist()
    norm_to_db = {}
    for name in db_names:
        norm_to_db.setdefault(normalize(name), []).append(name)

    results = []
    for ossaa_name, division in OSSAA_8MAN:
        norm_ossaa = normalize(ossaa_name)
        ossaa_tokens = set(norm_ossaa.split())

        # exact normalized match
        if norm_ossaa in norm_to_db:
            for db_name in norm_to_db[norm_ossaa]:
                results.append({'OSSAAName': ossaa_name, 'Division': division, 'MatchedDBName': db_name,
                                 'MatchType': 'ExactNormalized', 'Score': 1.0, 'Confirmed': 1})
            continue

        # token-overlap + difflib fuzzy fallback, top 3 candidates
        scored = []
        for db_name in db_names:
            db_norm = normalize(db_name)
            db_tokens = set(db_norm.split())
            if not ossaa_tokens or not db_tokens:
                continue
            overlap = len(ossaa_tokens & db_tokens) / len(ossaa_tokens | db_tokens)
            ratio = difflib.SequenceMatcher(None, norm_ossaa, db_norm).ratio()
            combined = (overlap + ratio) / 2
            scored.append((combined, db_name))
        scored.sort(reverse=True)

        if scored and scored[0][0] >= 0.5:
            best_score, best_name = scored[0]
            results.append({'OSSAAName': ossaa_name, 'Division': division, 'MatchedDBName': best_name,
                             'MatchType': 'Fuzzy', 'Score': round(best_score, 3), 'Confirmed': 0})
        else:
            results.append({'OSSAAName': ossaa_name, 'Division': division, 'MatchedDBName': None,
                             'MatchType': 'NoMatch', 'Score': 0.0, 'Confirmed': 0})

    return pd.DataFrame(results)


def apply_transitions(confirmed_df, dry_run=True):
    confirmed = confirmed_df[(confirmed_df['Confirmed'] == 1) & confirmed_df['MatchedDBName'].notna()]
    if confirmed.empty:
        logger.info("No confirmed rows to apply.")
        return

    if dry_run:
        logger.info(f"[DRY RUN] Would apply {len(confirmed)} team(s) to 8-man for {CURRENT_SEASON_BEGIN}+.")
        for _, row in confirmed.iterrows():
            logger.info(f"  {row['MatchedDBName']} (matched from OSSAA '{row['OSSAAName']}', Class {row['Division']})")
        return

    with engine.begin() as conn:
        for _, row in confirmed.iterrows():
            team = row['MatchedDBName']

            # Level history: close out the open-ended 11-man default, insert the verified 8-man row
            conn.execute(text("""
                UPDATE HS_Team_Level_History
                SET Season_End = :prior_end
                WHERE TeamName = :team AND PlayerLevel = 11 AND Season_End = 9999
            """), {'prior_end': PRIOR_SEASON_END, 'team': team})
            conn.execute(text("""
                INSERT INTO HS_Team_Level_History (TeamName, PlayerLevel, Season_Begin, Season_End, Is_Verified)
                VALUES (:team, 8, :begin, 9999, 1)
            """), {'team': team, 'begin': CURRENT_SEASON_BEGIN})

            # Conference history: same split, OK - Statewide -> OK - 8-Man
            conn.execute(text("""
                UPDATE HS_Team_Conference_History
                SET Season_End = :prior_end
                WHERE TeamName = :team AND Faux_Conference = 'OK - Statewide' AND Season_End = 9999
            """), {'prior_end': PRIOR_SEASON_END, 'team': team})
            conn.execute(text("""
                INSERT INTO HS_Team_Conference_History (TeamName, Faux_Conference, Season_Begin, Season_End, Is_Verified)
                VALUES (:team, 'OK - 8-Man', :begin, 9999, 1)
            """), {'team': team, 'begin': CURRENT_SEASON_BEGIN})

    logger.info(f"{len(confirmed)} team(s) transitioned to 8-man ({CURRENT_SEASON_BEGIN}+), logged as verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', default=None, help="Write the match-review CSV here (dry-run/match mode)")
    parser.add_argument('--input', default=None, help="Read a reviewed CSV back in (Confirmed column edited by hand)")
    parser.add_argument('--apply', action='store_true', help="Apply Confirmed=1 rows from --input")
    args = parser.parse_args()

    if args.apply:
        if not args.input:
            parser.error("--apply requires --input <reviewed CSV>")
        df = pd.read_csv(args.input)
        apply_transitions(df, dry_run=False)
        return

    ok_teams = fetch_ok_teams()
    logger.info(f"{len(ok_teams)} OK team(s) currently in HS_Team_Level_History.")

    matched = match_teams(ok_teams)
    counts = matched['MatchType'].value_counts()
    print("\n=== Match type breakdown ===")
    print(counts.to_string())
    print(f"\n{matched.to_string(index=False)}")

    if args.output:
        matched.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {args.output}. Review MatchedDBName for Fuzzy/NoMatch rows, "
                     f"set Confirmed=1 for rows to apply, then re-run with --input {args.output} --apply.")


if __name__ == "__main__":
    main()
