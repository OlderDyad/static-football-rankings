"""
undo_schedule_import.py -- run on Windows. Preview by default; --commit applies.

Takes back games that import_schedule_csv.py inserted under a WRONG opponent match, so the CSV can be
re-imported after the name is fixed in schedules/schedule_name_map.csv. For each --raw name, the
opponent-history URLs of that name are read from the CSV's Source column; the inserted rows
(Access_ID >= 900000000, Source = one of those URLs, the CSV's team on one side) are moved to
College_Scores_Duplicates (Kept_Access_ID = 0, Reason = 'wrong name match: ...') and deleted.
Games that were DUPLICATE/CONFLICT on the first import were never inserted, so nothing else changes.

Usage:  python undo_schedule_import.py schedules/Northeastern_St_opponent_history.csv --raw "Northwestern Oklahoma State University"
        (several --raw allowed) ... --commit
"""
import argparse, csv
from collections import Counter

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--raw", action="append", required=True)
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.file, encoding="utf-8-sig")))
    team = rows[0]["Team"].strip()
    urls = {}
    for r in rows:
        if r["Opponent_Raw"].strip() in a.raw and r.get("Source"):
            urls[r["Source"][:255]] = r["Opponent_Raw"].strip()
    missing = set(a.raw) - set(urls.values())
    if missing:
        print("Not in the CSV:", ", ".join(sorted(missing)))
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    hits = []
    for u, raw in urls.items():
        for aid, s, d, h, hs, v, vs in cur.execute(
                "SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score FROM dbo.College_Scores "
                "WHERE Access_ID >= 900000000 AND Source = ? AND (Home = ? OR Visitor = ?)", u, team, team).fetchall():
            hits.append((aid, s, d, h, hs, v, vs, raw))
    c = Counter((x[7], x[5] if x[3] == team else x[3]) for x in hits)
    print(f"{team}: {len(hits)} inserted games to take back")
    for (raw, opp), n in sorted(c.items()):
        print(f"  {n:4}  {raw!r} was matched to {opp!r}")
    if not a.commit:
        print("\nPreview only. Re-run with --commit, then fix schedule_name_map.csv and re-import the CSV.")
        return
    try:
        for aid, s, d, h, hs, v, vs, raw in hits:
            cur.execute("""
                INSERT INTO dbo.College_Scores_Duplicates
                    (Access_ID, Kept_Access_ID, Game_Date, Season, Home, Visitor, Home_Score, Visitor_Score,
                     Neutral, Line, Location, Location2, Reason, Moved_At)
                SELECT Access_ID, 0, Date, Season, Home, Visitor, Home_Score, Visitor_Score,
                       Neutral, Line, Location, Location2, ?, GETDATE()
                FROM dbo.College_Scores WHERE Access_ID = ?""",
                        f"wrong name match: '{raw}' imported as '{v if h == team else h}'", aid)
            cur.execute("DELETE FROM dbo.College_Scores WHERE Access_ID = ?", aid)
        conn.commit()
        print(f"\nCommitted: {len(hits)} games moved to College_Scores_Duplicates.")
    except Exception as e:
        conn.rollback()
        print(f"\nRolled back: {e}")


if __name__ == "__main__":
    main()
