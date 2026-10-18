"""
merge_same_school.py  -- run on Windows. Preview by default; --commit applies.

Merges two names that are the SAME school (e.g. "SW Missouri St" -> "Missouri St",
the school's modern name). Many games exist under both names (entered twice from
different sources), so a plain rename would double them. For every game of the
OLD name:

  DUPLICATE  same season, same opponent, same score (either home/away order)
             -> OLD row moved to College_Scores_Duplicates (NEW row kept)
  CONFLICT   same season, same opponent, different score, dates within 10 days
             -> default-and-flag rule: keep the lower Access_ID, move the other,
                Score_Disputed = 1 on the kept row
  REVIEW     same season and opponent, different score, a date unknown (Aug 1) --
             could be a second meeting or a conflict; left unchanged, listed
  SELF       old name vs new name (the school playing itself) -> listed, unchanged
  RENAME     everything else -> OLD name replaced by NEW name

Output: merge_<old>_review.csv with every row's action.
Usage:  python merge_same_school.py --old "SW Missouri St" --new "Missouri St"
        python merge_same_school.py --old "SW Missouri St" --new "Missouri St" --commit
"""
import argparse, csv, os, re

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))


def aug1(d):
    return d is None or (d.month == 8 and d.day == 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()

    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score
        FROM dbo.College_Scores WHERE Home IN (?, ?) OR Visitor IN (?, ?)""",
                       a.old, a.new, a.old, a.new).fetchall()

    def view(r, name):
        aid, s, d, h, hs, v, vs = r
        return (aid, s, d, v if h == name else h, hs if h == name else vs, vs if h == name else hs,
                "Home" if h == name else "Visitor")

    old = [view(r, a.old) for r in rows if a.old in (r[3], r[5])]
    new = [view(r, a.new) for r in rows if a.new in (r[3], r[5]) and a.old not in (r[3], r[5])]
    by_key = {}
    for n in new:
        by_key.setdefault((n[1], n[3]), []).append(n)

    used, actions = set(), []
    for o in sorted(old, key=lambda x: x[0]):
        aid, s, d, opp, sf, sa, side = o
        if opp == a.new:
            actions.append((o, "SELF", None, "old name plays new name"))
            continue
        cands = [n for n in by_key.get((s, opp), []) if n[0] not in used]
        exact = [n for n in cands if (n[4], n[5]) == (sf, sa)]
        if exact:
            used.add(exact[0][0])
            actions.append((o, "DUPLICATE", exact[0][0], "same score"))
            continue
        near = [n for n in cands if not aug1(d) and not aug1(n[2]) and abs((n[2] - d).days) <= 10]
        if near:
            used.add(near[0][0])
            actions.append((o, "CONFLICT", near[0][0], f"scores {sf}-{sa} vs {near[0][4]}-{near[0][5]}"))
            continue
        undated = [n for n in cands if aug1(d) or aug1(n[2])]
        if undated:
            actions.append((o, "REVIEW", undated[0][0], f"date unknown; scores {sf}-{sa} vs {undated[0][4]}-{undated[0][5]}"))
            continue
        actions.append((o, "RENAME", None, ""))

    fn = os.path.join(HERE, "merge_" + re.sub(r"\W+", "_", a.old).strip("_") + "_review.csv")
    with open(fn, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Season", "Date", "Opponent", "Score_For", "Score_Against", "Side",
                    "Action", "Matched_New_Access_ID", "Note"])
        for o, act, m, note in actions:
            w.writerow(list(o) + [act, m or "", note])
    from collections import Counter
    c = Counter(x[1] for x in actions)
    print(f"{a.old} -> {a.new}: {len(old):,} old-name games, {len(new):,} new-name games")
    for k in ("DUPLICATE", "CONFLICT", "REVIEW", "SELF", "RENAME"):
        print(f"  {k:9s} {c.get(k, 0):5d}")
    print(f"Written: {os.path.basename(fn)}")
    if not a.commit:
        print("\nPreview only. Re-run with --commit to apply DUPLICATE, CONFLICT and RENAME.")
        return

    # columns common to College_Scores and College_Scores_Duplicates
    cols = lambda t: [r[0] for r in cur.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION", t)]
    dup_cols = cols("College_Scores_Duplicates")
    common = [x for x in cols("College_Scores") if x in dup_cols and
              not cur.execute("SELECT COLUMNPROPERTY(OBJECT_ID('dbo.College_Scores_Duplicates'), ?, 'IsIdentity')",
                              x).fetchone()[0]]
    collist = ", ".join(f"[{x}]" for x in common)
    try:
        moved = renamed = flagged = 0
        for o, act, m, note in actions:
            aid, side = o[0], o[6]
            if act == "DUPLICATE" or act == "CONFLICT":
                drop, keep = aid, m
                if act == "CONFLICT" and m < aid:
                    pass                                  # new-name row is older: keep it
                elif act == "CONFLICT":
                    drop, keep = m, aid                   # old-name row is older: keep it, rename it
                    cur.execute(f"UPDATE dbo.College_Scores SET [{side}] = ? WHERE Access_ID = ?", a.new, aid)
                    renamed += 1
                cur.execute(f"INSERT INTO dbo.College_Scores_Duplicates ({collist}) "
                            f"SELECT {collist} FROM dbo.College_Scores WHERE Access_ID = ?", drop)
                cur.execute("DELETE FROM dbo.College_Scores WHERE Access_ID = ?", drop)
                moved += 1
                if act == "CONFLICT":
                    cur.execute("UPDATE dbo.College_Scores SET Score_Disputed = 1 WHERE Access_ID = ?", keep)
                    flagged += 1
            elif act == "RENAME":
                cur.execute(f"UPDATE dbo.College_Scores SET [{side}] = ? WHERE Access_ID = ?", a.new, aid)
                renamed += 1
        left = cur.execute("SELECT COUNT(*) FROM dbo.College_Scores WHERE Home = ? OR Visitor = ?",
                           a.old, a.old).fetchone()[0]
        expect = sum(1 for x in actions if x[1] in ("REVIEW", "SELF"))
        if left != expect:
            raise RuntimeError(f"{left} old-name rows left, expected {expect}")
        conn.commit()
        print(f"\nCommitted: moved {moved}, renamed {renamed}, flagged disputed {flagged}; "
              f"{left} old-name rows left (REVIEW/SELF).")
    except Exception as e:
        conn.rollback()
        print(f"\nRolled back: {e}")


if __name__ == "__main__":
    main()
