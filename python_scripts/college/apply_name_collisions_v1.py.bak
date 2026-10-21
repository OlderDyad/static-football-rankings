"""
apply_name_collisions.py  -- run on Windows. Preview by default; --commit applies.

Applies name_collision_review.csv (from split_name_collisions.py): renames the
Home or Visitor of each listed game to the proposed school, by Access_ID, only if
the row still holds the old name (safe to re-run).

  --include-weak            also apply "(weak)" proposals (undated-game hint)
  --skip "Opponent" ...     leave games against these opponents unchanged
  --only "California" ...   apply only these collision names

Usage:  python apply_name_collisions.py
        python apply_name_collisions.py --skip "Pennsylvania" --commit
"""
import argparse, csv, os
from collections import Counter

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-weak", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--file", default="name_collision_review.csv",
                    help="review file (residual_collision_review.csv from suspect_collisions.py)")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(os.path.join(HERE, a.file), encoding="utf-8")))
    todo = []
    for r in rows:
        prop = r["Proposed_Name"]
        if "weak" in prop and not a.include_weak:
            continue
        if r["Opponent"] in a.skip or (a.only and r["Name_Now"] not in a.only):
            continue
        todo.append((int(r["Access_ID"]), r["Side"], r["Name_Now"], prop.replace(" (weak)", "")))
    c = Counter((t[2], t[3]) for t in todo)
    for (old, new), n in sorted(c.items()):
        print(f"  {old:14s} -> {new:14s} {n:4d} games")
    if not a.commit:
        print(f"\nPreview: {len(todo)} games. Re-run with --commit to apply.")
        return
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    done = 0
    try:
        # schools that never had their own name yet (e.g. Union TN, King TN) get a College_Team_Names row
        for new in sorted({t[3] for t in todo}):
            if not cur.execute("SELECT 1 FROM dbo.College_Team_Names WHERE Team_Name = ?", new).fetchone():
                st = new.split()[-1] if len(new.split()[-1]) == 2 and new.split()[-1].isupper() else None
                cur.execute("INSERT INTO dbo.College_Team_Names (Team_Name, Kind, State, State_Source) "
                            "VALUES (?, 'College', ?, 'name suffix')", new, st)
                print(f"  added team name {new}")
        for aid, side, old, new in todo:
            cur.execute(f"UPDATE dbo.College_Scores SET [{side}] = ? WHERE Access_ID = ? AND [{side}] = ?",
                        new, aid, old)
            done += cur.rowcount
        conn.commit()
        print(f"\nCommitted: {done} of {len(todo)} games renamed "
              f"({len(todo) - done} already changed or not found).")
    except Exception as e:
        conn.rollback()
        print(f"Rolled back: {e}")


if __name__ == "__main__":
    main()
