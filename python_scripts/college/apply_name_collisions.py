"""
apply_name_collisions.py  -- run on Windows. Preview by default; --commit applies.

Applies name_collision_review.csv (from split_name_collisions.py): renames the
Home or Visitor of each listed game to the proposed school, by Access_ID, only if
the row still holds the old name (safe to re-run).

  --include-weak            also apply "(weak)" proposals (undated-game hint)
  --skip "Opponent" ...     leave games against these opponents unchanged
  --only "California" ...   apply only these collision names

Round-4 review files also carry:
  Proposed_Name CHECK   never applied (decide by hand, then edit the row)
  Dup_Of                the game already exists under the new name -> this row is moved to
                        College_Scores_Duplicates (Kept_Access_ID = Dup_Of) instead of renamed
  New_Date              date corrected in the same transaction

Usage:  python apply_name_collisions.py
        python apply_name_collisions.py --skip "Pennsylvania" --commit
"""
import argparse, csv, os
from collections import Counter

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))
# new names that are not colleges (default for a new name is Kind College, state from suffix)
NEW_KIND = {"Detroit Independents": ("Club", "MI"), "Detroit Athletic Club (MI)": ("Club", "MI")}


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
        if prop == "CHECK" or not prop:
            continue
        if "weak" in prop and not a.include_weak:
            continue
        if r["Opponent"] in a.skip or (a.only and r["Name_Now"] not in a.only):
            continue
        todo.append((int(r["Access_ID"]), r["Side"], r["Name_Now"], prop.replace(" (weak)", ""),
                     int(r["Dup_Of"]) if r.get("Dup_Of") else None, r.get("New_Date") or None))
    checks = sum(1 for r in rows if r["Proposed_Name"] == "CHECK")
    c = Counter((t[2], t[3], "duplicate -> moved" if t[4] else "renamed") for t in todo)
    for (old, new, how), n in sorted(c.items()):
        print(f"  {old:16s} -> {new:26s} {how:18s} {n:4d}")
    dates = [t for t in todo if t[5]]
    for t in dates:
        print(f"  date fix: Access_ID {t[0]} -> {t[5]}")
    if checks:
        print(f"  CHECK rows left alone: {checks}")
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
                kind, st = NEW_KIND.get(new, ("College", st))
                cur.execute("INSERT INTO dbo.College_Team_Names (Team_Name, Kind, State, State_Source) "
                            "VALUES (?, ?, ?, 'name suffix')", new, kind, st)
                print(f"  added team name {new} ({kind})")
        moved = dated = 0
        for aid, side, old, new, dup, nd in todo:
            if nd:
                cur.execute("UPDATE dbo.College_Scores SET Date = ? WHERE Access_ID = ?", nd, aid)
                dated += cur.rowcount
            if dup:
                n = cur.execute("""
                    INSERT INTO dbo.College_Scores_Duplicates
                        (Access_ID, Kept_Access_ID, Game_Date, Season, Home, Visitor, Home_Score, Visitor_Score,
                         Neutral, Line, Location, Location2, Reason, Moved_At)
                    SELECT Access_ID, ?, Date, Season, Home, Visitor, Home_Score, Visitor_Score,
                           Neutral, Line, Location, Location2, ?, GETDATE()
                    FROM dbo.College_Scores WHERE Access_ID = ? AND [""" + side + """] = ?""",
                                dup, f"'{old}' row duplicates the {new} game (name collision round 4)",
                                aid, old).rowcount
                if n:
                    cur.execute("DELETE FROM dbo.College_Scores WHERE Access_ID = ?", aid)
                    moved += 1
                continue
            cur.execute(f"UPDATE dbo.College_Scores SET [{side}] = ? WHERE Access_ID = ? AND [{side}] = ?",
                        new, aid, old)
            done += cur.rowcount
        conn.commit()
        print(f"\nCommitted: {done} games renamed, {moved} duplicates moved, {dated} dates fixed "
              f"({len(todo) - done - moved} already changed or not found).")
    except Exception as e:
        conn.rollback()
        print(f"Rolled back: {e}")


if __name__ == "__main__":
    main()
