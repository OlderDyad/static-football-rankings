"""
split_name_collisions.py  -- run on Windows (reads SQL Server; changes nothing)

Some names hold TWO schools for part of their history, because the second school
only got its own suffixed name later (Georgetown KY exists only from 2005; its
earlier games sit under "Georgetown DC"). Rules, in order, for each game:

  1. opponent in KEEP_BASE                       -> base school (known real games)
  2. FBS_STAYS and opponent is FBS today         -> base school (the small school
                                                    did not play majors; bowls and
                                                    intersectional games stay)
  3. opponent in ALT_OPPONENTS, or opponent state
     in ALT_STATES                               -> the other school
  4. post-season game (Nov 20 on, 1973+) vs a
     non-FBS opponent, for FBS_STAYS names       -> the other school (D-II playoffs)
  5. undated (Aug 1) game in a season where the
     base school's schedule is dated            -> the other school, marked (weak)
  otherwise the game stays.  (Access division labels are NOT used: they call TCU,
  Miami OH and West Virginia "Small College" in the 1930s-60s.)

Output: name_collision_review.csv -- only games proposed to move; review by opponent.
"""
import csv, os
from collections import defaultdict

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))

NW_SMALL = {"Willamette", "Linfield", "Lewis & Clark", "Whitman", "Puget Sound", "Pacific Lutheran",
            "College of Idaho", "Whitworth", "Southern Oregon", "Western Oregon", "Eastern Oregon",
            "Oregon Tech", "Simon Fraser", "Central Washington", "Western Washington", "Chico St",
            "Humboldt St", "Southern Oregon St", "Oregon Normal", "Albany OR", "McMinnville"}

# base: (alt name, ALT_STATES, ALT_OPPONENTS, KEEP_BASE, FBS_STAYS, alt hidden before season)
# Round 1 (applied 2026-10-17): California -> California PA, Indiana -> Indiana PA,
# Georgetown DC -> Georgetown KY, Pacific -> Pacific OR. Kept for the record; set ROUND = 1 to rerun.
ROUND1 = {
    "California":    ("California PA", {"PA", "WV", "OH", "MD", "NY", "NJ", "CT", "VA", "DE"},
                      set(), {"Carlisle Indian School"}, True, 2027),
    "Indiana":       ("Indiana PA", {"PA", "NY", "NJ", "MD", "DE", "CT", "VA", "WV"},
                      set(), set(), True, 2027),
    "Georgetown DC": ("Georgetown KY", {"KY", "IN", "TN", "OH"},
                      set(), set(), False, 2005),
    "Pacific":       ("Pacific OR", set(), NW_SMALL, set(), False, 2010),
}
# Round 2 (found by game_residuals.py): one base name can hide several schools, so each
# base has a LIST of alternatives, tried in order. Extra field: FBS_GOES_ALT = games against
# today's FBS programs belong to the alternative (Cumberland TN played Georgia Tech,
# Vanderbilt, Alabama; the Kentucky school did not).
#   base: [(alt, ALT_STATES, ALT_OPPONENTS, before_season, FBS_GOES_ALT), ...], KEEP_BASE
ROUND2 = {
    "Union KY": ([("Union NY", {"NY", "VT", "MA", "CT", "NJ", "PA", "RI", "NH", "ME"}, set(), 2009, False),
                  ("Union TN", {"MS", "AL", "AR", "LA"}, set(), 1953, True)], set()),
    "King's PA": ([("King TN", {"TN", "VA", "NC", "SC", "GA", "KY", "WV", "AL"}, set(), 1946, True)], set()),
    "Cumberlands KY": ([("Cumberland TN", {"GA", "AL", "MS", "LA", "AR"}, set(), 1960, True)], set()),
    "St Mary's MI": ([("St Mary's KY", {"KY", "IN", "TN"}, set(), 2027, False)], set()),
}
# Union University (TN) dropped football after 1952; Cumberland TN's modern games are already
# under its own name, so both alternatives stop there (Faulkner, Shorter, South Florida stay).

# Round 4 (2026-10-20): bare names left over from the Access import, where EVERY game belongs
# to some other name. Each base has rules tried in order:
#   (new name, first season, last season, opponent states or None, opponents or None, note)
# A rule matches when first <= season <= last and (opponent in its list or opponent state in
# its states); states and opponents both None = any opponent. Games no rule takes are written
# as CHECK (never applied). BY_ID overrides everything; NEW_DATE fixes dates in the same pass.
# Each rule's years are the school's football years, checked before adding the rule.
NE = {"NY", "VT", "MA", "CT", "NJ", "PA", "RI", "NH", "ME"}
MIDWEST = {"OH", "IN", "MI", "IL", "WV", "KY", "PA", "WI", "IA"}
SOUTH = {"FL", "GA", "AL", "LA", "TN", "MS", "SC", "NC", "AR"}
ROUND4 = {
    # Anderson University (IN) football 1947-; Anderson SC started 2024 and has its own name.
    "Anderson": [("Anderson IN", 1947, 2023, None, None, "Anderson (IN) football 1947-")],
    # Detroit Athletic Club, founded 1887 (Detroit Mercy football began 1896). Same name the
    # 1906 newspaper split uses, so later newspaper seasons land on it too.
    "Detroit MercyAC": [("Detroit Athletic Club (MI)", 1887, 1930, None, None, "Detroit Athletic Club")],
    # Miami (OH) football since 1888, Miami (FL) since 1926.
    "Miami": [("Miami OH", 1888, 2026, MIDWEST, {"Marshall"}, "Miami (OH) since 1888, Midwest opponent"),
              ("Miami FL", 1926, 2026, SOUTH, {"San Diego St"}, "Miami (FL) since 1926, Southern opponent")],
    # Union (NY) since 1886; Union (TN) football ended 1952; Union (KY) after that in the South.
    "Union": [("Union NY", 1886, 2026, NE, {"Middlebury", "WPI"}, "Union (NY), Northeast opponent"),
              ("Union TN", 1900, 1952, SOUTH, None, "Union (TN) football to 1952, Southern opponent"),
              ("Union KY", 1953, 2026, SOUTH | {"KY", "VA", "WV"}, None, "Union (KY), Southern opponent after 1952")],
}
ROUND4_BY_ID = {
    14670: ("Anderson Training School", "Sewanee 1910 schedule: Anderson Training School, W 27-0 Oct 8"),
    2431: ("Detroit Independents", "Michigan 1883 schedule: Detroit Independents, W 40-5 May 12 (DAC founded 1887)"),
    445238: ("Miami FL", "Wolfe: Central Michigan at Miami FL 52-3, Sep 26 2026"),
}
ROUND4_NEW_DATE = {14670: "1910-10-08", 2431: "1883-05-12"}

# Round 5 (2026-10-21, from game_residuals.py): same rule format as round 4, but the base name is a
# real school too, so games no rule takes STAY (not CHECK) and are not written to the review file.
US = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY",
      "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
      "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"}
ROUND5 = {
    # Nichols College (Dudley MA) plays New England; Nicholls State (Thibodaux LA) football since 1972.
    # Stops at 2000: later Nicholls St games are already under its own name, and Nichols College's
    # D-III opponents outside the Northeast (Bridgewater VA 2001-04, Gallaudet 2023-24) are real.
    "Nichols": [("Nicholls St", 1972, 2000, US - NE, None, "Nicholls St (LA) since 1972, non-Northeast opponent")],   # applied 2026-10-21
    "Loyola": [],     # by Access_ID only (ROUND5_BY_ID); New Orleans games stay
}
# "Loyola" = Loyola New Orleans (Wolf Pack, 1921-39; its games STAY). Other schools' games matched
# one by one to Wikipedia season schedules (Loyola Wolf Pack / Lions / Ramblers / Green and Gray pages,
# Villanova 1928 and Holy Cross 1930 list "Loyola (MD)"). 2026-10-21.
_LMU = """92060 347420 347627 347780 351469 350150 311830 262334 25754 25948 262353
26409 262365 262366 26621 26667 262380 262390 27233 262400 85582 27609
27756 262424 262428 85589 262439 28271 262462 262469
262477 262485 262489 262493 29598 262499 262503 29930 262511 30131 262521 30257 307991
312261 30592 262533 264667 31126 262551 264669 307998 262555 31541
262564 31863 31999 262569 32150 32205 262584 262587 262590 262591
264690 34802 312509 85676 312549 85686 262640 312590 36311 264698 262653 262655 36718
36945 312643 37092 37140 262665 37484 262671 37693 37828 262678
318387 280304 318401 280708 318408 359069 359196 318453 318469 359336 359474 313418 313462 282828"""
_CHI = """349068 349458 349469 245700 346969 347156 351369 347644 347896 348108 325932 241225
268949 268965 325923"""
_BAL = """242460 351347 242070 347535 241862 347787 347834 187856 350103 348048 350146
269153 269202 311916 269444 269589 227326"""
ROUND5_BY_ID = {}
ROUND5_BY_ID.update({int(x): ("Loyola Marymount", "Loyola Lions (Los Angeles) season schedule") for x in _LMU.split()})
ROUND5_BY_ID.update({int(x): ("Loyola Chicago", "Loyola Ramblers (Chicago) season schedule") for x in _CHI.split()})
ROUND5_BY_ID.update({int(x): ("Loyola Baltimore", "Loyola (MD) on the schedule / Baltimore rivals") for x in _BAL.split()})
# Not on any schedule checked -> CHECK (left unchanged): Temple 1896-1908, Detroit 1896/1900, Denver 1907,
# Colorado Mines 1908-09, American Int'l and Hofstra 1950, Central Conn St 1952 (a Northeast Loyola,
# perhaps Loyola Montreal), and 1970-71 club games vs Duquesne, Case Western, Chicago.
for x in """249225 249080 352655 352860 249272 351597 349391 344427 344440 213130 274169 274616
281284 255729 281779 307574""".split():
    ROUND5_BY_ID[int(x)] = ("CHECK", "Loyola game not found on any school's schedule")
ROUND5_NEW_DATE = {29930: "1938-10-30"}           # LMU at Centenary, Oct 30 1938
# Same LMU game entered twice under 'Loyola' (only one meeting that season): move the second copy.
ROUND5_DUP_OF = {30131: 307991, 31541: 307998}   # Hardin-Simmons 1938 (Nov 19), 1940 (Nov 8)
ROUND = 5


def main():
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    if ROUND == 4:
        return round4(cur, conn)
    if ROUND == 5:
        return round4(cur, conn, ROUND5, ROUND5_BY_ID, ROUND5_NEW_DATE, stay=True, dup_of=ROUND5_DUP_OF)
    COLLISIONS = ROUND1 if ROUND == 1 else ROUND2
    names = list(COLLISIONS)
    ph = ",".join("?" * len(names))
    games = cur.execute(f"""
        SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score
        FROM dbo.College_Scores WHERE Home IN ({ph}) OR Visitor IN ({ph})""", *names, *names).fetchall()
    info = {t: (st or "", ld or "") for t, st, ld in cur.execute(
        "SELECT Team_Name, State, Latest_Division FROM dbo.College_Team_Names").fetchall()}
    conn.close()

    def is_aug1(d):
        return d is None or (d.month == 8 and d.day == 1)

    dated = defaultdict(int)
    for g in games:
        if not is_aug1(g[2]):
            for t in (g[3], g[5]):
                dated[(t, g[1])] += 1

    out, tally = [], defaultdict(lambda: defaultdict(int))
    for aid, s, d, h, hs, v, vs in games:
        for side, team, opp in (("Home", h, v), ("Visitor", v, h)):
            if team not in COLLISIONS:
                continue
            ost, olatest = info.get(opp, ("", ""))
            fbs = olatest == "1A"
            prop = why = None
            if ROUND == 1:
                alt, alt_states, alt_opps, keep, fbs_stays, until = COLLISIONS[team]
                if s >= until or opp == alt:
                    continue
                if opp in keep:
                    pass
                elif fbs_stays and fbs:
                    pass
                elif opp in alt_opps:
                    prop, why = alt, f"{opp} is a regular {alt} opponent"
                elif ost in alt_states:
                    prop, why = alt, f"opponent state {ost}"
                elif fbs_stays and d is not None and s >= 1973 and (d.month == 12 or (d.month == 11 and d.day >= 20)):
                    prop, why = alt, "post-season game vs non-FBS opponent (D-II playoffs)"
                elif is_aug1(d) and dated[(team, s)] >= 5:
                    prop, why = alt + " (weak)", f"undated game; {team}'s {s} schedule is dated"
            else:
                rules, keep = COLLISIONS[team]
                if opp in keep or opp in [r[0] for r in rules]:
                    continue
                for alt, alt_states, alt_opps, until, fbs_alt in rules:
                    if s >= until:
                        continue
                    if opp in alt_opps:
                        prop, why = alt, f"{opp} is a regular {alt} opponent"
                    elif fbs_alt and fbs and ost != info.get(team, ("", ""))[0]:   # home-state majors stay
                        prop, why = alt, f"{opp} is a major program ({alt} played majors, {team} did not)"
                    elif ost in alt_states:
                        prop, why = alt, f"opponent state {ost}"
                    if prop:
                        break
            if prop is None:
                tally[team]["stay"] += 1
                continue
            tally[team]["weak" if "weak" in prop else "move"] += 1
            out.append([aid, s, d, team, side, opp, ost, "FBS" if fbs else "",
                        hs if side == "Home" else vs, vs if side == "Home" else hs, prop, why])

    out.sort(key=lambda x: (x[3], x[5], x[1]))
    with open(os.path.join(HERE, "name_collision_review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Season", "Date", "Name_Now", "Side", "Opponent", "Opp_State", "Opp_FBS",
                    "Score_For", "Score_Against", "Proposed_Name", "Reason"])
        w.writerows(out)
    print("Written: name_collision_review.csv\n")
    for t in COLLISIONS:
        c = tally[t]
        alts = COLLISIONS[t][0] if ROUND == 1 else "/".join(r[0] for r in COLLISIONS[t][0])
        print(f"  {t:14s} -> {alts:20s} move {c['move']:4d}  weak {c['weak']:3d}  stay {c['stay']:5d}")
        opp = defaultdict(int)
        for x in out:
            if x[3] == t:
                opp[x[5]] += 1
        print("     moved opponents: " + ", ".join(f"{o} {n}" for o, n in sorted(opp.items(), key=lambda z: -z[1])[:30]))


def round4(cur, conn, rules4=None, by_id=None, new_date=None, stay=False, dup_of=None):
    """Every game of each bare name gets a new name (or CHECK). A game that already exists under
    the new name (same season, opponent and score) is marked Dup_Of: apply moves it to
    College_Scores_Duplicates instead of renaming it."""
    ROUND4_ = rules4 if rules4 is not None else ROUND4
    BY_ID = by_id if by_id is not None else ROUND4_BY_ID
    NEW_DATE = new_date if new_date is not None else ROUND4_NEW_DATE
    names = list(ROUND4_)
    ph = ",".join("?" * len(names))
    games = cur.execute(f"""
        SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score
        FROM dbo.College_Scores WHERE Home IN ({ph}) OR Visitor IN ({ph})""", *names, *names).fetchall()
    info = {t: (st or "", ld or "") for t, st, ld in cur.execute(
        "SELECT Team_Name, State, Latest_Division FROM dbo.College_Team_Names").fetchall()}
    targets = sorted(({r[0] for rules in ROUND4_.values() for r in rules} | {v[0] for v in BY_ID.values()}) - {"CHECK"})
    ph = ",".join("?" * len(targets))
    have = defaultdict(list)                      # (new name, season, opponent) -> [(aid, for, against)]
    for aid, s, d, h, hs, v, vs in cur.execute(f"""
            SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score
            FROM dbo.College_Scores WHERE Home IN ({ph}) OR Visitor IN ({ph})""", *targets, *targets):
        if h in targets:
            have[(h, s, v)].append((aid, hs, vs))
        if v in targets:
            have[(v, s, h)].append((aid, vs, hs))
    conn.close()

    out, tally = [], defaultdict(lambda: defaultdict(int))
    for aid, s, d, h, hs, v, vs in games:
        for side, team, opp in (("Home", h, v), ("Visitor", v, h)):
            if team not in ROUND4_:
                continue
            ost = info.get(opp, ("", ""))[0]
            sf, sa = (hs, vs) if side == "Home" else (vs, hs)
            prop = why = None
            forced = False
            if aid in BY_ID:
                prop, why = BY_ID[aid]
                if prop == "CHECK":
                    prop, forced = None, True
            else:
                for alt, first, last, states, opps, note in ROUND4_[team]:
                    if not first <= s <= last:
                        continue
                    if (states is None and opps is None) or (opps and opp in opps) or (states and ost in states):
                        prop, why = alt, f"{note} ({opp}, {ost or 'state ?'})"
                        break
            dup = (dup_of or {}).get(aid, "")
            if prop and not dup:
                for kaid, kf, ka in have.get((prop, s, opp), []):
                    if (kf, ka) == (sf, sa) and kaid != aid:
                        dup = kaid
                        break
            tally[team]["stay" if (stay and not prop and not forced) else "CHECK" if not prop else ("dup" if dup else prop)] += 1
            if stay and not prop and not forced:
                continue
            out.append([aid, s, d, team, side, opp, ost, "", sf, sa, prop or "CHECK",
                        why or "no rule matched -- decide by hand", dup, NEW_DATE.get(aid, "")])

    out.sort(key=lambda x: (x[3], x[10], x[1]))
    with open(os.path.join(HERE, "name_collision_review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Season", "Date", "Name_Now", "Side", "Opponent", "Opp_State", "Opp_FBS",
                    "Score_For", "Score_Against", "Proposed_Name", "Reason", "Dup_Of", "New_Date"])
        w.writerows(out)
    print(f"Written: name_collision_review.csv (round {ROUND})\n")
    for t in ROUND4_:
        print(f"  {t:16s} " + ", ".join(f"{k} {n}" for k, n in sorted(tally[t].items())))
    for x in out:
        if x[10] == "CHECK":
            print(f"     CHECK {x[0]} {x[1]} {x[3]} vs {x[5]} ({x[6] or '?'}) {x[8]}-{x[9]}")
        if stay and x[10] != "CHECK":
            print(f"     {x[0]} {x[1]} {x[3]} vs {x[5]} ({x[6] or '?'}) {x[8]}-{x[9]} -> {x[10]}")
        if x[12]:
            print(f"     DUP   {x[0]} {x[1]} {x[3]} vs {x[5]} {x[8]}-{x[9]} = existing {x[10]} row {x[12]}")


if __name__ == "__main__":
    main()
