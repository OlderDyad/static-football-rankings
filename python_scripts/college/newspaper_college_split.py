"""
newspaper_college_split.py  -- run on Windows after a newspaper batch is in HS_Scores.
Preview by default; --commit applies.

Takes the HS_Scores games of one newspaper import (by --batch, or --source-like) and:
  both teams college varsity  -> MOVE to College_Scores (deleted from HS_Scores; --keep-hs keeps a copy)
  college vs a NON-HS team    -> MOVE too (club, YMCA, alumni, military, reserves/freshmen: no HS varsity
                                 team in the game, so it does not belong in HS_Scores) -- rule of 2026-10-22
  college vs HS varsity       -> COPY to College_Scores (HS row stays)
  no college varsity          -> STAY in HS_Scores only
Non-HS side: name matches club/military/reserve words, or the map file says CLUB, or College_Team_Names
links the name (HS_Team_Name) to a Club/Military/Freshmen row. --copy-clubs restores the old behaviour
(college-vs-club games kept in HS_Scores too).
Games already in College_Scores (same season, same two teams, dates within 3 days or an
Aug-1 placeholder) are not added again:
  DUPLICATE  same score            (DATE-FIX when ours is Aug-1 and the paper has the date)
  CONFLICT   different score       -> listed for you to check, nothing changed
Two papers printing the same game count once.

Which HS names are colleges (decided in this order):
  1. newspaper_college_map.csv  -- your decisions (HS_Name, College_Name); College_Name = HS
     means "not a college". Grows as you work; reused for every later season.
  2. College_Team_Names.HS_Team_Name link (Kind = College)
  3. name looks like a college (University, College, Institute, Normal, A&M, ...) and matches a
     college team by name -> proposed, marked REVIEW (treated as HS until you confirm it in
     the map file -- copy the row from newspaper_college_names.csv)
  Reserves / freshmen / scrubs / second team / alumni / academies are never college varsity.
The non-college side of a COPY keeps its HS name in College_Scores (and gets a
College_Team_Names row: Kind HS/Prep or Club), so the two tables stay linked.

Outputs (python_scripts/college/newspaper_split/):
  newspaper_college_names.csv   every team name in the batch and the decision
  newspaper_college_games.csv   every game and its action
Usage:  python newspaper_college_split.py --season 1906 --batch 123 124
        python newspaper_college_split.py --season 1906 --source-like "%Lansing%" "%Dayton%"
        ... --commit [--fix-dates] [--keep-hs]
"""
import argparse, csv, os, re, sys, uuid
from datetime import timedelta
from collections import Counter, defaultdict

import pyodbc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from college_names import Matcher  # noqa: E402

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "newspaper_split")
MAP_FILE = os.path.join(HERE, "newspaper_college_map.csv")

COLLEGE_WORDS = re.compile(r"\b(university|univ|college|institute|normal|polytechnic|a\s*&\s*m|agricultural|"
                           r"school of mines|seminary|tech|m\.?\s*a\.?\s*c\.?)\b", re.I)
NOT_VARSITY = re.compile(r"\b(reserves?|freshmen|freshman|frosh|scrubs?|second|2nd|seconds|jv|junior varsity|"
                         r"alumni|academy|prep|high|hs|grammar|juniors?|sophomores?)\b", re.I)
CLUB_WORDS = re.compile(r"\b(a\.?c\.?|athletic club|athletics|ymca|y\.m\.c\.a|independents?|club|alumni|"
                        r"all[- ]stars?|town|city team)\b", re.I)
# not a high school varsity either: clubs, military units, college reserves / freshmen / scrubs
NON_HS = re.compile(r"\b(a\.?c\.?|athletic club|athletics|ymca|y\.m\.c\.a|independents?|club|alumni|all[- ]stars?|"
                    r"city team|town team|fort|camp|barracks|naval|navy|marines?|regiment|battery|infantry|artillery|"
                    r"cavalry|soldiers|training station|reserves?|freshmen|freshman|frosh|scrubs?|second team)\b", re.I)


def aug1(d):
    return d is None or (d.month == 8 and d.day == 1)


def load_map():
    m = {}
    if os.path.exists(MAP_FILE):
        for r in csv.DictReader(open(MAP_FILE, encoding="utf-8-sig")):
            if r.get("HS_Name") and r.get("College_Name"):
                m[r["HS_Name"].replace("\xa0", " ").strip()] = r["College_Name"].replace("\xa0", " ").strip()
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--batch", type=int, nargs="*", default=[])
    ap.add_argument("--source-like", nargs="*", default=[])
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--fix-dates", action="store_true", help="give dates to our Aug-1 games the paper dates")
    ap.add_argument("--keep-hs", action="store_true", help="college-vs-college games stay in HS_Scores too")
    ap.add_argument("--played-dates", action="store_true",
                    help="papers print Sunday/Monday REPORT dates: use the Saturday before for new games and date fixes")
    ap.add_argument("--drop-conflicts", action="store_true",
                    help="CONFLICT (MOVE) games: keep College_Scores' score (checked) and remove the paper's row "
                         "from HS_Scores; fix our score first where the paper is right")
    ap.add_argument("--copy-clubs", action="store_true",
                    help="old behaviour: college-vs-club/military games are COPIED (kept in HS_Scores too)")
    a = ap.parse_args()
    if not a.batch and not a.source_like:
        sys.exit("Give --batch or --source-like to pick the newspaper games.")
    os.makedirs(OUT, exist_ok=True)

    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    where, args = ["Season = ?"], [a.season]
    picks = []
    if a.batch:
        picks.append(f"BatchID IN ({','.join('?' * len(a.batch))})")
        args += a.batch
    for s in a.source_like:
        picks.append("Source LIKE ?")
        args.append(s)
    where.append("(" + " OR ".join(picks) + ")")
    hs = cur.execute(f"""SELECT ID, Date, Season, Home, Home_Score, Visitor, Visitor_Score, Neutral, Location, Source
                         FROM dbo.HS_Scores WHERE {' AND '.join(where)}
                           AND Home_Score IS NOT NULL AND Visitor_Score IS NOT NULL""", *args).fetchall()
    print(f"{len(hs):,} HS_Scores games selected for {a.season}")
    if not hs:
        return
    teams = {r[0]: (r[1] or "", r[2] or "") for r in cur.execute(
        "SELECT Team_Name, Kind, HS_Team_Name FROM dbo.College_Team_Names").fetchall()}
    by_hs = defaultdict(list)
    for t, (kind, hsn) in teams.items():
        if hsn and kind == "College":
            by_hs[hsn].append(t)

    user_map = load_map()
    matcher = Matcher()
    decide = {}                                   # HS name -> (college name or None, how)
    for name in sorted({x for g in hs for x in (g[3], g[5])}):
        if name in user_map:
            c = user_map[name]
            decide[name] = (None if c.upper() in ("HS", "CLUB") else c,
                            "your map (club / not HS)" if c.upper() == "CLUB" else "your map")
        elif NOT_VARSITY.search(name):
            decide[name] = (None, "not varsity (reserves/freshmen/prep/alumni)")
        elif by_hs.get(name):
            decide[name] = (by_hs[name][0], "College_Team_Names link")
        elif COLLEGE_WORDS.search(name):
            st = re.search(r"\(([A-Z]{2})\)\s*$", name)
            t, how, alts = matcher.match(name, a.season, st.group(1) if st else None)
            if t and teams.get(t, ("",))[0] == "College":
                decide[name] = (None, f"REVIEW: looks like {t} ({how}{'; also ' + ', '.join(alts[:3]) if alts else ''})")
            else:
                decide[name] = (None, "REVIEW: college-like name, no college match")
        else:
            decide[name] = (None, "HS / town team")
    with open(os.path.join(OUT, "newspaper_college_names.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["HS_Name", "College_Name", "Decision", "Games"])
        cnt = Counter(x for g in hs for x in (g[3], g[5]))
        for name, (c, how) in sorted(decide.items(), key=lambda z: (z[1][0] is None, z[0])):
            prop = c or (re.search(r"looks like (.+?) \(", how).group(1) if how.startswith("REVIEW: looks") else "")
            w.writerow([name, prop, how, cnt[name]])

    # existing college games this season
    existing = defaultdict(list)
    for aid, d, h, hs_, v, vs in cur.execute("""SELECT Access_ID, Date, Home, Home_Score, Visitor, Visitor_Score
                                               FROM dbo.College_Scores WHERE Season = ?""", a.season):
        existing[frozenset((h, v))].append((aid, d, h, hs_, v, vs))

    club_link = {hsn for t, (kind, hsn) in teams.items() if hsn and kind in ("Club", "Military", "Freshmen")}

    def non_hs(name):
        """True when the non-college side is not a high school varsity (no HS team in the game)."""
        return (user_map.get(name, "").upper() == "CLUB" or name in club_link or bool(NON_HS.search(name)))

    actions, seen, used_ids = [], [], set()
    for gid, d, s, h, hsc, v, vsc, n, loc, src in hs:
        ch, cv = decide[h][0], decide[v][0]
        if not ch and not cv:
            actions.append([gid, d, h, hsc, v, vsc, "", "", "STAY", "", src])
            continue
        H, V = ch or h, cv or v                   # college-table names
        other = v if ch and not cv else h if cv and not ch else None
        act = "MOVE" if (ch and cv) or (other and not a.copy_clubs and non_hs(other)) else "COPY"
        # same game printed twice (two papers)
        key = (frozenset((H, V)), frozenset(((H, hsc), (V, vsc))))
        dup = next((x for x in seen if x[0] == key and (aug1(d) or aug1(x[1]) or abs((x[1] - d).days) <= 3)), None)
        note = ""
        if dup:
            act = "SAME GAME TWICE" + (" (MOVE)" if act == "MOVE" else "")
        else:
            seen.append((key, d))
            cands = [e for e in existing.get(frozenset((H, V)), [])
                     if (aug1(e[1]) or aug1(d) or abs((e[1] - d).days) <= 3) and e[0] not in used_ids]
            # a same-score game anywhere among the candidates wins (teams can meet twice a season)
            same = [e for e in cands if ({e[2]: e[3], e[4]: e[5]}.get(H), {e[2]: e[3], e[4]: e[5]}.get(V)) == (hsc, vsc)]
            if same:
                aid, ed = same[0][0], same[0][1]
                used_ids.add(aid)
                act = ("DATE-FIX" if aug1(ed) and not aug1(d) else "DUPLICATE") + (" (MOVE)" if act == "MOVE" else "")
                note = str(aid)
            elif cands:
                aid, ed, eh, ehs, ev, evs = cands[0]
                mine = {eh: ehs, ev: evs}
                act = "CONFLICT" + (" (MOVE)" if act == "MOVE" else "")
                note = f"Access_ID {aid}: ours {mine.get(H)}-{mine.get(V)}"
        actions.append([gid, d, h, hsc, v, vsc, H, V, act, note, src])

    with open(os.path.join(OUT, "newspaper_college_games.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["HS_ID", "Date", "Home", "Home_Score", "Visitor", "Visitor_Score",
                    "College_Home", "College_Visitor", "Action", "Note", "Source"])
        w.writerows(actions)
    c = Counter(x[8] for x in actions)
    print("Games: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    rev = [k for k, v in decide.items() if v[1].startswith("REVIEW")]
    print(f"Team names: {sum(1 for v in decide.values() if v[0]):,} college varsity, {len(rev)} to REVIEW "
          f"(treated as HS until confirmed in newspaper_college_map.csv)")
    for k in rev[:25]:
        print(f"   {k:40s} {decide[k][1]}")
    new_games = [x for x in actions if x[8] in ("MOVE", "COPY")]
    teams_helped = Counter(t for x in new_games for t in (x[6], x[7]) if teams.get(t, ("",))[0] == "College")
    print(f"\nNew college games: {len(new_games)} ({c.get('MOVE', 0)} MOVE: vs college or club/military, {c.get('COPY', 0)} COPY: vs HS); "
          f"{c.get('DUPLICATE', 0) + c.get('DUPLICATE (MOVE)', 0) + c.get('DATE-FIX', 0) + c.get('DATE-FIX (MOVE)', 0)} already in College_Scores")
    print("College teams gaining games: " + ", ".join(f"{t} +{n}" for t, n in teams_helped.most_common(20)))
    if not a.commit:
        print(f"\nPreview only -- see {OUT}. Re-run with --commit to apply.")
        return

    colinfo = {r[0]: r for r in cur.execute("""
        SELECT c.name, c.is_identity, c.is_computed, c.is_nullable, t.name, c.default_object_id
        FROM sys.columns c JOIN sys.types t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID('dbo.College_Scores')""")}
    counters = {}
    for col in ("Access_ID", "ID"):
        r = colinfo.get(col)
        if r and not r[1] and not r[2] and r[4] in ("int", "bigint"):
            counters[col] = max((cur.execute(f"SELECT MAX([{col}]) FROM dbo.College_Scores").fetchone()[0] or 0) + 1,
                                900000000 if col == "Access_ID" else 1)
    try:
        ins = moved = fixed = named = flagged = 0
        for gid, d, h, hsc, v, vsc, H, V, act, note, src in actions:
            base = act.replace(" (MOVE)", "")
            if a.played_dates and d is not None and not aug1(d) and d.weekday() in (6, 0):
                d = d - timedelta(days=1 if d.weekday() == 6 else 2)       # Sun -> Sat, Mon -> Sat
            if base in ("MOVE", "COPY"):
                vals = {"Date": d, "Season": a.season, "Home": H, "Visitor": V, "Home_Score": hsc,
                        "Visitor_Score": vsc, "Margin": hsc - vsc, "Neutral": 0,
                        "Source": f"Newspaper: {src}"[:255] if src else "Newspaper", "Future_Game": 0}
                for col, nxt in counters.items():
                    vals[col] = nxt
                    counters[col] += 1
                if "ID" in colinfo and "ID" not in vals and colinfo["ID"][4] == "uniqueidentifier" \
                        and not colinfo["ID"][5]:
                    vals["ID"] = str(uuid.uuid4())
                vals = {k: x for k, x in vals.items() if k in colinfo and not colinfo[k][1] and not colinfo[k][2]}
                cur.execute(f"INSERT INTO dbo.College_Scores ({', '.join('[' + k + ']' for k in vals)}) "
                            f"VALUES ({','.join('?' * len(vals))})", *vals.values())
                ins += 1
            if base == "DATE-FIX" and a.fix_dates:
                cur.execute("UPDATE dbo.College_Scores SET Date = ? WHERE Access_ID = ?", d, note)
                fixed += 1
            if act.startswith("CONFLICT") and a.drop_conflicts:
                m_ = re.match(r"Access_ID (\d+)", note)
                if m_:      # default-and-flag: our score stays, marked disputed
                    cur.execute("UPDATE dbo.College_Scores SET Score_Disputed = 1 WHERE Access_ID = ?", int(m_.group(1)))
                    flagged += 1
            if "MOVE" in act and not a.keep_hs and (not act.startswith("CONFLICT") or a.drop_conflicts):
                # Season first: HS_Scores is indexed on Season, not on ID (ID alone = full table scan)
                cur.execute("DELETE FROM dbo.HS_Scores WHERE Season = ? AND ID = ?", a.season, gid)
                moved += 1
        for t in sorted({x for r in actions if r[8] in ("MOVE", "COPY") for x in (r[6], r[7])}):
            if t not in teams:
                kind = "Club" if (CLUB_WORDS.search(t) or NON_HS.search(t) or user_map.get(t, "").upper() == "CLUB") else "HS/Prep"
                st = re.search(r"\(([A-Z]{2})\)\s*$", t)
                cur.execute("INSERT INTO dbo.College_Team_Names (Team_Name, Kind, State, State_Source, HS_Team_Name) "
                            "VALUES (?, ?, ?, 'newspaper', ?)", t, kind, st.group(1) if st else None, t)
                named += 1
        conn.commit()
        print(f"\nCommitted: {ins} games added to College_Scores, {moved} college-vs-college games removed from "
              f"HS_Scores, {fixed} dates filled, {named} team names added, {flagged} conflicts flagged Score_Disputed.")
    except Exception as e:
        conn.rollback()
        print(f"\nRolled back: {e}")


if __name__ == "__main__":
    main()
