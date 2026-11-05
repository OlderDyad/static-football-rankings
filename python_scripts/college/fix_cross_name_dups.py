"""
fix_cross_name_dups.py  -- run on Windows; preview by default, --commit moves rows

Finds games stored twice under DIFFERENT opponent names: team T has two games within 2 days,
with the same score from T's side, against opponents A and B (e.g. Southland team vs 'Sam Houston St'
and vs 'San Diego St', same day, same score). One copy names the wrong school.
Pure aliases (same school, two names) should be merged with merge_same_school.py first.

Which copy is right, in this order:
  1. BUSY   - the wrong opponent already has ANOTHER game within 2 days (it was playing someone
              else that day); keep the copy whose opponent was free.
  2. STATE  - exactly one opponent is in T's state: keep it.
  3. SOURCE - one copy came from a school site / Winsipedia import (Access_ID >= 900000000),
              the other from the Access file: keep the import. (After STATE: imports can carry a
              wrong same-name school too, e.g. 'Wayne State' mapped to Wayne St NE for Ferris St.)
  otherwise REVIEW (nothing moved).

Output fix_cross_name_dups.csv (Rule, Keep/Move ids, names). --commit moves the 'Move' rows to
College_Scores_Duplicates (Kept_Access_ID = the kept row) for every rule except REVIEW.
Usage: python fix_cross_name_dups.py [--from 1900] [--commit]
"""
import argparse, csv, os
from collections import defaultdict, Counter

import pyodbc

HERE = os.path.dirname(os.path.abspath(__file__))
CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;")
DUP_COLS = ("Access_ID, Kept_Access_ID, Game_Date, Season, Home, Visitor, Home_Score, Visitor_Score, "
            "Neutral, Line, Location, Location2, Reason, Moved_At")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="first", type=int, default=1900)
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    skip = set()
    sf = os.path.join(HERE, "fix_cross_name_skip.csv")         # Name_1,Name_2 pairs to leave alone
    if os.path.exists(sf):
        for r in csv.reader(open(sf, encoding="utf-8-sig")):
            if len(r) >= 2 and r[0] != "Name_1":
                skip.add(frozenset((r[0].strip(), r[1].strip())))
    state = {n: (s or "") for n, s in cur.execute("SELECT Team_Name, State FROM dbo.College_Team_Names")}
    games, by_team = {}, defaultdict(list)
    for aid, se, d, h, hs, v, vs in cur.execute(
            "SELECT Access_ID, Season, [Date], Home, Home_Score, Visitor, Visitor_Score FROM dbo.College_Scores "
            "WHERE Season >= ? AND [Date] IS NOT NULL AND Home_Score IS NOT NULL AND Visitor_Score IS NOT NULL "
            "AND NOT (MONTH([Date]) = 8 AND DAY([Date]) = 1)", a.first):
        games[aid] = (se, d, h, hs, v, vs)
        by_team[(h, se)].append(aid)
        by_team[(v, se)].append(aid)

    def busy(team, d, skip):
        return any(abs((games[x][1] - d).days) <= 2 for x in by_team[(team, games[skip[0]][0])] if x not in skip)

    out, seen = [], set()
    for (t, se), aids in by_team.items():
        aids = sorted(aids, key=lambda x: games[x][1])
        for i, x in enumerate(aids):
            for y in aids[i + 1:]:
                if (games[y][1] - games[x][1]).days > 2:
                    break
                key = (min(x, y), max(x, y))
                if key in seen:
                    continue
                _, dx, hx, hsx, vx, vsx = games[x]
                _, dy, hy, hsy, vy, vsy = games[y]
                ox, oy = (vx if hx == t else hx), (vy if hy == t else hy)
                if ox == oy or frozenset((ox, oy)) in skip:
                    continue
                tsx, osx = (hsx, vsx) if hx == t else (vsx, hsx)
                tsy, osy = (hsy, vsy) if hy == t else (vsy, hsy)
                if (tsx, osx) != (tsy, osy):
                    continue
                seen.add(key)
                bx, by = busy(ox, dx, (x, y)), busy(oy, dy, (x, y))
                rule, keep = "REVIEW", None
                if bx != by:
                    rule, keep = "BUSY", (y if bx else x)
                elif (state.get(ox) == state.get(t)) != (state.get(oy) == state.get(t)) and state.get(t):
                    rule, keep = "STATE", (x if state.get(ox) == state.get(t) else y)
                elif (x >= 900000000) != (y >= 900000000):
                    rule, keep = "SOURCE", (x if x >= 900000000 else y)
                move = (y if keep == x else x) if keep else ""
                out.append([rule, t, se, dx, ox, state.get(ox, ""), x, oy, state.get(oy, ""), y,
                            f"{tsx}-{osx}", keep or "", move])
    print("Pairs:", dict(Counter(r[0] for r in out)))
    pc = Counter((r[0], tuple(sorted((r[4], r[7])))) for r in out)
    print("\nMost common name pairs:")
    for (rule, p), n in pc.most_common(25):
        print(f"  {n:4}  {rule:6}  {p[0]}  /  {p[1]}")
    with open(os.path.join(HERE, "fix_cross_name_dups.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Rule", "Team", "Season", "Date", "Opp_1", "State_1", "Id_1", "Opp_2", "State_2", "Id_2",
                    "Score", "Keep", "Move"])
        w.writerows(out)
    print("Written: fix_cross_name_dups.csv")
    if not a.commit:
        print("\nPreview only. Check the file, then rerun with --commit (REVIEW rows are never moved).")
        return
    moved, gone = 0, set()
    for r in out:
        if r[0] == "REVIEW" or not r[12]:
            continue
        mv, kp = int(r[12]), int(r[11])
        if kp in gone or mv in gone:                          # chains of 3+ copies: never drop the last one
            continue
        n = cur.execute(f"INSERT INTO dbo.College_Scores_Duplicates ({DUP_COLS}) "
                        "SELECT Access_ID, ?, [Date], Season, Home, Visitor, Home_Score, Visitor_Score, "
                        "Neutral, Line, Location, Location2, ?, GETDATE() FROM dbo.College_Scores WHERE Access_ID = ?",
                        kp, f"same game under another opponent name ({r[0]}: kept {r[4] if int(r[6]) == kp else r[7]})",
                        mv).rowcount
        if n:
            cur.execute("DELETE FROM dbo.College_Scores WHERE Access_ID = ?", mv)
            gone.add(mv)
            moved += 1
    conn.commit()
    print(f"Committed: {moved} rows moved to College_Scores_Duplicates.")


if __name__ == "__main__":
    main()
