#!/usr/bin/env python3
"""
find_hs_games_mislabeled_as_college.py

READ-ONLY investigation script. Makes zero writes to the database. This is
the mirror image of find_college_hs_mismatches.py.

That script looks for BARE, ambiguous names (e.g. "Alma (MI)") that might
secretly be the college. It structurally cannot catch the opposite mistake:
a name that's ALREADY labeled "X College (ST)" / "X University (ST)" in
HS_Scores because some alias rule resolved a raw clipping name straight to
the college -- but that alias is wrong for one particular game, because the
newspaper really meant the town's high school.

Real example found manually: "Hope College (MI)" has 6 games in HS_Scores.
5 of them are against other real colleges (Eastern Michigan, Alma College,
Ferris State...) -- a normal college schedule. But one, a 1930 game against
"Alma (MI)", turned out on image review to be two actual high schools. The
alias table maps raw "Hope" straight to "Hope College (MI)" with no way to
know that one specific clipping meant the high school in Hope Township, not
the college in Holland, MI.

This script:
  1. Finds every team name already labeled College/University in HS_Scores.
  2. Builds each one's normal opponent pattern (real colleges mostly play
     other real colleges).
  3. Flags individual games where the opponent breaks that pattern -- a
     bare/unqualified name instead of another college -- as a possible
     "this specific game was really two high schools" mistake.

Usage
-----
python find_hs_games_mislabeled_as_college.py
python find_hs_games_mislabeled_as_college.py --states MI --season-start 1920 --season-end 1935
python find_hs_games_mislabeled_as_college.py --min-suspicion 3 --output My_Review.csv
"""

import os
import argparse
import logging
import re
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RISK_LIST = os.path.join(SCRIPT_DIR, 'college_hs_risk_list.csv')
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, 'HS_Mislabeled_As_College_Review.csv')
DEFAULT_STATES = "NE,IA,SD,ND,MN,WI,MI,IL,KY,OH"

db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

# Same keyword logic as find_college_hs_mismatches.py -- kept local so this
# script runs standalone.
COLLEGE_KEYWORDS = ['college', 'university']
# Some real high schools carry "University"/"College" in their own proper
# name without being a college -- e.g. "University of Detroit Jesuit" is a
# Catholic prep HIGH SCHOOL. Don't count these as "labeled college."
HS_NAME_CARVEOUTS = ['jesuit', 'prep', 'academy', 'high school', 'catholic central']

# See find_college_hs_mismatches.py for the full rationale -- county name
# (e.g. "Georgetown Scott County (KY)") is a geographic qualifier, not a
# distinguishing school name, same role "Twp" plays elsewhere.
GENERIC_QUALIFIERS = r'(?:Twp\.?\b|Township\b|City\b|(?:[A-Za-z]+\s+)?(?:Co\.?|County)\b)'


def is_labeled_college(name):
    if not isinstance(name, str) or not name:
        return False
    lowered = name.lower()
    if any(kw in lowered for kw in HS_NAME_CARVEOUTS):
        return False
    return any(kw in lowered for kw in COLLEGE_KEYWORDS)


def load_risk_list(path, states):
    """Same bare-town-name risk list used by find_college_hs_mismatches.py --
    used here just as extra supporting evidence (opponent is a known
    college-town collision name), not as the primary filter."""
    if not os.path.exists(path):
        return pd.DataFrame(columns=['TownName', 'State', 'pattern'])
    df = pd.read_csv(path, encoding='utf-8-sig')
    df = df[df['State'].isin(states)].copy()
    df['pattern'] = df.apply(
        lambda r: re.compile(
            r'^' + re.escape(r['TownName']) + r'(?:\s+' + GENERIC_QUALIFIERS + r')*'
            r'\s*\(' + re.escape(r['State']) + r'\)$',
            re.IGNORECASE
        ),
        axis=1
    )
    return df


def opponent_matches_risk_list(name, risk_df):
    if not isinstance(name, str) or not name or risk_df.empty:
        return False
    return any(row['pattern'].match(name) for _, row in risk_df.iterrows())


def team_in_target_state(name, states):
    if not isinstance(name, str) or not name:
        return False
    return any(name.rstrip().endswith(f'({s})') for s in states)


def era_weight(season):
    """Same era curve as find_college_hs_mismatches.py -- college/HS
    crossover games were common early, essentially stopped by 1950."""
    if season < 1930:
        return 2, "Pre-1930 season -- college/HS crossover games were common this early."
    if season < 1945:
        return 1, "1930s/early-1940s season -- crossover games still happened, though less often than the 1920s."
    if season < 1950:
        return 0, "Late-1940s season -- crossover games were tapering off by this point (neutral, no adjustment)."
    return -2, "1950 or later -- college/HS crossover games had essentially stopped, so a labeled-college team's opponent list breaking pattern this late is more likely a data-entry quirk than a real crossover."


def fetch_labeled_college_teams(states, season_start, season_end):
    state_clause = " OR ".join([f"Home LIKE '%({s})' OR Visitor LIKE '%({s})'" for s in states])
    query = text(f"""
        SELECT DISTINCT Home AS TeamName FROM HS_Scores
        WHERE (Home LIKE '%College%' OR Home LIKE '%University%')
          AND Season >= :season_start AND Season <= :season_end AND ({state_clause})
        UNION
        SELECT DISTINCT Visitor AS TeamName FROM HS_Scores
        WHERE (Visitor LIKE '%College%' OR Visitor LIKE '%University%')
          AND Season >= :season_start AND Season <= :season_end AND ({state_clause})
    """)
    logger.info(f"Finding College/University-labeled team names for {states}, seasons {season_start}-{season_end}... (read-only)")
    df = pd.read_sql(query, engine, params={'season_start': season_start, 'season_end': season_end})
    names = [n for n in df['TeamName'].tolist() if is_labeled_college(n)]
    logger.info(f"  {len(names)} labeled-college team name(s) found.")
    return names


def fetch_all_games_for_teams(team_names):
    """Full history (any season) for these team names -- needed to build
    each one's normal opponent pattern. Still read-only."""
    if not team_names:
        return pd.DataFrame()
    names = list(team_names)
    placeholders = ", ".join([f":n{i}" for i in range(len(names))])
    params = {f"n{i}": n for i, n in enumerate(names)}
    query = text(f"""
        SELECT Season, Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores
        WHERE Home IN ({placeholders}) OR Visitor IN ({placeholders})
    """)
    return pd.read_sql(query, engine, params=params)


def main():
    parser = argparse.ArgumentParser(description="Read-only scan for HS games mislabeled as college (opposite direction of find_college_hs_mismatches.py).")
    parser.add_argument('--risk-list', default=DEFAULT_RISK_LIST)
    parser.add_argument('--states', default=DEFAULT_STATES)
    parser.add_argument('--season-start', type=int, default=1920)
    parser.add_argument('--season-end', type=int, default=1959)
    parser.add_argument('--min-suspicion', type=int, default=2, help="Only include rows scoring at/above this. Default 2.")
    parser.add_argument('--min-college-opponent-rate', type=float, default=0.5,
                         help="Only flag a team's off-pattern games if at least this fraction of its OTHER games are against other labeled colleges. Default 0.5.")
    parser.add_argument('--output', default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    states = [s.strip().upper() for s in args.states.split(',') if s.strip()]
    risk_df = load_risk_list(args.risk_list, states)

    labeled_teams = fetch_labeled_college_teams(states, args.season_start, args.season_end)
    if not labeled_teams:
        logger.info("No College/University-labeled team names found in this range. Nothing to check.")
        return

    history_df = fetch_all_games_for_teams(labeled_teams)

    review_rows = []
    for team in labeled_teams:
        as_home = history_df[history_df['Home'] == team]
        as_visitor = history_df[history_df['Visitor'] == team]

        games = []
        for _, r in as_home.iterrows():
            games.append({'Season': r['Season'], 'Date': r['Date'], 'Side': 'Home', 'Opponent': r['Visitor'],
                          'Team_Score': r['Home_Score'], 'Opp_Score': r['Visitor_Score'], 'Source': r['Source']})
        for _, r in as_visitor.iterrows():
            games.append({'Season': r['Season'], 'Date': r['Date'], 'Side': 'Visitor', 'Opponent': r['Home'],
                          'Team_Score': r['Visitor_Score'], 'Opp_Score': r['Home_Score'], 'Source': r['Source']})

        total_games = len(games)
        if total_games == 0:
            continue

        college_opponent_games = sum(1 for g in games if is_labeled_college(g['Opponent']))
        college_opponent_rate = college_opponent_games / total_games

        # Recurrence of each opponent -- informational only (shown, not
        # scored), since a recurring "off-pattern" opponent could mean either
        # a genuine long-running guarantee-game series OR that this team's
        # college label is wrong for ALL those games, not just one. Worth
        # your judgment call, not something to auto-weight either direction.
        opponent_seasons = {}
        for g in games:
            opponent_seasons.setdefault(g['Opponent'], set()).add(g['Season'])

        for g in games:
            if g['Season'] < args.season_start or g['Season'] > args.season_end:
                continue
            if is_labeled_college(g['Opponent']):
                continue  # matches the normal college-vs-college pattern, not suspicious

            # A team can get DISCOVERED via a game connection to a target
            # state (e.g. "University of Dayton (OH)" once played a
            # Michigan opponent) but then have most of its flagged games be
            # entirely out-of-scope (Ohio vs Kentucky, nothing to do with
            # Michigan). Require at least one side of THIS specific game to
            # actually be in a target state before reporting it.
            if not (team_in_target_state(team, states) or team_in_target_state(g['Opponent'], states)):
                continue

            if total_games < 3 or college_opponent_rate < args.min_college_opponent_rate:
                continue  # not enough evidence this team even HAS a "normal college schedule" to break from

            score = 2
            reasons = [f"'{team}' is labeled a college, but this opponent ('{g['Opponent']}') has no College/University "
                       f"qualifier -- breaks the team's usual pattern of playing other colleges "
                       f"({college_opponent_games}/{total_games} = {college_opponent_rate:.0%} of its games are vs other labeled colleges)."]

            if college_opponent_rate >= 0.8:
                score += 3
                reasons.append(f"Very strong college-only pattern ({college_opponent_rate:.0%}) makes this one exception more likely a mistake than a real game.")
            elif college_opponent_rate >= args.min_college_opponent_rate:
                score += 1

            if opponent_matches_risk_list(g['Opponent'], risk_df):
                score += 2
                reasons.append(f"Opponent '{g['Opponent']}' is itself a risk-listed college-town name -- may be a college-vs-college game where one side lost its 'College' qualifier during extraction.")

            recur = len(opponent_seasons.get(g['Opponent'], set()))
            if recur >= 3:
                reasons.append(f"This exact opponent recurs across {recur} different seasons -- could be a real long-running guarantee-game series, OR evidence the '{team}' label is wrong for all of these, not just this one. Worth checking more than one.")

            era_adj, era_reason = era_weight(g['Season'])
            if era_adj != 0:
                score += era_adj
                reasons.append(era_reason)

            if score < args.min_suspicion:
                continue

            review_rows.append({
                'Suspicion_Score': score,
                'Season': g['Season'],
                'Date': g['Date'],
                'Labeled_College_Team': team,
                'Side': g['Side'],
                'Opponent': g['Opponent'],
                'Team_Score': g['Team_Score'],
                'Opponent_Score': g['Opp_Score'],
                'College_Opponent_Rate': f"{college_opponent_games}/{total_games}",
                'Reasoning': " | ".join(reasons),
                'Source': g['Source'],
                'Your_Determination': '',  # e.g. "Real college game" / "Actually two HS -- rename" / "Needs image check"
                # If you confirm this needs a rename, put the exact replacement name here
                # (e.g. "Hope (MI)"). apply_college_hs_corrections.py only acts on rows
                # where BOTH Your_Determination and Corrected_Name are filled in.
                'Corrected_Name': '',
                'Notes': '',
            })

    if not review_rows:
        logger.info(f"No candidates scored >= {args.min_suspicion}. Nothing written.")
        return

    review_df = pd.DataFrame(review_rows).sort_values(by='Suspicion_Score', ascending=False)
    tmp = args.output + '.tmp'
    review_df.to_csv(tmp, index=False, encoding='utf-8-sig')
    os.replace(tmp, args.output)
    logger.info(f"Done. {len(review_df)} candidate game(s) written to {args.output} for your review.")
    logger.info("Nothing in HS_Scores was changed -- this is a read-only report.")


if __name__ == "__main__":
    main()
