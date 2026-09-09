#!/usr/bin/env python3
"""
edmond_oca_jv_split.py

Edmond Oklahoma Christian Academy (OK) has ~2x the plausible varsity game
count in HS_Scores for every season 2003-2022 (confirmed by hand for 2017:
26 DB rows vs. an actual 11-2 / 13-game varsity season per MaxPreps). The
extra rows are real games, just at a JV/sub-varsity level, imported under
the same standardized team name as varsity ("Edmond Oklahoma Christian
Academy (OK)") instead of being split out the way other schools already
are in this DB (e.g. "Tulsa Central JV (OK)", "Sallisaw Central JV (OK)").

This script, for each season:
  1. Pulls every HS_Scores row where Home or Visitor is
     "Edmond Oklahoma Christian Academy (OK)".
  2. Fetches that season's real varsity schedule directly from MaxPreps
     (server-rendered HTML table -- no JS execution needed) at
     https://www.maxpreps.com/ok/edmond/oklahoma-christian-academy-eagles/football/{YY}-{YY+1}/schedule/
  3. Matches each DB row to the varsity schedule by (date, our_score,
     opponent_score). A match = confirmed varsity, no action needed.
     No match = flagged as non-varsity (JV/2nd team), a rename candidate.
  4. Prints a per-season summary table. No writes happen unless --apply
     is passed, and even then each flagged row is fixed individually via
     apply_fix()-equivalent logic (ID-scoped, full audit trail in
     HS_Scores_Change_Log) -- never a blanket rename by team name.

Usage:
  python edmond_oca_jv_split.py --start 2003 --end 2022                  # review only, no writes
  python edmond_oca_jv_split.py --start 2003 --end 2022 --show-flagged   # also print flagged row detail
  python edmond_oca_jv_split.py --start 2003 --end 2022 --apply          # apply renames after review
  python edmond_oca_jv_split.py --start 2017 --end 2017 --show-flagged   # single-season spot check
"""

import argparse
import logging
import re
import time
from datetime import date

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

TEAM_NAME = "Edmond Oklahoma Christian Academy (OK)"
JV_NAME = "Edmond Oklahoma Christian Academy JV (OK)"
SCHEDULE_URL_TMPL = "https://www.maxpreps.com/ok/edmond/oklahoma-christian-academy-eagles/football/{yy1}-{yy2}/schedule/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_varsity_schedule(season):
    """Returns a set of (month, day, our_score, their_score) tuples for the
    real varsity schedule of the given season, scraped from MaxPreps'
    server-rendered schedule table. Returns None if the page couldn't be
    fetched/parsed (so the caller can skip that season rather than assume
    zero varsity games)."""
    yy1 = season % 100
    yy2 = (season + 1) % 100
    url = SCHEDULE_URL_TMPL.format(yy1=f"{yy1:02d}", yy2=f"{yy2:02d}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        logger.warning(f"Season {season}: request failed ({e}) -- skipping, DB rows left unclassified.")
        return None

    if resp.status_code != 200:
        logger.warning(f"Season {season}: HTTP {resp.status_code} at {url} -- skipping, DB rows left unclassified.")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table tbody tr")
    if not rows:
        logger.warning(f"Season {season}: no schedule table rows found at {url} -- skipping, DB rows left unclassified.")
        return None

    games = set()
    for row in rows:
        date_link = row.select_one("td a[aria-label]")
        result_span = row.select_one("span.result")
        score_span = row.select_one("span.score")
        if date_link is None or result_span is None or score_span is None:
            continue

        m = re.search(r"(\d{1,2})/(\d{1,2})", date_link.get_text())
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))

        score_text = score_span.get_text().strip()
        sm = re.search(r"(\d+)-(\d+)", score_text)
        if not sm:
            continue
        s1, s2 = int(sm.group(1)), int(sm.group(2))
        result = result_span.get_text().strip().upper()  # 'W' or 'L' (or 'T')

        # score_span is always "winner_score-loser_score" regardless of
        # which side OCA was on; use the W/L result to assign our_score.
        if result == 'W':
            our_score, their_score = s1, s2
        elif result == 'L':
            our_score, their_score = s2, s1
        else:
            # tie -- s1 == s2, order doesn't matter
            our_score, their_score = s1, s2

        games.add((month, day, our_score, their_score))

    return games


def get_db_rows(season):
    """All HS_Scores rows for the team in this season, with our_score /
    their_score normalized regardless of which side (Home/Visitor) OCA
    was on."""
    df = pd.read_sql(text("""
        SELECT ID, Date, Season, Home, Home_Score, Visitor, Visitor_Score
        FROM HS_Scores
        WHERE Season = :season
          AND (Home = :team OR Visitor = :team)
    """), engine, params={'season': season, 'team': TEAM_NAME})

    if df.empty:
        return df

    df['is_home'] = df['Home'] == TEAM_NAME
    df['our_score'] = df.apply(lambda r: r['Home_Score'] if r['is_home'] else r['Visitor_Score'], axis=1)
    df['their_score'] = df.apply(lambda r: r['Visitor_Score'] if r['is_home'] else r['Home_Score'], axis=1)
    df['field'] = df['is_home'].apply(lambda h: 'Home' if h else 'Visitor')
    return df


def classify_season(season):
    """Returns (matched_df, flagged_df, unverified) for one season.
    unverified=True means the MaxPreps fetch failed and nothing in this
    season should be touched."""
    db_rows = get_db_rows(season)
    if db_rows.empty:
        return db_rows, db_rows, False

    varsity_games = fetch_varsity_schedule(season)
    if varsity_games is None:
        return db_rows.iloc[0:0], db_rows.iloc[0:0], True

    def is_varsity(row):
        d = row['Date']
        key = (d.month, d.day, int(row['our_score']), int(row['their_score']))
        return key in varsity_games

    db_rows['is_varsity'] = db_rows.apply(is_varsity, axis=1)
    matched = db_rows[db_rows['is_varsity']]
    flagged = db_rows[~db_rows['is_varsity']]
    return matched, flagged, False


def apply_jv_rename(scores_id, field, reason, dry_run=False):
    with engine.begin() as conn:
        current = conn.execute(text(f"SELECT {field} AS val FROM HS_Scores WHERE ID = :id"),
                                {'id': scores_id}).fetchone()
        if current is None:
            logger.warning(f"No HS_Scores row found for ID {scores_id} -- skipped.")
            return False
        old_value = current.val
        preview = f"{scores_id}: SET {field} = '{JV_NAME}' (was '{old_value}')"

        if str(old_value) == JV_NAME:
            logger.info(f"{scores_id}: {field} already '{JV_NAME}' -- no change needed.")
            return False

        if dry_run:
            logger.info(f"[DRY RUN] {preview}")
            return True

        conn.execute(text("""
            INSERT INTO HS_Scores_Change_Log
                (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
            VALUES (:id, NULL, :field, :old, :new, :reason, :script)
        """), {'id': scores_id, 'field': field, 'old': str(old_value), 'new': JV_NAME,
               'reason': reason, 'script': 'edmond_oca_jv_split.py'})

        conn.execute(text(f"UPDATE HS_Scores SET {field} = :new WHERE ID = :id"),
                     {'new': JV_NAME, 'id': scores_id})

    logger.info(preview + "  [logged to HS_Scores_Change_Log]")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--end', type=int, required=True)
    parser.add_argument('--show-flagged', action='store_true', help="Print full row detail for flagged (non-varsity) rows")
    parser.add_argument('--apply', action='store_true', help="Actually rename flagged rows to the JV standardized name (default is dry-run/review only)")
    args = parser.parse_args()

    summary_rows = []
    all_flagged = []

    for season in range(args.start, args.end + 1):
        matched, flagged, unverified = classify_season(season)
        if unverified:
            summary_rows.append({'Season': season, 'DBRows': len(get_db_rows(season)),
                                  'Varsity_Matched': 'N/A', 'Flagged_NonVarsity': 'N/A',
                                  'Note': 'MaxPreps fetch failed -- skipped'})
            time.sleep(0.5)
            continue

        summary_rows.append({'Season': season, 'DBRows': len(matched) + len(flagged),
                              'Varsity_Matched': len(matched), 'Flagged_NonVarsity': len(flagged),
                              'Note': ''})
        if len(flagged):
            all_flagged.append(flagged)
        time.sleep(0.5)  # be polite to MaxPreps

    summary_df = pd.DataFrame(summary_rows)
    print("\n=== Edmond OCA varsity/JV classification summary ===")
    print(summary_df.to_string(index=False))

    if not all_flagged:
        print("\nNo flagged (non-varsity) rows found.")
        return

    flagged_df = pd.concat(all_flagged, ignore_index=True)
    print(f"\nTotal flagged rows across {args.start}-{args.end}: {len(flagged_df)}")

    if args.show_flagged:
        print("\n=== Flagged (non-varsity) row detail ===")
        print(flagged_df[['ID', 'Date', 'Season', 'Home', 'Home_Score', 'Visitor', 'Visitor_Score']].to_string(index=False))

    if args.apply:
        print(f"\nApplying JV rename to {len(flagged_df)} rows...")
        applied = 0
        for _, row in flagged_df.iterrows():
            reason = (f"Edmond OCA varsity/JV split: {row['Date']} game not found on real MaxPreps "
                      f"varsity schedule for season {row['Season']} -- reclassified as JV/sub-varsity.")
            if apply_jv_rename(row['ID'], row['field'], reason, dry_run=False):
                applied += 1
        print(f"Applied: {applied} / {len(flagged_df)}")
    else:
        print("\n(Review only -- no changes made. Re-run with --apply once you've checked --show-flagged output.)")


if __name__ == "__main__":
    main()