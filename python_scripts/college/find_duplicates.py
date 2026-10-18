"""
find_duplicates.py  (analysis only -- writes duplicate_review.csv, changes nothing)

Works on the Access export with the committed name fixes applied and the
1,001 already-quarantined St Mary's/John's/Francis/Thomas duplicates removed,
i.e. the same games now in College_Scores_Staging.

Groups:
  A  same date (real date), same two teams, same score       -> duplicate, keep one
  B  same date (real date), same two teams, different score  -> duplicate, scores conflict
  C  placeholder date (Aug 1 = date unknown), same teams      -> may be two real games
  D  same season, same teams, same score, dates <= 7 days apart -> probable date typo duplicate
  E  team listed as playing itself

Proposed action per row: KEEP / MOVE (to College_Scores_Duplicates) / REVIEW.
Keep rule (A, D): the copy whose home team is supported by a Location2 city if
only one copy has it, else the lowest Access_ID (oldest entry).
Keep rule (B): drop copies with an obvious bad score (0-0, or a 1/2 win marker);
otherwise REVIEW.
"""
import csv, os, re
from collections import defaultdict, Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))


def clean(n):
    return re.sub(r"\s+", " ", (n or "").strip())


def main():
    fix, dup_done = {}, set()
    for r in csv.DictReader(open(os.path.join(HERE, "name_fixes/college_name_fixes.csv"), encoding="utf-8")):
        fix[(r["Access_ID"], r["Side"])] = r["New_Name"]
        if r["Is_Duplicate"] == "1":
            dup_done.add(r["Access_ID"])
    games = []
    for r in csv.DictReader(open(os.path.join(HERE, "access_export/access_scores.csv"), encoding="utf-8")):
        if r["ID"] in dup_done:
            continue
        games.append(dict(id=int(r["ID"]), d=r["Date"][:10], s=int(float(r["Season"])),
                          h=clean(fix.get((r["ID"], "Home"), r["Home"])),
                          v=clean(fix.get((r["ID"], "Visitor"), r["Visitor"])),
                          hs=int(float(r["Home Score"])), vs=int(float(r["Visitor Score"])),
                          n=r["Nuetral"] == "True", l2=clean(r["Location2"])))

    def pair(x): return (min(x["h"], x["v"]), max(x["h"], x["v"]))
    def sc(x, home): return (x["hs"], x["vs"]) if x["h"] == home else (x["vs"], x["hs"])
    def bad(x): return (x["hs"] == 0 and x["vs"] == 0) or max(x["hs"], x["vs"]) <= 2

    out, gid = [], 0

    def emit(group, cls, members, actions, note):
        nonlocal gid
        gid += 1
        for x in members:
            out.append([f"{cls}{gid}", cls, x["id"], x["s"], x["d"], x["v"], x["vs"], x["hs"], x["h"],
                        "Y" if x["n"] else "", x["l2"], actions[x["id"]], note, ""])

    def keep_one(members):
        with_city = [x for x in members if x["l2"] and not x["l2"].isdigit()]
        k = with_city[0] if len(with_city) == 1 else min(members, key=lambda x: x["id"])
        return {x["id"]: ("KEEP" if x is k else "MOVE") for x in members}

    by_date = defaultdict(list)
    for x in games:
        by_date[(x["d"],) + pair(x)].append(x)
    in_groups = set()
    for k, m in by_date.items():
        if len(m) < 2:
            continue
        a = m[0]
        same = all(sc(x, a["h"]) == sc(a, a["h"]) for x in m)
        placeholder = k[0][5:] == "08-01"
        flipped = any(x["h"] != a["h"] for x in m)
        note = "home team differs between copies" if flipped else ""
        if placeholder:
            if same:
                emit(k, "C", m, keep_one(m), "date unknown (Aug 1), same score -> probably one game")
            else:
                emit(k, "C", m, {x["id"]: "KEEP" for x in m}, "date unknown (Aug 1), different scores -> probably two games")
        elif same:
            emit(k, "A", m, keep_one(m), note)
        else:
            good = [x for x in m if not bad(x)]
            if 0 < len(good) < len(m) and len(good) == 1:
                acts = {x["id"]: ("KEEP" if x in good else "MOVE") for x in m}
                emit(k, "B", m, acts, "other copy has 0-0 or 1/2 win-marker score")
            else:
                emit(k, "B", m, {x["id"]: "REVIEW" for x in m}, "scores conflict" + ("; " + note if note else ""))
        in_groups.update(x["id"] for x in m)

    by_season = defaultdict(list)
    for x in games:
        by_season[(x["s"],) + pair(x)].append(x)
    for k, m in by_season.items():
        m = [x for x in m if x["id"] not in in_groups and x["d"][5:] != "08-01"]
        used = set()
        for i in range(len(m)):
            for j in range(i + 1, len(m)):
                a, b = m[i], m[j]
                if a["id"] in used or b["id"] in used or a["d"] == b["d"]:
                    continue
                if sc(a, a["h"]) == sc(b, a["h"]) and abs((date.fromisoformat(a["d"]) - date.fromisoformat(b["d"])).days) <= 7:
                    emit(k, "D", [a, b], {a["id"]: "REVIEW", b["id"]: "REVIEW"}, "same score, dates within 7 days")
                    used.update((a["id"], b["id"]))

    for x in games:
        if x["h"] == x["v"]:
            emit(None, "E", [x], {x["id"]: "REVIEW"}, "team listed as playing itself")

    with open(os.path.join(HERE, "duplicate_review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Group", "Class", "Access_ID", "Season", "Date", "Visitor", "Visitor_Score", "Home_Score",
                    "Home", "Neutral", "Location2", "Proposed_Action", "Note", "Your_Action"])
        w.writerows(out)

    groups = Counter(r[1] for r in {r[0]: r for r in out}.values())
    acts = Counter((r[1], r[11]) for r in out)
    print("groups by class:", dict(sorted(groups.items())))
    for k in sorted(acts):
        print(f"  {k[0]} {k[1]:7s} {acts[k]:6,}")


if __name__ == "__main__":
    main()
