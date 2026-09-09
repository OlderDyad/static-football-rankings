#!/usr/bin/env python3
"""
maxpreps_2019_date_truncation_fix.py

Repairs a specific, now-confirmed date-corruption bug found ONLY in the
2019 season's MaxPreps import batch (Source = 'www.maxpreps.com', the
old, undated source string -- pre-dates the FinalizeMaxPrepsData rewrite
that now writes a per-game '/YY-YY/'-dated source URL and whose date
parsing was independently verified safe). That 2019 batch's date-parsing
step kept only the FIRST CHARACTER of a two-digit day-of-month string, so
a game played on the 10th-19th of a month landed on day "1", the 20th-29th
landed on day "2", and the 30th/31st landed on day "3" -- always with the
correct month and year, just the wrong day.

Confirmed against Tulsa Bishop Kelley's real MaxPreps schedule:
  Durant:            stored 10/1  -> real 10/11
  Ada:               stored 10/2  -> real 10/25
  Bishop McGuinness: stored 11/2  -> real 11/29
And independently confirmed at the statistical level: 2019 is the only
season (2004-2023) where the share of Source='www.maxpreps.com' rows
landing on a single-digit day (41.2%) is far above the ~24-34% baseline
every other season falls in, and within 2019 the weekday distribution of
single-digit-day rows is wildly abnormal (16.7% Tuesday, 7.4% Wednesday)
versus the two-digit-day rows (84% Friday) -- exactly what you'd expect
if a chunk of ordinary Friday games got relabeled onto day 1/2/3 and
inherited whatever weekday that day happened to fall on that month.

WHY ONLY DAY 1/2/3: the truncation can only ever produce day 1, 2, or 3
(first character of "10"-"19" is "1", of "20"-"29" is "2", of "30"/"31"
is "3") -- days 4-9 are structurally impossible outputs of this bug, and
were confirmed clean (overwhelmingly Friday) in the underlying data.

CANDIDATE SET: rows with Source='www.maxpreps.com', Season=2019,
DAY(Date) IN (1,2,3), AND a weekday that's essentially never a real HS
football day (Monday/Tuesday/Wednesday/Sunday) -- the conservative,
confirmed-bad subset. Rows already showing Friday/Saturday/Thursday on a
day-1/2/3 date are deliberately left OUT of the candidate set -- we can't
tell those apart from a genuinely correct day-1/2/3 game, and this script
never touches a row it can't make a confident case about.

RECOVERY LOGIC: the truncated day came from a known 10-day source range
that month (10-19, 20-29, or 30-31). HS football is overwhelmingly played
on Fridays. If EXACTLY ONE day in that range is a Friday, that's proposed
as the correction (High-UniqueFriday). If there's no Friday but exactly
one Thursday/Saturday, that's proposed instead, at lower confidence
(Medium-UniqueThuSat). Otherwise (multiple Friday candidates, or none and
multiple/no Thu-Sat candidates) the row is left Ambiguous -- a 10-day
range often contains 2 Fridays, and guessing wrong would be worse than
not fixing it. These need a live MaxPreps schedule pull, same as
Durant/Bishop McGuinness were resolved by hand.

Validated against the 3 known-correct answers above: Ada resolved
correctly as High-UniqueFriday (only 10/25 is a Friday in the 20-29
range); Durant and Bishop McGuinness both correctly fell into Ambiguous
(each had 2 Friday candidates in their range: 10/11 & 10/18 for Durant,
11/22 & 11/29 for McGuinness) rather than being guessed wrong. That's the
intended, safe failure mode -- ambiguous cases are surfaced for a live
check, never silently mis-corrected.

This script is READ-ONLY by default. --apply only ever touches
High-UniqueFriday and Medium-UniqueThuSat rows (Date field only, via the
same ID-scoped, audit-logged update pattern every other fix in this
project uses, logged to HS_Scores_Change_Log). Ambiguous rows are never
auto-applied, only listed for manual/live-schedule follow-up.

Usage:
  python maxpreps_2019_date_truncation_fix.py --state OK                   # dry-run report
  python maxpreps_2019_date_truncation_fix.py --state OK --output ok_2019_dates.csv
  python maxpreps_2019_date_truncation_fix.py --state OK --apply           # apply High/Medium rows only
"""

import argparse
import calendar
import logging
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

SOURCE_RANGE = {1: (10, 19), 2: (20, 29), 3: (30, 31)}
ALL_WEEKDAYS = ['Friday', 'Saturday', 'Thursday', 'Monday', 'Tuesday', 'Wednesday', 'Sunday']


def compute_bad_weekdays(state, max_count=0):
    """Determines which weekdays are 'essentially never' a real HS football
    day IN THIS STATE, from its own clean (DAY 4-9, structurally impossible
    for the truncation bug to touch) 2019 rows -- rather than assuming a
    hardcoded national list. Oklahoma is solidly Friday-culture (472
    Friday / 18 Thursday / 6 Saturday / 0 everything else in its own day
    4-9 baseline), but some regions -- parts of the Northeast, for
    instance -- play more Tuesday/Wednesday games due to shared-field
    scheduling. A weekday that's rightly 'corruption-only' in Oklahoma
    could be a normal, real game day elsewhere, so this calibrates fresh
    per state instead of reusing OK's list.

    Uses an EXACT-ZERO-COUNT rule (max_count=0), not a percentage
    threshold -- a first pass with a 3% cutoff wrongly swept Saturday
    (6 games, 1.2% of OK's baseline) into the corruption-candidate bucket
    alongside Monday/Tuesday/Wednesday/Sunday (all genuinely 0 games).
    Saturday is a real, if rare, OK game day (jamborees, weather makeups)
    -- any nonzero count, however small, means the day is sometimes
    legitimately used and shouldn't be auto-flagged. Only a weekday that
    NEVER happens even once in the clean baseline is safe to treat as
    corruption-only."""
    query = text("""
        SELECT DATENAME(WEEKDAY, Date) AS Weekday, COUNT(*) AS Cnt
        FROM HS_Scores
        WHERE Source = 'www.maxpreps.com' AND Season = 2019
          AND (Home LIKE :pattern OR Visitor LIKE :pattern)
          AND DAY(Date) BETWEEN 4 AND 9
        GROUP BY DATENAME(WEEKDAY, Date)
    """)
    df = pd.read_sql(query, engine, params={'pattern': f'%{state}'})
    total = int(df['Cnt'].sum())
    if total == 0:
        logger.warning(f"No clean (day 4-9) baseline rows found for {state} -- can't calibrate, "
                        f"falling back to the OK-derived default (Mon/Tue/Wed/Sun).")
        return {'Monday', 'Tuesday', 'Wednesday', 'Sunday'}

    shares = dict(zip(df['Weekday'], df['Cnt']))
    logger.info(f"{state} clean-baseline weekday counts (day 4-9, n={total}): " +
                ", ".join(f"{wd}={shares.get(wd, 0)} ({100.0 * shares.get(wd, 0) / total:.1f}%)" for wd in ALL_WEEKDAYS))

    bad = {wd for wd in ALL_WEEKDAYS if shares.get(wd, 0) <= max_count}
    logger.info(f"{state}: treating {sorted(bad)} as corruption-candidate weekdays "
                f"(<= {max_count} occurrence(s) in clean baseline).")
    return bad


def fetch_candidates(state, bad_weekdays):
    placeholders = ", ".join(f":wd{i}" for i in range(len(bad_weekdays)))
    query = text(f"""
        SELECT ID, Season, Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores
        WHERE Source = 'www.maxpreps.com' AND Season = 2019
          AND (Home LIKE :pattern OR Visitor LIKE :pattern)
          AND DAY(Date) IN (1, 2, 3)
          AND DATENAME(WEEKDAY, Date) IN ({placeholders})
    """)
    params = {'pattern': f'%{state}'}
    params.update({f'wd{i}': wd for i, wd in enumerate(bad_weekdays)})
    df = pd.read_sql(query, engine, params=params)
    df['ID'] = df['ID'].astype(str)
    return df


def propose_correction(current_date):
    """Returns (proposed_date_or_None, confidence_label, all_fri_thu_sat_candidates)."""
    year, month, day = current_date.year, current_date.month, current_date.day
    lo, hi = SOURCE_RANGE[day]
    days_in_month = calendar.monthrange(year, month)[1]
    hi = min(hi, days_in_month)

    candidates = [date(year, month, d) for d in range(lo, hi + 1)]
    weekday_of = {d: d.strftime('%A') for d in candidates}

    fridays = [d for d in candidates if weekday_of[d] == 'Friday']
    fri_thu_sat = [d for d in candidates if weekday_of[d] in ('Friday', 'Thursday', 'Saturday')]

    if len(fridays) == 1:
        return fridays[0], 'High-UniqueFriday', fri_thu_sat
    if len(fridays) == 0:
        thu_sat = [d for d in candidates if weekday_of[d] in ('Thursday', 'Saturday')]
        if len(thu_sat) == 1:
            return thu_sat[0], 'Medium-UniqueThuSat', fri_thu_sat
    return None, 'Ambiguous-NeedsLiveCheck', fri_thu_sat


def build_report(df):
    rows = []
    for r in df.itertuples(index=False):
        current_date = r.Date if isinstance(r.Date, date) else pd.to_datetime(r.Date).date()
        proposed, confidence, fri_thu_sat = propose_correction(current_date)
        rows.append({
            'ScoresID': r.ID,
            'CurrentDate': current_date,
            'CurrentWeekday': current_date.strftime('%A'),
            'Home': r.Home, 'Visitor': r.Visitor,
            'Home_Score': r.Home_Score, 'Visitor_Score': r.Visitor_Score,
            'ProposedDate': proposed,
            'ProposedWeekday': proposed.strftime('%A') if proposed else None,
            'Confidence': confidence,
            'CandidateDates': ', '.join(f"{d} ({d.strftime('%a')})" for d in fri_thu_sat),
        })
    return pd.DataFrame(rows)


def apply_corrections(report_df, dry_run=True):
    fixable = report_df[report_df['Confidence'].isin(['High-UniqueFriday', 'Medium-UniqueThuSat'])]
    if fixable.empty:
        logger.info("No High/Medium confidence rows to apply.")
        return

    if dry_run:
        logger.info(f"[DRY RUN] Would apply {len(fixable)} correction(s) "
                     f"({(fixable['Confidence'] == 'High-UniqueFriday').sum()} High, "
                     f"{(fixable['Confidence'] == 'Medium-UniqueThuSat').sum()} Medium). "
                     f"{len(report_df) - len(fixable)} Ambiguous row(s) left untouched.")
        return

    applied = 0
    with engine.begin() as conn:
        for _, row in fixable.iterrows():
            reason = (f"2019 MaxPreps date-truncation bug: stored date {row['CurrentDate']} "
                      f"({row['CurrentWeekday']}) corrected to {row['ProposedDate']} "
                      f"({row['ProposedWeekday']}) -- {row['Confidence']}, unique Fri/Thu/Sat "
                      f"match within the truncation source-day range for that month. "
                      f"See maxpreps_2019_date_truncation_fix.py docstring for methodology.")
            conn.execute(text("""
                INSERT INTO HS_Scores_Change_Log
                    (ScoresID, FieldChanged, OldValue, NewValue, Reason, Script)
                VALUES (:id, 'Date', :old, :new, :reason, 'maxpreps_2019_date_truncation_fix.py')
            """), {'id': row['ScoresID'], 'old': str(row['CurrentDate']),
                   'new': str(row['ProposedDate']), 'reason': reason})
            conn.execute(text("UPDATE HS_Scores SET Date = :new WHERE ID = :id"),
                         {'new': row['ProposedDate'], 'id': row['ScoresID']})
            applied += 1
    logger.info(f"{applied} correction(s) applied and logged to HS_Scores_Change_Log.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state', required=True, help="2-letter code, e.g. OK")
    parser.add_argument('--output', default=None, help="Also write the full report to this CSV path")
    parser.add_argument('--apply', action='store_true', help="Apply High/Medium confidence corrections (default is dry-run/report only)")
    args = parser.parse_args()

    state = f"({args.state.strip().strip('()').upper()})"
    bad_weekdays = compute_bad_weekdays(state)
    df = fetch_candidates(state, bad_weekdays)
    logger.info(f"{len(df)} candidate row(s) found for {state} (Source=www.maxpreps.com, Season=2019, "
                f"day 1-3, weekday in {sorted(bad_weekdays)}).")
    if df.empty:
        return

    report = build_report(df)
    counts = report['Confidence'].value_counts()
    print(f"\n=== Confidence breakdown for {state} ===")
    print(counts.to_string())
    print(f"\n{report.to_string(index=False)}")

    if args.output:
        report.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {args.output}")

    apply_corrections(report, dry_run=not args.apply)
    if not args.apply:
        print("\n(Review only -- no changes made. Re-run with --apply to fix High/Medium confidence rows. "
              "Ambiguous rows need a live MaxPreps schedule check, same as Durant/Bishop McGuinness earlier.)")


if __name__ == "__main__":
    main()
