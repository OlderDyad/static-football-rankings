"""
game_residuals.py  -- run on Windows (reads SQL Server; changes nothing)

Compares every game's actual margin with what the two teams' final ratings predict
(predicted = home margin rating - visitor margin rating; no home-field term, same as the
rating procedure) and lists the games that miss worst. Misnamed opponents (a local
"Centre" counted as Centre College), mistyped or swapped scores and wrong-season games
all show up here, whatever their dates.

  Residual  actual margin - predicted margin (home view)
  Z         residual / that season's residual spread (early seasons are noisier)
  Impact    rating points the game moves: |residual| / home games + |residual| / visitor games
            (a bad game against a 3-game team distorts more than one in a 12-game season)

Hints column (clues, not verdicts):
  scores swapped?     the result fits far better with the winner reversed
  undated             Aug-1 placeholder date (small-school / name-collision territory)
  far apart           the two schools are in different regions -- check the opponent's name
  few games           a team with 3 or fewer games that season
  huge score          a side scored 90+ or the total is 120+
Only games where both teams are rated and in the season's main network are checked.

Output: game_residuals.csv (top --top by Impact, default 3000)
Usage:  python game_residuals.py
        python game_residuals.py --from 1900 --to 1960 --top 1000
        python game_residuals.py --min-games 5      (leave out short-season teams)
"""
import argparse, csv, os
from collections import defaultdict
from statistics import pstdev

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))

REGION = {}
for reg, sts in {
    "New England": "ME NH VT MA RI CT",
    "Mid-Atlantic": "NY NJ PA DE MD DC",
    "South Atlantic": "VA WV NC SC GA FL",
    "South Central": "KY TN AL MS AR LA",
    "Great Lakes": "OH MI IN IL WI",
    "Plains": "MN IA MO KS NE SD ND",
    "Southwest": "TX OK NM AZ",
    "Mountain": "CO WY MT ID UT NV",
    "Pacific": "CA OR WA AK HI",
}.items():
    for st in sts.split():
        REGION[st] = reg
NEIGHBOR_REGIONS = {frozenset(x) for x in [
    ("New England", "Mid-Atlantic"), ("Mid-Atlantic", "South Atlantic"), ("Mid-Atlantic", "Great Lakes"),
    ("South Atlantic", "South Central"), ("South Central", "Great Lakes"), ("South Central", "Southwest"),
    ("Great Lakes", "Plains"), ("Plains", "Southwest"), ("Plains", "Mountain"), ("Mountain", "Pacific"),
    ("Mountain", "Southwest"), ("South Atlantic", "Great Lakes"), ("Southwest", "Pacific"), ("South Central", "Plains")]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="first", type=int, default=1869)
    ap.add_argument("--to", dest="last", type=int, default=2026)
    ap.add_argument("--top", type=int, default=3000)
    ap.add_argument("--min-games", type=int, default=0,
                    help="skip games where either team has fewer games (2-game teams always miss both ways)")
    a = ap.parse_args()

    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    print("Reading ratings, teams, games ...")
    rating = {}
    for s, t, m in cur.execute("""
        SELECT r.Season, r.Home, r.Avg_Of_Avg_Of_Home_Modified_Score
        FROM dbo.College_Rankings r
        JOIN (SELECT Season, MAX(Week) AS W FROM dbo.College_Rankings GROUP BY Season) x
          ON x.Season = r.Season AND x.W = r.Week
        WHERE r.Season BETWEEN ? AND ?""", a.first, a.last):
        if m is not None:
            rating[(t, s)] = float(m)
    state = {t: (st or "") for t, st in cur.execute("SELECT Team_Name, State FROM dbo.College_Team_Names")}
    cols = {r[0] for r in cur.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'College_Scores'")}
    neutral = "Neutral" if "Neutral" in cols else "CAST(0 AS BIT)"
    games = cur.execute(f"""
        SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score, {neutral}
        FROM dbo.College_Scores
        WHERE Season BETWEEN ? AND ? AND Home_Score IS NOT NULL AND Visitor_Score IS NOT NULL""",
                        a.first, a.last).fetchall()
    conn.close()

    ngames = defaultdict(int)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for g in games:
        ngames[(g[3], g[1])] += 1
        ngames[(g[5], g[1])] += 1
        ra, rb = find((g[3], g[1])), find((g[5], g[1]))
        if ra != rb:
            parent[ra] = rb
    size = defaultdict(int)
    for k in list(parent):
        size[find(k)] += 1
    main = {}
    for k in parent:
        r = find(k)
        if size[r] > size.get(main.get(k[1]), 0):
            main[k[1]] = r

    rows, by_season = [], defaultdict(list)
    for aid, s, d, h, hs, v, vs, n in games:
        if (h, s) not in rating or (v, s) not in rating:
            continue
        if find((h, s)) != main.get(s) or find((v, s)) != main.get(s):
            continue
        pred = rating[(h, s)] - rating[(v, s)]
        act = hs - vs
        res = act - pred
        by_season[s].append(res)
        rows.append([aid, s, d, h, hs, v, vs, bool(n), rating[(h, s)], rating[(v, s)], pred, act, res])
    spread = {s: (pstdev(r) or 1.0) for s, r in by_season.items() if len(r) > 1}

    out = []
    for aid, s, d, h, hs, v, vs, n, rh, rv, pred, act, res in rows:
        gh, gv = ngames[(h, s)], ngames[(v, s)]
        if min(gh, gv) < a.min_games:
            continue
        impact = abs(res) / gh + abs(res) / gv
        hints = []
        if abs(act) >= 7 and abs(-act - pred) < 0.3 * abs(act - pred):
            hints.append("scores swapped?")
        if d is None or (d.month == 8 and d.day == 1):
            hints.append("undated")
        rh_, rv_ = REGION.get(state.get(h, "")), REGION.get(state.get(v, ""))
        if rh_ and rv_ and rh_ != rv_ and frozenset((rh_, rv_)) not in NEIGHBOR_REGIONS:
            hints.append(f"far apart ({state.get(h)} vs {state.get(v)})")
        if min(gh, gv) <= 3:
            hints.append("few games")
        if max(hs, vs) >= 90 or hs + vs >= 120:
            hints.append("huge score")
        out.append([round(impact, 2), s, d, aid, h, hs, v, vs, "Y" if n else "", round(rh, 1), round(rv, 1),
                    round(pred, 1), act, round(res, 1), round(res / spread.get(s, 1.0), 2), gh, gv,
                    state.get(h, ""), state.get(v, ""), "; ".join(hints)])
    out.sort(key=lambda x: -x[0])
    with open(os.path.join(HERE, "game_residuals.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Impact", "Season", "Date", "Access_ID", "Home", "Home_Score", "Visitor", "Visitor_Score",
                    "Neutral", "Home_Rating", "Visitor_Rating", "Predicted", "Actual", "Residual", "Z",
                    "Home_Games", "Visitor_Games", "Home_State", "Visitor_State", "Hints"])
        w.writerows(out[:a.top])
    print(f"{len(rows):,} games checked; top {min(a.top, len(out)):,} written to game_residuals.csv")
    hinted = [x for x in out if x[19]]
    print(f"{sum(1 for x in out[:a.top] if 'swapped' in x[19])} 'scores swapped?' and "
          f"{sum(1 for x in out[:a.top] if 'far apart' in x[19])} 'far apart' among the top {a.top}")
    print("\nTop 30 by impact:")
    for x in out[:30]:
        print(f"  {x[0]:6.1f}  {x[1]} {x[4]:24.24s} {x[5]:>3}-{x[7]:<3} {x[6]:24.24s} pred {x[11]:+6.1f}  "
              f"res {x[13]:+6.1f}  games {x[15]}/{x[16]}  {x[19]}")


if __name__ == "__main__":
    main()
