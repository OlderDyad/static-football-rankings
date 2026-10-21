"""
fix_newspaper_names.py  -- run on Windows. Preview by default; --commit applies.

Repairs college names given to newspaper games by newspaper_college_split.py, then removes
any duplicate games that the repair exposes (same season, same two teams, same score, dates
within 3 days or an Aug-1 placeholder):
  - the older row (Access data, or the first newspaper copy) is kept, and gets the paper's
    date if it only had the Aug-1 placeholder
  - the other row goes to College_Scores_Duplicates
Only rows whose Source starts with 'Newspaper' are renamed.

Also: removes the College_Team_Names rows the split added for the wrong names, adds new
college teams (e.g. Western Reserve), and updates newspaper_college_map.csv so later
seasons map these names correctly.

Usage:  python fix_newspaper_names.py --season 1906
        python fix_newspaper_names.py --season 1906 --commit
"""
import argparse, csv, os
from collections import defaultdict

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(HERE, "newspaper_college_map.csv")

# wrong name in College_Scores -> right college name ; HS name for the map file
RENAMES = [
    ("United States Military Academy (NY)", "Army", "United States Military Academy (NY)"),
    ("United States Naval Academy (MD)", "Navy", "United States Naval Academy (MD)"),
    ("Carlisle Indians (PA)", "Carlisle Indian School", "Carlisle Indians (PA)"),
    ("Washington & Jefferson", "Wash & Jeff", "Washington & Jefferson College (PA)"),
    ("Cornell", "Cornell NY", "Cornell University (NY)"),
    ("Case School of Applied Science (OH)", "Case Western Reserve", "Case School of Applied Science (OH)"),
    ("Western Reserve University (OH)", "Western Reserve", "Western Reserve University (OH)"),
]
NEW_COLLEGES = {"Western Reserve": "OH"}            # college teams not yet in College_Team_Names


def aug1(d):
    return d is None or (d.month == 8 and d.day == 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()

    for old, new, _ in RENAMES:
        n = cur.execute("""SELECT COUNT(*) FROM dbo.College_Scores WHERE Season = ? AND Source LIKE 'Newspaper%'
                           AND ? IN (Home, Visitor)""", a.season, old).fetchone()[0]
        print(f"  rename {old!r:42} -> {new!r:24} {n} games")
        if a.commit and n:
            cur.execute("UPDATE dbo.College_Scores SET Home = ? WHERE Season = ? AND Source LIKE 'Newspaper%' AND Home = ?",
                        new, a.season, old)
            cur.execute("UPDATE dbo.College_Scores SET Visitor = ? WHERE Season = ? AND Source LIKE 'Newspaper%' AND Visitor = ?",
                        new, a.season, old)

    # duplicates now visible (within the season, after renames when committing)
    rows = cur.execute("""SELECT Access_ID, Date, Home, Home_Score, Visitor, Visitor_Score, ISNULL(Source, '')
                          FROM dbo.College_Scores WHERE Season = ?""", a.season).fetchall()
    ren = {o: n for o, n, _ in RENAMES}
    groups = defaultdict(list)
    for aid, d, h, hs, v, vs, src in rows:
        if not a.commit and src.startswith("Newspaper"):
            h, v = ren.get(h, h), ren.get(v, v)          # preview: show what renaming will expose
        groups[frozenset((h, v))].append((aid, d, h, hs, v, vs, src))
    dups, datefix = [], []
    for g in groups.values():
        g.sort(key=lambda x: (x[6].startswith("Newspaper"), x[0]))   # Access rows first, then oldest
        kept = []
        for r in g:
            match = None
            for k in kept:
                same = ({k[2]: k[3], k[4]: k[5]}.get(r[2]), {k[2]: k[3], k[4]: k[5]}.get(r[4])) == (r[3], r[5])
                if same and (aug1(k[1]) or aug1(r[1]) or abs((k[1] - r[1]).days) <= 3):
                    match = k
                    break
            if match:
                dups.append((r[0], match[0]))
                if aug1(match[1]) and not aug1(r[1]):
                    datefix.append((match[0], r[1]))
            else:
                kept.append(r)
    print(f"\n{len(dups)} duplicate games to move to College_Scores_Duplicates, {len(datefix)} dates to fill")
    for d_, k_ in dups[:20]:
        r = next(x for x in rows if x[0] == d_)
        print(f"   {r[1]} {r[2]} {r[3]}-{r[5]} {r[4]}  (keeps Access_ID {k_})")

    if not a.commit:
        print("\nPreview only. Re-run with --commit to apply.")
        return
    try:
        cols = [r[0] for r in cur.execute("""SELECT c.COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS c
              JOIN INFORMATION_SCHEMA.COLUMNS d ON d.TABLE_NAME = 'College_Scores_Duplicates' AND d.COLUMN_NAME = c.COLUMN_NAME
              WHERE c.TABLE_NAME = 'College_Scores'
                AND COLUMNPROPERTY(OBJECT_ID('dbo.College_Scores_Duplicates'), c.COLUMN_NAME, 'IsIdentity') = 0""")]
        cl = ", ".join(f"[{c}]" for c in cols)
        for keep, d in datefix:
            cur.execute("UPDATE dbo.College_Scores SET Date = ? WHERE Access_ID = ?", d, keep)
        for dup, _ in dups:
            cur.execute(f"INSERT INTO dbo.College_Scores_Duplicates ({cl}) SELECT {cl} FROM dbo.College_Scores WHERE Access_ID = ?", dup)
            cur.execute("DELETE FROM dbo.College_Scores WHERE Access_ID = ?", dup)
        # team names: drop the wrong ones the split added, add new colleges
        for old, new, _ in RENAMES:
            if not cur.execute("SELECT 1 FROM dbo.College_Scores WHERE ? IN (Home, Visitor)", old).fetchone():
                cur.execute("DELETE FROM dbo.College_Team_Names WHERE Team_Name = ? AND State_Source = 'newspaper'", old)
        for t, st in NEW_COLLEGES.items():
            if not cur.execute("SELECT 1 FROM dbo.College_Team_Names WHERE Team_Name = ?", t).fetchone():
                cur.execute("INSERT INTO dbo.College_Team_Names (Team_Name, Kind, State, State_Source) "
                            "VALUES (?, 'College', ?, 'newspaper')", t, st)
        conn.commit()
        print(f"\nCommitted: renames done, {len(dups)} duplicates moved, {len(datefix)} dates filled.")
    except Exception as e:
        conn.rollback()
        print(f"\nRolled back: {e}")
        return
    # map file: later seasons map these HS names straight to the right college
    rows_ = list(csv.DictReader(open(MAP_FILE, encoding="utf-8-sig"))) if os.path.exists(MAP_FILE) else []
    have = {r["HS_Name"]: r for r in rows_}
    for _, new, hsname in RENAMES:
        if hsname in have:
            have[hsname]["College_Name"] = new
        else:
            rows_.append({"HS_Name": hsname, "College_Name": new, "Note": "fix_newspaper_names"})
    with open(MAP_FILE, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["HS_Name", "College_Name", "Note"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_)
    print("newspaper_college_map.csv updated.")


if __name__ == "__main__":
    main()
