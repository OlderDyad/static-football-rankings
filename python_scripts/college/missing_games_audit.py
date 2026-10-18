"""
missing_games_audit.py  -- run on Windows (reads SQL Server; changes nothing)

Finds college team-seasons that are probably missing games, so data gathering can be
targeted (record books / media guides, newspapers, school sites).

For every College team-season (Kind = 'College' in College_Team_Names) it compares the
games on file with two expectations:
  Own   - median games of the same team in nearby seasons (+/- --window, needs 3+ seasons)
  Peer  - median games that season of College teams in the same division
          (division from College_Team_Names.Division_History; era-wide if none)
Expected = the larger of the two. A season is flagged when it is at least --min-missing
games short AND has no more than --share of the expected games.

It also flags GAP seasons: no games on file, but games in the seasons on both sides.
War years (1917-1919, 1942-1946) and 2020 are labelled -- many programs really paused.

Outputs (python_scripts/college/):
  missing_games_by_season.csv   flagged team-seasons, highest priority first
  missing_games_by_team.csv     per program: total estimated missing games, flagged
                                seasons as ranges -- the list for record-book hunting
Priority favours seasons that matter for the ratings: more games missing, a higher
rating rank, and few distinct opponents (weakly tied into the network).

Usage:  python missing_games_audit.py
        python missing_games_audit.py --from 1900 --to 1999 --min-missing 2
"""
import argparse, csv, os, re
from collections import defaultdict
from statistics import median

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))
PAUSE_YEARS = set(range(1917, 1920)) | set(range(1942, 1947)) | {2020}


def division_map(history):
    """'1892-1936 NCAA; 1937-1972 Small College; 1973-2026 III' -> {season: division}"""
    out = {}
    for part in (history or "").split(";"):
        m = re.match(r"\s*(\d{4})-(\d{4})\s+(.+?)\s*$", part)
        if m:
            for s in range(int(m.group(1)), int(m.group(2)) + 1):
                out[s] = m.group(3)
    return out


def ranges(years):
    years = sorted(years)
    out, start, prev = [], None, None
    for y in years:
        if start is None:
            start = prev = y
        elif y == prev + 1:
            prev = y
        else:
            out.append(f"{start}" if start == prev else f"{start}-{prev}")
            start = prev = y
    if start is not None:
        out.append(f"{start}" if start == prev else f"{start}-{prev}")
    return ", ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="first", type=int, default=1869)
    ap.add_argument("--to", dest="last", type=int, default=2025)
    ap.add_argument("--window", type=int, default=4)
    ap.add_argument("--min-missing", type=int, default=3)
    ap.add_argument("--share", type=float, default=0.6)
    a = ap.parse_args()

    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    print("Reading games ...")
    rows = cur.execute("SELECT Season, Home, Visitor FROM dbo.College_Scores WHERE Season BETWEEN ? AND ?",
                       a.first - a.window, a.last + a.window).fetchall()
    print("Reading teams and ratings ...")
    teams = {t: (k, st, division_map(h)) for t, k, st, h in cur.execute(
        "SELECT Team_Name, Kind, State, Division_History FROM dbo.College_Team_Names").fetchall()}
    rat = cur.execute("""
        SELECT r.Season, r.Home,
               ISNULL(r.Combined_Rating, 0.958 * r.Avg_Of_Avg_Of_Home_Modified_Score + 2.791)
        FROM dbo.College_Rankings r
        WHERE r.Season BETWEEN ? AND ?
          AND r.Week = (SELECT MAX(Week) FROM dbo.College_Rankings x WHERE x.Season = r.Season)
    """, a.first, a.last).fetchall()
    conn.close()

    games = defaultdict(int)                  # (team, season) -> games on file
    opps = defaultdict(set)
    for s, h, v in rows:
        for t, o in ((h, v), (v, h)):
            games[(t, s)] += 1
            opps[(t, s)].add(o)
    seasons_of = defaultdict(set)
    for t, s in games:
        seasons_of[t].add(s)

    rank = {}
    by_season = defaultdict(list)
    for s, t, c in rat:
        if c is not None and games.get((t, s), 0) >= 3:
            by_season[s].append((float(c), t))
    for s, lst in by_season.items():
        n = len(lst)
        for i, (_, t) in enumerate(sorted(lst, reverse=True), 1):
            rank[(t, s)] = (i, n)

    def is_college(t):
        return teams.get(t, ("",))[0] == "College"

    def div(t, s):
        return teams.get(t, ("", "", {}))[2].get(s, "")

    # peer medians: College teams by (season, division); fallback by season
    peer = defaultdict(list)
    for (t, s), g in games.items():
        if is_college(t):
            peer[(s, div(t, s))].append(g)
            peer[(s, "*")].append(g)
    peer_med = {k: median(v) for k, v in peer.items() if len(v) >= 5}

    flagged = []
    for t, seas in seasons_of.items():
        if not is_college(t):
            continue
        lo, hi = max(min(seas), a.first), min(max(seas), a.last)
        for s in range(lo, hi + 1):
            g = games.get((t, s), 0)
            near = [games[(t, y)] for y in range(s - a.window, s + a.window + 1)
                    if y != s and (t, y) in games]
            own = median(near) if len(near) >= 3 else None
            d = div(t, s)
            pm = peer_med.get((s, d)) or peer_med.get((s, "*"))
            if g == 0:
                before = any((t, y) in games for y in (s - 1, s - 2))
                after = any((t, y) in games for y in (s + 1, s + 2))
                if not (before and after):
                    continue
                kind = "GAP (war/pandemic year)" if s in PAUSE_YEARS else "GAP"
            else:
                kind = "SHORT"
            exp = max(x for x in (own, pm, 0) if x is not None)
            missing = exp - g
            if missing < a.min_missing or (g > 0 and g > a.share * exp):
                continue
            r, n = rank.get((t, s), (None, None))
            n_opp = len(opps.get((t, s), ()))
            # priority: games missing x rating weight x weak-link weight; pauses down-weighted
            rating_w = 1 + (2 * (1 - (r - 1) / n) if r else 0)          # 1 (bottom) .. 3 (top)
            link_w = 1.5 if n_opp <= 2 else 1.0
            pause_w = 0.3 if s in PAUSE_YEARS else 1.0
            prio = round(missing * rating_w * link_w * pause_w, 2)
            flagged.append([prio, t, teams[t][1] or "", s, d, kind, g, own if own is not None else "",
                            pm if pm is not None else "", round(exp, 1), round(missing, 1),
                            n_opp, f"{r}/{n}" if r else ""])

    flagged.sort(key=lambda x: -x[0])
    with open(os.path.join(HERE, "missing_games_by_season.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Priority", "Team", "State", "Season", "Division", "Type", "Games_On_File",
                    "Own_Median_Nearby", "Peer_Median", "Expected", "Est_Missing", "Distinct_Opponents",
                    "Rating_Rank"])
        w.writerows(flagged)

    by_team = defaultdict(list)
    for x in flagged:
        by_team[x[1]].append(x)
    team_rows = []
    for t, xs in by_team.items():
        real = [x for x in xs if "war" not in x[5]]
        if not real:
            continue
        tot = sum(x[10] for x in real)
        team_rows.append([round(sum(x[0] for x in real), 1), t, teams[t][1] or "",
                          teams[t][2].get(max(seasons_of[t]), "") if teams[t][2] else "",
                          len(real), round(tot), sum(1 for x in real if x[5] == "GAP"),
                          ranges(x[3] for x in real)])
    team_rows.sort(key=lambda x: -x[0])
    with open(os.path.join(HERE, "missing_games_by_team.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Priority", "Team", "State", "Latest_Division", "Seasons_Flagged", "Est_Missing_Games",
                    "Gap_Seasons", "Flagged_Seasons"])
        w.writerows(team_rows)

    tot = sum(x[10] for x in flagged if "war" not in x[5])
    print(f"\n{len(flagged):,} team-seasons flagged ({sum(1 for x in flagged if x[5] == 'GAP'):,} gap seasons); "
          f"about {tot:,.0f} games estimated missing across {len(team_rows):,} programs.")
    print("Written: missing_games_by_season.csv, missing_games_by_team.csv")
    dec = defaultdict(float)
    for x in flagged:
        if "war" not in x[5]:
            dec[x[3] // 10 * 10] += x[10]
    print("\nEstimated missing games by decade:")
    for d in sorted(dec):
        print(f"  {d}s {dec[d]:8,.0f}")
    print("\nTop 25 programs (best targets for record books / media guides):")
    for x in team_rows[:25]:
        print(f"  {x[1]:28s} {x[2]:2s} {x[3][:14]:14s} {x[4]:3d} seasons ~{x[5]:4d} games  {x[7][:60]}")
    print("\nTop 15 single seasons:")
    for x in flagged[:15]:
        print(f"  {x[3]} {x[1]:28s} {x[5]:6s} on file {x[6]:2d}, expected {x[9]:4}, rank {x[12]}")


if __name__ == "__main__":
    main()
