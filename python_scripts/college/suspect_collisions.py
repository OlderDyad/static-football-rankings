"""
suspect_collisions.py  -- run on Windows (reads SQL Server; changes nothing)

Round 3 of the name-collision work, driven by the ratings. A famous name that a small
college shares ("Illinois" = Illinois College, "Colorado" = Colorado College, "Mississippi"
= Mississippi College, "Arkansas" = Arkansas College, "Northwestern" = Northwestern College
WI/MN/IA, "Trinity" = Trinity CT, "Loyola" = Loyola Baltimore/Chicago/Marymount, "Marshall"
= College of Marshall TX, now East Texas Baptist) shows up as the big school losing, tying
or barely beating small colleges far below its level.

A game of a listed name is proposed for the small college when either
  RESULT:   the big school lost or tied to a non-FBS opponent, 35+ points below its rating, or
  SCHEDULE: after 1950 the big (FBS) school "played" a today-D-II/D-III/NAIA school, or
  PLACE:    only for Trinity, Loyola (Marymount) and Marshall (pre-1944): opponent in the small
            college's area, where the big school never played.
With several small colleges for one name, the one in the opponent's region is chosen.

Output: residual_collision_review.csv -- same columns as name_collision_review.csv, so
  python apply_name_collisions.py --file residual_collision_review.csv           (preview)
  python apply_name_collisions.py --file residual_collision_review.csv --commit
Review the CSV first: delete any row that is a real upset (Centre over Harvard happened).
"""
import argparse, csv, os
from collections import defaultdict

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))

REGION = {}
for reg, sts in {"NE": "ME NH VT MA RI CT NY NJ", "MA": "PA DE MD DC VA WV", "SE": "NC SC GA FL",
                 "SC": "KY TN AL MS", "SW": "TX OK LA AR", "GL": "OH MI IN IL WI",
                 "PL": "MN IA MO KS NE SD ND", "MT": "CO WY MT ID UT NV NM AZ", "PA": "CA OR WA"}.items():
    for st in sts.split():
        REGION[st] = reg

# big name: list of (small college, its states, last season it played, place rule allowed)
# "place rule" = an opponent in the small college's area is enough. Only used where the big
# school essentially never played there (Trinity TX in New England, Loyola New Orleans vs
# California colleges, Marshall WV vs Texas colleges before 1944).
ALTS = {
    "Illinois":     [("Illinois College", {"IL", "MO", "IA"}, 2026, False)],
    "Colorado":     [("Colorado College", {"CO", "WY", "NM", "UT"}, 2008, False)],
    "Mississippi":  [("Mississippi College", {"MS", "LA", "AL", "AR", "TN", "TX"}, 2026, False)],
    "Arkansas":     [("Arkansas College", {"AR", "MO", "TN", "MS"}, 1950, False)],
    "Northwestern": [("Northwestern College", {"WI", "IL"}, 2026, False), ("Northwestern MN", {"MN", "ND", "SD"}, 2026, False),
                     ("Northwestern IA", {"IA", "NE", "KS"}, 2026, False)],
    "Trinity":      [("Trinity CT", {"CT", "MA", "RI", "NY", "VT", "NH", "ME", "NJ"}, 2026, True)],
    "Loyola":       [("Loyola Marymount", {"CA"}, 1951, True)],
    "Marshall":     [("East Texas Baptist", {"TX", "LA", "AR", "OK"}, 1943, True)],
}
SMALL = {"II", "III", "NAIA"}   # today's level of opponents an FBS school would not schedule after 1950


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=float, default=-35.0)
    a = ap.parse_args()
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    rating = {}
    for s, t, m in cur.execute("""
        SELECT r.Season, r.Home, r.Avg_Of_Avg_Of_Home_Modified_Score FROM dbo.College_Rankings r
        JOIN (SELECT Season, MAX(Week) AS W FROM dbo.College_Rankings GROUP BY Season) x
          ON x.Season = r.Season AND x.W = r.Week"""):
        if m is not None:
            rating[(t, s)] = float(m)
    info = {t: (st or "", ld or "") for t, st, ld in cur.execute(
        "SELECT Team_Name, State, Latest_Division FROM dbo.College_Team_Names")}
    names = list(ALTS)
    ph = ",".join("?" * len(names))
    games = cur.execute(f"""SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score
        FROM dbo.College_Scores WHERE (Home IN ({ph}) OR Visitor IN ({ph}))
          AND Home_Score IS NOT NULL""", *names, *names).fetchall()
    conn.close()

    out, tally = [], defaultdict(int)
    for aid, s, d, h, hs, v, vs in games:
        for side, team, opp, f, ag in (("Home", h, v, hs, vs), ("Visitor", v, h, vs, hs)):
            if team not in ALTS:
                continue
            ost, olat = info.get(opp, ("", ""))
            if olat == "1A" or opp in [x[0] for x in ALTS[team]]:
                continue                                   # FBS opponents: the big school
            base_fbs = info.get(team, ("", ""))[1] == "1A"
            res = None
            if (team, s) in rating and (opp, s) in rating:
                res = (f - ag) - (rating[(team, s)] - rating[(opp, s)])
            alts = [x for x in ALTS[team] if s <= x[2]]
            if not alts:
                continue
            choice = next((x for x in alts if ost in x[1]), None)
            why = []
            # 1. PLACE (only where the big school never played there)
            if choice and choice[3]:
                why.append(f"opponent in {ost}, {choice[0]}'s area")
            # 2. RESULT: big school lost or tied, far below its rating (any era)
            if base_fbs and res is not None and f <= ag and res <= a.res:
                why.append(f"{team} {f}-{ag}, {abs(res):.0f} pts worse than its rating predicts")
            # 3. MODERN SCHEDULE: an FBS school vs a D-II / D-III / NAIA school after 1950
            if base_fbs and s >= 1950 and (olat in SMALL or olat.startswith("III")):
                why.append(f"{team} would not schedule {opp} ({olat}) in {s}")
            if not why:
                continue
            choice = choice or alts[0]
            alt = choice[0]
            tally[(team, alt)] += 1
            out.append([aid, s, d, team, side, opp, ost, "", f, ag, alt, "; ".join(why)])
    out.sort(key=lambda x: (x[3], x[1]))
    fn = os.path.join(HERE, "residual_collision_review.csv")
    with open(fn, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Season", "Date", "Name_Now", "Side", "Opponent", "Opp_State", "Opp_FBS",
                    "Score_For", "Score_Against", "Proposed_Name", "Reason"])
        w.writerows(out)
    print("Written: residual_collision_review.csv\n")
    for (t, alt), n in sorted(tally.items()):
        opp = defaultdict(int)
        for x in out:
            if x[3] == t and x[10] == alt:
                opp[x[5]] += 1
        print(f"  {t:13s} -> {alt:20s} {n:4d}  " + ", ".join(f"{o} {c}" for o, c in sorted(opp.items(), key=lambda z: -z[1])[:15]))


if __name__ == "__main__":
    main()
