#!/usr/bin/env python3
"""
diagnose_date_truncation.py

Turns the 2019/OK date-truncation discovery (found by accident, chasing a
repeat-offender team) into a systemic, reusable check for ANY state/season
-- so the next state onboarded (LA, TX, ...) doesn't have to get lucky the
same way.

THE BUG (confirmed on OK 2019, legacy Excel-macro-era MaxPreps import):
a two-digit day-of-month got truncated to its FIRST digit only --
day 11 -> "1", day 25 -> "2", day 29 -> "2", day 16 -> "1", day 30/31 -> "3".
Days 1-9 are never touched (already single-digit). So corruption can only
ever manifest as an EXCESS of games landing on day-of-month 1, 2, or 3
within a season, relative to what a normal ~Friday-night schedule would
produce.

TWO INDEPENDENT SIGNALS, exactly the two the OK investigation used --
requiring BOTH keeps this from crying wolf on a genuinely bunched
early-month schedule:
  1. SHARE  -- day-in-(1,2,3) rows are a bigger fraction of the season
              than random chance would predict (~3/30 ~= 10% if dates were
              uniform; real high school seasons cluster on Fridays, so the
              real baseline is usually lower than that, not higher).
  2. WEEKDAY DISTORTION -- real HS football is overwhelmingly Friday
              (some Thu/Sat). If day-in-(1,2,3) rows are genuinely Friday
              games, their weekday distribution should look like the
              season's OTHER rows. If those "day 1/2/3" rows are actually
              corrupted 11/12/13, 21/22/23, 29/30/31 etc., their true
              weekdays are essentially random relative to the calendar,
              so the Friday share collapses. A season where day-1/2/3
              rows are noticeably LESS Friday-heavy than the rest of that
              same season is the tell.

Scans every (State, Season) combination among "old-style" rows (Source
exactly 'www.maxpreps.com', literal/undated -- the same legacy-pipeline
signature that isolated the OK bug from the current, unaffected
maxpreps_scraper_db.py + FinalizeMaxPrepsData pipeline). Entirely
READ-ONLY -- a ranked report, nothing more. Confirmed-suspect seasons feed
into maxpreps_2019_date_truncation_fix.py-style repair (that script will
need generalizing past its current OK/2019 hardcoding once a real hit
shows up elsewhere -- deliberately not doing that speculatively before we
know it's needed).

ASSUMPTION TO VERIFY PER STATE: this trusts Source = 'www.maxpreps.com'
(exact, literal) as the legacy-pipeline marker, same as the original OK
diagnosis. If an older/different state used a different literal Source
string historically, adjust OLD_STYLE_SOURCE below or pass --source.

Usage:
  python diagnose_date_truncation.py --state LA
  python diagnose_date_truncation.py --state TX --min-games 30
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

OLD_STYLE_SOURCE = 'www.maxpreps.com'
MIN_GAMES_PER_SEASON = 20      # skip seasons too small to say anything statistically
SHARE_FLAG_THRESHOLD = 0.16    # day-in-(1,2,3) share above this is suspicious on its own
FRIDAY_DROP_FLAG = 0.20        # Friday-share(day123) below Friday-share(rest) by this much = suspicious


def fetch_old_style_rows(state, source):
    df = pd.read_sql(text("""
        SELECT Season, Date, DATENAME(WEEKDAY, Date) AS Weekday
        FROM HS_Scores
        WHERE (Home LIKE :pattern OR Visitor LIKE :pattern) AND Source = :source
    """), engine, params={'pattern': f'%({state})', 'source': source})
    df['Day'] = pd.to_datetime(df['Date']).dt.day
    return df


def scan_seasons(df, min_games):
    """REQUIRES the Friday-collapse signal -- validated against OK's known-real
    2019 case alongside 8 other candidates: the 6 that only showed an
    'elevated day-1/2/3 share' with NO Friday-collapse turned out to have
    HIGHER Friday share on day-1/2/3 than the rest of the season (the
    opposite of what truncation produces) -- just calendar coincidence, not
    corruption. Elevated share is real corroborating evidence, but only
    ever IN ADDITION to a genuine Friday-collapse, never on its own."""
    results = []
    for season, group in df.groupby('Season'):
        total = len(group)
        if total < min_games:
            continue
        day123 = group[group['Day'].isin([1, 2, 3])]
        rest = group[~group['Day'].isin([1, 2, 3])]
        if day123.empty or rest.empty:
            continue

        share = len(day123) / total
        fri_123 = (day123['Weekday'] == 'Friday').mean()
        fri_rest = (rest['Weekday'] == 'Friday').mean()
        friday_drop = fri_rest - fri_123

        if friday_drop < FRIDAY_DROP_FLAG:
            continue  # the only signal that's actually held up under validation

        flags = [f'Friday-share collapse ({fri_rest:.1%} -> {fri_123:.1%})']
        severity = 'Medium'
        if share >= SHARE_FLAG_THRESHOLD:
            flags.append(f'elevated day-1/2/3 share ({share:.1%})')
            severity = 'High'

        results.append({
            'Season': int(season), 'TotalGames': total, 'Day123Count': len(day123),
            'Day123Share': round(share, 3), 'FridayShare_Day123': round(fri_123, 3),
            'FridayShare_Rest': round(fri_rest, 3), 'FridayDrop': round(friday_drop, 3),
            'Flags': '; '.join(flags),
            'Severity': severity,
        })
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state', required=True, help="2-letter code, e.g. LA")
    parser.add_argument('--source', default=OLD_STYLE_SOURCE, help="Legacy-pipeline Source marker to scan (default: 'www.maxpreps.com')")
    parser.add_argument('--min-games', type=int, default=MIN_GAMES_PER_SEASON)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    df = fetch_old_style_rows(args.state, args.source)
    logger.info(f"{len(df)} old-style row(s) (Source='{args.source}') found for {args.state}.")

    if df.empty:
        logger.info(f"{args.state}: no old-style legacy-pipeline rows at all -- this state may never have gone "
                     f"through the vulnerable import path, or uses a different Source string (check with --source).")
        return

    report = scan_seasons(df, args.min_games)

    if report.empty:
        logger.info(f"{args.state}: no season showed the truncation signature. Clean on this check.")
    else:
        print(f"\n{len(report)} suspect season(s) for {args.state}:")
        print(report.sort_values(['Severity', 'FridayDrop'], ascending=[True, False]).to_string(index=False))
        high = (report['Severity'] == 'High').sum()
        logger.info(f"{args.state}: {high} High-severity (both signals present), "
                    f"{len(report) - high} Medium (one signal) -- worth a manual live-schedule spot check "
                    f"on the High ones before assuming it's real, same as the OK 2019 diagnosis.")

    if args.output:
        report.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {args.output}")


if __name__ == "__main__":
    main()
