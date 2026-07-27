#!/usr/bin/env python3
"""
find_college_hs_mismatches.py

READ-ONLY investigation script. Makes zero writes to the database and zero
edits to any staged import file. It only queries HS_Scores and writes a new
review CSV for you to look at.

Problem: your import convention is "no suffix = high school varsity", but a
lot of small Midwest towns (1920-1959) also had a college of the same name
(Albion -> Albion College vs Albion High). When a newspaper clipping listed
just the bare town name without "College"/"Frosh"/etc., that game could have
been imported as the high school when it was really the college (or, less
often, the reverse).

This script:
  1. Loads a curated list of town/college name collisions (college_hs_risk_list.csv).
  2. Pulls every HS_Scores game for those town names, in your target states
     and season range.
  3. Scores each game for "this might actually be the college, not the HS"
     using opponent identity, that team's own scoring pattern, and how
     often this exact matchup recurs across seasons.
  4. Writes a sorted review CSV. YOU decide what's actually wrong -- this
     never touches HS_Scores.

Usage
-----
python find_college_hs_mismatches.py
python find_college_hs_mismatches.py --states MI,WI,IL --season-start 1920 --season-end 1940
python find_college_hs_mismatches.py --min-suspicion 2 --output My_Review.csv
"""

import os
import argparse
import logging
import re
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RISK_LIST = os.path.join(SCRIPT_DIR, 'college_hs_risk_list.csv')
# Deliberately NOT the Staged folder -- master_scores_importer.py sweeps up
# every .csv in Staged (except New_Alias_Suggestions.csv) as score data, and
# this review sheet is not score data.
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, 'College_HS_Mismatch_Review.csv')

DEFAULT_STATES = "NE,IA,SD,ND,MN,WI,MI,IL,KY,OH"

db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)


# Generic administrative qualifiers that don't identify a distinct school --
# a name that's just the town plus one of these is still a bare/ambiguous
# reference to "the" school in that town, not a specifically-named separate
# institution. Deliberately NOT genuinely-distinguishing words like
# "Central," "Roosevelt," "Community," or a saint's name -- those mean a
# real, specific, unambiguous school (see MI smoke-test findings: Kalamazoo
# and Ypsilanti are cities with several distinctly-named high schools, and
# matching any "Kalamazoo ..." name as if it collided with Kalamazoo College
# was pure noise). Kentucky/Ohio newspapers often identify a team by county
# rather than city -- and the county's own proper name is part of that
# geographic label, not a distinguishing SCHOOL name, e.g. real example
# found in KY output: "Georgetown Scott County (KY)" is still just "the"
# Georgetown high school, described by its county, same role "Twp" plays
# for Albion. So "[ProperNoun] Co/County" is allowed as a qualifier unit too,
# not just the bare word alone.
GENERIC_QUALIFIERS = r'(?:Twp\.?\b|Township\b|City\b|(?:[A-Za-z]+\s+)?(?:Co\.?|County)\b)'


def load_risk_list(path, states):
    df = pd.read_csv(path, encoding='utf-8-sig')
    df = df[df['State'].isin(states)].copy()
    # Precompute a regex per row: matches the bare town name, optionally
    # followed by one or more generic qualifiers (Twp, County, City, etc.),
    # then the state suffix -- e.g. "Albion (MI)" or "Albion Twp (MI)" match,
    # but "Albion Central (MI)" or "Kalamazoo St. Augustine (MI)" do NOT,
    # since those are proper names of a specific, unambiguous school.
    df['pattern'] = df.apply(
        lambda r: re.compile(
            r'^' + re.escape(r['TownName']) + r'(?:\s+' + GENERIC_QUALIFIERS + r')*'
            r'\s*\(' + re.escape(r['State']) + r'\)$',
            re.IGNORECASE
        ),
        axis=1
    )
    return df


# Modifiers your project already uses to mark a non-varsity-HS team. If a
# name already carries one of these, it's not ambiguous -- it's already
# correctly disambiguated, so it's not part of what we're hunting for here.
ALREADY_DISAMBIGUATED_KEYWORDS = [
    'college', 'university', 'frosh', 'freshman', 'freshmen', 'junior high',
    'alumni', 'club', 'pro', ' jv', ' j.v', 'lightweights', ' b team',
    ' reserve', ' reserves', 'varsity', 'seminary', 'normal school',
    'teachers', 'scrubs', 'subs', 'seconds',
]
# Deliberately NOT added: 'col.' / 'u.' -- bare short abbreviations are too
# easy to false-match inside messy OCR'd 1920s-era text (a stray period near
# an unrelated "u" is common), and 'college'/'university' (full words) already
# cover the case these were meant for.

# Keywords that specifically mean "this name is already unambiguously a
# college/university" -- used for the opponent-side high-confidence trigger
# below. Narrower than ALREADY_DISAMBIGUATED_KEYWORDS (which also covers
# Frosh/JV/Alumni-type HS-level modifiers that don't imply "college").
COLLEGE_KEYWORDS = ['college', 'university']

# Some real high schools carry "University" or "College" in their own proper
# name without being a college at all -- e.g. "University of Detroit Jesuit"
# is a Catholic prep HIGH SCHOOL, not the University of Detroit's team. If
# one of these also appears, don't trust the bare college-keyword match.
HS_NAME_CARVEOUTS = ['jesuit', 'prep', 'academy', 'high school', 'catholic central']


def is_already_disambiguated(name):
    lowered = name.lower()
    return any(kw in lowered for kw in ALREADY_DISAMBIGUATED_KEYWORDS)


def build_combined_risk_pattern(risk_df):
    """
    One alternation of every individual per-town risk-list pattern, e.g.
    "(?:^Albion...\\(MI\\)$)|(?:^Alma...\\(MI\\)$)|...". Used for a single
    vectorized pass over a whole column instead of testing every name
    against all N risk-list patterns one at a time in a Python loop.

    This matters at full 10-state/40-season scale: ~200K games x up to 71
    patterns x 2 sides (Home/Visitor) is tens of millions of individual
    re.match() calls done row-by-row via games_df.iterrows() -- that's what
    actually takes minutes, not the SQL query itself. pandas' .str.match()
    does the equivalent work as one C-level vectorized pass instead.
    """
    if risk_df.empty:
        return re.compile(r'(?!)')  # matches nothing
    return re.compile('|'.join(f'(?:{p.pattern})' for p in risk_df['pattern']), re.IGNORECASE)


def build_disambiguation_pattern():
    """Vectorized equivalent of is_already_disambiguated() for a whole column at once."""
    return re.compile('|'.join(re.escape(kw) for kw in ALREADY_DISAMBIGUATED_KEYWORDS), re.IGNORECASE)


def is_unambiguous_college(name):
    if not isinstance(name, str) or not name:
        return False
    lowered = name.lower()
    if any(kw in lowered for kw in HS_NAME_CARVEOUTS):
        return False
    return any(kw in lowered for kw in COLLEGE_KEYWORDS)


def name_matches_risk_list(name, risk_df):
    """Return the risk_list row (as a dict) if this standardized team name
    matches a risk-list town+state collision AND isn't already carrying a
    disambiguating modifier, else None."""
    if not isinstance(name, str) or not name:
        return None
    if is_already_disambiguated(name):
        return None
    for _, row in risk_df.iterrows():
        if row['pattern'].match(name):
            return row.to_dict()
    return None


def fetch_state_season_games(states, season_start, season_end):
    state_clause = " OR ".join([f"Home LIKE '%({s})' OR Visitor LIKE '%({s})'" for s in states])
    query = text(f"""
        SELECT ID, Season, Date, Home, Visitor, Home_Score, Visitor_Score, Forfeit, Source
        FROM HS_Scores
        WHERE Season >= :season_start AND Season <= :season_end
          AND ({state_clause})
    """)
    logger.info(f"Querying HS_Scores for {states}, seasons {season_start}-{season_end}... (read-only)")
    df = pd.read_sql(query, engine, params={'season_start': season_start, 'season_end': season_end})
    logger.info(f"  {len(df)} games in range.")
    return df


def fetch_all_games_for_teams(team_names):
    """Full history (any season/state) for a specific set of standardized
    team names -- used to build each flagged team's own scoring baseline
    and opponent-recurrence pattern. Still read-only."""
    if not team_names:
        return pd.DataFrame()
    names = list(team_names)
    placeholders = ", ".join([f":n{i}" for i in range(len(names))])
    params = {f"n{i}": n for i, n in enumerate(names)}
    query = text(f"""
        SELECT Season, Date, Home, Visitor, Home_Score, Visitor_Score
        FROM HS_Scores
        WHERE Home IN ({placeholders}) OR Visitor IN ({placeholders})
    """)
    return pd.read_sql(query, engine, params=params)


def build_team_baselines(history_df, team_names):
    """
    For each flagged team name, compute:
      - mean/std margin (from that team's perspective, win positive)
      - the set of opponents faced and how many distinct seasons each
        opponent was faced (a real HS conference rival recurs for years;
        a one-time "guarantee game" opponent doesn't)
    """
    baselines = {}
    for team in team_names:
        as_home = history_df[history_df['Home'] == team]
        as_visitor = history_df[history_df['Visitor'] == team]
        margins = pd.concat([
            (as_home['Home_Score'] - as_home['Visitor_Score']),
            (as_visitor['Visitor_Score'] - as_visitor['Home_Score']),
        ])
        opponent_seasons = {}
        for _, r in as_home.iterrows():
            opponent_seasons.setdefault(r['Visitor'], set()).add(r['Season'])
        for _, r in as_visitor.iterrows():
            opponent_seasons.setdefault(r['Home'], set()).add(r['Season'])
        baselines[team] = {
            'mean_margin': margins.mean() if len(margins) else 0,
            'std_margin': margins.std() if len(margins) > 1 else 0,
            'game_count': len(margins),
            'opponent_seasons': opponent_seasons,  # opponent -> set of seasons faced
        }
    return baselines


def score_candidate(row, side, opponent, team_score, opp_score, risk_df, baseline, season_start):
    """Returns (suspicion_score, reasons_list) for one flagged game."""
    score = 0
    reasons = []

    if is_unambiguous_college(opponent):
        score += 4
        reasons.append(f"Opponent '{opponent}' is ALREADY explicitly labeled a college/university -- a bare town-name team playing a confirmed college is very likely that same college's varsity/frosh, not the high school.")
    else:
        opp_risk_hit = name_matches_risk_list(opponent, risk_df)
        if opp_risk_hit:
            score += 3
            reasons.append(f"Opponent '{opponent}' is ALSO a risk-listed college-town name -- may be a college-vs-college guarantee game misfiled as HS, or confirms both sides need a look.")

    if pd.notna(team_score) and pd.notna(opp_score) and baseline['game_count'] >= 3:
        # Home_Score/Visitor_Score come back as float64 from pandas whenever
        # the column has any NULLs elsewhere in the result set, even though
        # these two values are present -- cast to int before using the ':d'
        # format code below, or it raises on a bare float.
        margin = int(team_score) - int(opp_score)
        std = baseline['std_margin']
        if std and std > 0:
            z = abs((margin - baseline['mean_margin']) / std)
            if z >= 1.5:
                score += 2
                reasons.append(f"Margin ({margin:+d}) is a {z:.1f}-sigma outlier vs this team's usual margin ({baseline['mean_margin']:.1f} avg).")

    seasons_faced = baseline['opponent_seasons'].get(opponent, set())
    if len(seasons_faced) <= 1:
        score += 1
        reasons.append("This opponent pairing is a one-off (not a recurring year-over-year matchup) -- more consistent with a one-time guarantee game than a conference rivalry.")
    elif len(seasons_faced) >= 3:
        score -= 2
        reasons.append(f"Recurs across {len(seasons_faced)} different seasons vs this same opponent -- looks like a real, stable HS conference rivalry.")

    return score, reasons


def era_weight(season):
    """
    College varsity/frosh teams playing high schools was common in the
    earliest decades of this dataset and had essentially stopped by 1950.
    Rather than a flat "pre-1935" bonus, weight suspicion by how plausible a
    crossover game actually was in that specific season -- this keeps the
    review sheet focused on the era where mistakes are actually likely,
    instead of spreading suspicion evenly across 40 seasons.
    """
    if season < 1930:
        return 2, "Pre-1930 season -- college/HS crossover games were common this early."
    if season < 1945:
        return 1, "1930s/early-1940s season -- crossover games still happened, though less often than the 1920s."
    if season < 1950:
        return 0, "Late-1940s season -- crossover games were tapering off by this point (neutral, no adjustment)."
    return -2, "1950 or later -- college/HS crossover games had essentially stopped by this point, so this is most likely a genuine same-name high school, not a misfiled college game."


def main():
    parser = argparse.ArgumentParser(description="Read-only scan for possible college/HS name-collision mismatches in HS_Scores.")
    parser.add_argument('--risk-list', default=DEFAULT_RISK_LIST)
    parser.add_argument('--states', default=DEFAULT_STATES, help="Comma-separated state codes, e.g. MI,WI,IL")
    parser.add_argument('--season-start', type=int, default=1920)
    parser.add_argument('--season-end', type=int, default=1959)
    parser.add_argument('--min-suspicion', type=int, default=1, help="Only include rows scoring at/above this. Default 1 (drop the obvious non-issues).")
    parser.add_argument('--output', default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    states = [s.strip().upper() for s in args.states.split(',') if s.strip()]
    risk_df = load_risk_list(args.risk_list, states)
    logger.info(f"Loaded {len(risk_df)} risk-list town/college entries for states: {', '.join(states)}")

    games_df = fetch_state_season_games(states, args.season_start, args.season_end)
    if games_df.empty:
        logger.warning("No games found in range. Nothing to check.")
        return

    # Find every game where Home or Visitor matches a risk-list town name.
    # Vectorized: one combined alternation regex tested against the whole
    # Home/Visitor column in a single pandas .str.match()/.str.contains()
    # pass, instead of looping every one of ~200K games through all N
    # risk-list patterns one at a time (name_matches_risk_list() is still
    # used below, per-candidate, where the small resulting subset makes the
    # per-pattern loop cheap again).
    combined_risk_pattern = build_combined_risk_pattern(risk_df)
    disambig_pattern = build_disambiguation_pattern()

    home = games_df['Home'].fillna('').astype(str)
    visitor = games_df['Visitor'].fillna('').astype(str)

    home_hit_mask = home.str.match(combined_risk_pattern) & ~home.str.contains(disambig_pattern, regex=True)
    visitor_hit_mask = visitor.str.match(combined_risk_pattern) & ~visitor.str.contains(disambig_pattern, regex=True)

    candidates = []
    for g in games_df[home_hit_mask].itertuples(index=False):
        candidates.append({'flagged_team': g.Home, 'side': 'Home', 'opponent': g.Visitor,
                            'team_score': g.Home_Score, 'opp_score': g.Visitor_Score,
                            'Season': g.Season, 'Date': g.Date, 'Source': g.Source})
    for g in games_df[visitor_hit_mask].itertuples(index=False):
        candidates.append({'flagged_team': g.Visitor, 'side': 'Visitor', 'opponent': g.Home,
                            'team_score': g.Visitor_Score, 'opp_score': g.Home_Score,
                            'Season': g.Season, 'Date': g.Date, 'Source': g.Source})

    if not candidates:
        logger.info("No risk-list name matches found in this range. Nothing to review.")
        return

    logger.info(f"{len(candidates)} candidate game-sides matched the risk list. Pulling full history for baselines...")

    flagged_team_names = {c['flagged_team'] for c in candidates}
    history_df = fetch_all_games_for_teams(flagged_team_names)
    baselines = build_team_baselines(history_df, flagged_team_names)

    review_rows = []
    for c in candidates:
        baseline = baselines[c['flagged_team']]
        score, reasons = score_candidate(
            c, c['side'], c['opponent'], c['team_score'], c['opp_score'],
            risk_df, baseline, args.season_start
        )
        era_adjustment, era_reason = era_weight(c['Season'])
        if era_adjustment != 0:
            score += era_adjustment
            reasons.append(era_reason)

        if score < args.min_suspicion:
            continue

        review_rows.append({
            'Suspicion_Score': score,
            'Season': c['Season'],
            'Date': c['Date'],
            'Flagged_Team': c['flagged_team'],
            'Flagged_Team_Side': c['side'],
            'Opponent': c['opponent'],
            'Flagged_Team_Score': c['team_score'],
            'Opponent_Score': c['opp_score'],
            'Team_Historical_Avg_Margin': round(baseline['mean_margin'], 1),
            'Team_Historical_Game_Count': baseline['game_count'],
            'Reasoning': " | ".join(reasons),
            'Source': c['Source'],
            # Left blank for you to fill in:
            'Your_Determination': '',   # e.g. "HS - correct" / "College - rename" / "Needs image check"
            # If you confirm this needs a rename, put the exact replacement name here
            # (e.g. "Detroit University of Detroit Jesuit (MI)"). apply_college_hs_corrections.py
            # only acts on rows where BOTH Your_Determination and Corrected_Name are filled in.
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
