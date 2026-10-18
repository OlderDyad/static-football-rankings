"""
build_name_fixes.py  (runs on the exported CSVs; changes nothing in SQL)

Turns the approved name decisions into two load files:

  name_fixes/college_name_fixes.csv
      One row per game side whose team name changes (ID-based, Access_ID + Side):
        Fix_Type = whitespace_case  -- trim/collapse spaces, majority capitalization
                   merge            -- approved variant merges (name_review.csv, Approve=Y)
                   split            -- bare St Mary's/John's/Francis/Thomas -> coded school
      Is_Duplicate = 1 when the renamed game already exists under the coded name
      (same date, same opponent) -- those rows get quarantined, not kept twice.

  name_fixes/college_team_aliases.csv
      Alias_Name -> Canonical_Name for real spelling variants (merges), kept
      for matching names from future sources (wolferatings scraper etc.).
"""
import csv, os, re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "access_export")
OUT = os.path.join(HERE, "name_fixes")


def clean(n):
    return re.sub(r"\s+", " ", (n or "").strip())


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(EXP, "access_scores.csv"), encoding="utf-8")))

    # 1. majority capitalization per case-insensitive name
    cnt = Counter()
    for r in rows:
        cnt[clean(r["Home"])] += 1; cnt[clean(r["Visitor"])] += 1
    groups = defaultdict(list)
    for n in cnt:
        groups[n.lower()].append(n)
    case = {}
    for v in groups.values():
        best = max(v, key=lambda x: (cnt[x], x != x.lower(), x != x.upper()))
        for x in v:
            case[x] = best

    # 2. approved merges
    merge = {}
    for r in csv.DictReader(open(os.path.join(HERE, "name_review.csv"), encoding="utf-8")):
        if (r["Approve(Y/N)"] or "").strip().upper() == "Y" and r["Name"] != r["Suggested_Canonical"]:
            merge[r["Name"]] = r["Suggested_Canonical"]

    # 3. game-level splits (Override_Name wins over Assigned_Name)
    split = {}
    for r in csv.DictReader(open(os.path.join(HERE, "ambiguous_split_review.csv"), encoding="utf-8")):
        new = (r["Override_Name"] or "").strip() or r["Assigned_Name"]
        if new:
            split[(r["Access_ID"], r["Side"])] = (new, r["Duplicate"] == "Y")

    fixes, types = [], Counter()
    for r in rows:
        for side in ("Home", "Visitor"):
            raw = r[side]
            name, ftype, dup = case[clean(raw)], "whitespace_case", 0
            if name in merge:
                name, ftype = merge[name], "merge"
            if (r["ID"], side) in split:
                name, d = split[(r["ID"], side)]
                ftype, dup = "split", int(d)
            if name != raw:
                fixes.append([r["ID"], side, raw, name, ftype, dup])
                types[ftype] += 1

    with open(os.path.join(OUT, "college_name_fixes.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Side", "Old_Name", "New_Name", "Fix_Type", "Is_Duplicate"])
        w.writerows(fixes)
    with open(os.path.join(OUT, "college_team_aliases.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Alias_Name", "Canonical_Name", "Reason"])
        for a, c in sorted(merge.items()):
            w.writerow([a, c, "Access name review 2026-10-15"])

    print(f"name fixes: {len(fixes):,}  {dict(types)}")
    print(f"duplicates flagged: {sum(f[5] for f in fixes):,}")
    print(f"aliases: {len(merge)}")
    final = Counter()
    fx = {(f[0], f[1]): f[3] for f in fixes}
    for r in rows:
        for side in ("Home", "Visitor"):
            final[fx.get((r["ID"], side), r[side])] += 1
    print(f"distinct team names after fixes: {len(final):,}")


if __name__ == "__main__":
    main()
