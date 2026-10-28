"""
fix_lost_points.py -- run on Windows. Preview by default; --commit applies.

Some older source blocks lost one team's points (Northern Colorado 264-265k, Central Arkansas 302k, ...):
our row shows 26-0 or 0-0 where the real score was 26-9. After an import preview, this reads the
review file(s) and takes the SOURCE score for CONFLICT rows where
    our score has a 0 that the source does not, and the other team's points match exactly,
    or ours is 0-0 and the source has points.
Every other conflict is left alone (flag it with import_schedule_csv.py --flag-conflicts as usual).
Margin is recomputed and Score_Disputed cleared on the rows it fixes.

Usage:  python fix_lost_points.py schedules\\Western_Colorado_opponent_history_review.csv [more files] [--commit]
Then rerun the import (the fixed games now show as DUPLICATE) and commit it.
"""
import argparse, csv

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")


def lost(ours, t, o):
    a, b = ours
    return (a == 0 and t > 0 and b == o) or (b == 0 and o > 0 and a == t) or (a == 0 and b == 0 and t + o > 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    fixes = {}
    for fn in a.files:
        for x in csv.DictReader(open(fn, encoding="utf-8-sig")):
            if x.get("Action") != "CONFLICT" or not x.get("Ours"):
                continue
            ours = tuple(int(v) for v in x["Ours"].split("-"))
            t, o = int(x["Team_Score"]), int(x["Opp_Score"])
            if lost(ours, t, o):
                fixes[int(x["Access_ID"])] = (x["Team"].strip(), t, o, x["Season"], x["Opponent"], x["Ours"])
    for aid, (team, t, o, s, opp, ours) in sorted(fixes.items(), key=lambda k: k[1][3]):
        print(f"  {s} {team} {t}-{o} {opp}   ours {ours}   (Access_ID {aid})")
    print(f"{len(fixes)} lost-points rows")
    if not a.commit:
        print("\nPreview only. Re-run with --commit.")
        return
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    n = 0
    try:
        for aid, (team, t, o, *_r) in fixes.items():
            n += cur.execute("""
                UPDATE dbo.College_Scores SET
                    Home_Score    = CASE WHEN Home = ? THEN ? ELSE ? END,
                    Visitor_Score = CASE WHEN Home = ? THEN ? ELSE ? END,
                    Score_Disputed = 0
                WHERE Access_ID = ? AND ? IN (Home, Visitor)""", team, t, o, team, o, t, aid, team).rowcount
            cur.execute("UPDATE dbo.College_Scores SET Margin = Home_Score - Visitor_Score WHERE Access_ID = ?", aid)
        conn.commit()
        print(f"\nCommitted: {n} scores fixed.")
    except Exception as e:
        conn.rollback()
        print(f"\nRolled back: {e}")


if __name__ == "__main__":
    main()
