"""
build_coach_ids.py -- give every coach a Coach_ID (one person = one ID).

Input : name_fixes/college_coach_seasons.csv
Output: name_fixes/college_coaches.csv          Coach_ID, Coach_Name, Name_Variants, Teams, First, Last, Seasons
        name_fixes/college_coach_seasons_ids.csv the coach-season rows + Coach_ID
        name_fixes/coach_id_review.csv           merges/splits worth a look

How:
 1. Tenures: at one school, consecutive seasons whose coach names are the same person
    (same last name, compatible first name / nickname) form one tenure -- this joins the
    Access spelling and the Wikipedia spelling of one man ("Paul W. \"Bear\" Bryant" / "Bear Bryant").
 2. Careers: tenures at different schools are joined when the names match (first or nickname
    + last name) and the tenures do not overlap in time (a coach can't lead two schools at once;
    a 1-season overlap is allowed for a mid-season move). Two same-named coaches active at the
    same time stay separate (Todd Knight, Ouachita Baptist vs Todd Knight, Newberry).
"""
import csv, os, re
from collections import defaultdict, Counter
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "name_fixes")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def parts(name):
    """-> (first-name tokens incl. nickname, last name)"""
    n = name.replace("“", '"').replace("”", '"').replace("’", "'")
    nick = [x.lower() for x in re.findall(r'"([^"]+)"', n)]
    n = re.sub(r'"[^"]+"', " ", n)
    n = re.sub(r"\([^)]*\)", " ", n)
    toks = [t for t in re.findall(r"[A-Za-z'\-]+", n)]
    suf = {t.lower() for t in toks if t.lower().strip(".") in SUFFIX}
    toks = [t for t in toks if t.lower().strip(".") not in SUFFIX]
    if not toks:
        return set(), ""
    last = toks[-1].lower()
    firsts = {toks[0].lower()} | set(nick)
    if len(toks[0]) == 1 and len(toks) > 2:      # "W. Stanley Smith"
        firsts.add(toks[1].lower())
    return firsts, last


def same_last(a, b):
    return a == b or (len(a) > 3 and len(b) > 3 and SequenceMatcher(None, a, b).ratio() >= 0.85)


def suffix(name):
    return {t.lower().strip(".") for t in re.findall(r"[A-Za-z.]+", name) if t.lower().strip(".") in SUFFIX}


def compatible(n1, n2):
    f1, l1 = parts(n1)
    f2, l2 = parts(n2)
    if not l1 or not l2 or not same_last(l1, l2):
        return False
    s1, s2 = suffix(n1), suffix(n2)
    if s1 and s2 and s1 != s2:          # Amos Alonzo Stagg Sr. is not Amos Alonzo Stagg Jr.
        return False
    if f1 & f2:
        return True
    # an initial matches a name with that first letter ("W. S. Borland" ~ "William Borland")
    return any(a[0] == b[0] for a in f1 for b in f2 if len(a) == 1 or len(b) == 1)


def main():
    rows = [r for r in csv.DictReader(open(os.path.join(FX, "college_coach_seasons.csv"), encoding="utf-8"))
            if r["Role"] != "No coach"]
    by_team = defaultdict(list)
    for i, r in enumerate(rows):
        by_team[r["Team_Name"]].append((int(r["Season"]), r["Coach"], i))

    # ---- 1. tenures ----
    tenures = []          # dict(team, names Counter, seasons set, rows list)
    row_tenure = {}
    for team, lst in by_team.items():
        lst.sort()
        open_t = []       # tenures still running at this team
        for season, coach, i in lst:
            hit = None
            for t in open_t:
                if season - max(t["seasons"]) <= 1 and any(compatible(coach, n) for n in t["names"]):
                    hit = t
                    break
            if hit is None:
                hit = {"team": team, "names": Counter(), "seasons": set(), "rows": []}
                tenures.append(hit)
                open_t.append(hit)
            hit["names"][coach] += 1
            hit["seasons"].add(season)
            hit["rows"].append(i)
            row_tenure[i] = len(tenures) - 1 if hit is tenures[-1] else tenures.index(hit)
            open_t = [t for t in open_t if season - max(t["seasons"]) <= 1]

    # ---- 2. careers: union tenures with matching names and no time overlap ----
    parent = list(range(len(tenures)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    seasons_of = {i: set(t["seasons"]) for i, t in enumerate(tenures)}
    names_of = {i: Counter(t["names"]) for i, t in enumerate(tenures)}
    keys = defaultdict(list)                    # last name -> tenures
    for i, t in enumerate(tenures):
        for n in t["names"]:
            keys[parts(n)[1]].append(i)
    review = []
    order = sorted(range(len(tenures)), key=lambda i: min(tenures[i]["seasons"]))
    for i in order:
        for n in list(tenures[i]["names"]):
            for j in keys.get(parts(n)[1], []):
                a, b = find(i), find(j)
                if a == b:
                    continue
                if not any(compatible(x, y) for x in names_of[a] for y in names_of[b]):
                    continue
                # chains through initials ("Bear Bryant" ~ "B.F. Bryant" ~ "Boston Bryant") must not
                # join two different full first names
                fa = {f for x in names_of[a] for f in parts(x)[0] if len(f) > 1}
                fb = {f for x in names_of[b] for f in parts(x)[0] if len(f) > 1}
                if fa and fb and not (fa & fb):
                    continue
                # a career can't stretch over a 20-year break or past 60 years
                sa, sb = seasons_of[a], seasons_of[b]
                gap = max(min(sb) - max(sa), min(sa) - max(sb))
                if gap > 20 or max(max(sa), max(sb)) - min(min(sa), min(sb)) > 60:
                    continue
                overlap = len(seasons_of[a] & seasons_of[b])
                if overlap > 1:
                    review.append(["kept apart (same name, overlapping seasons)",
                                   " / ".join(sorted(names_of[a])[:2]), " / ".join(sorted(names_of[b])[:2]),
                                   f"{min(seasons_of[a])}-{max(seasons_of[a])}", f"{min(seasons_of[b])}-{max(seasons_of[b])}"])
                    continue
                parent[b] = a
                seasons_of[a] |= seasons_of[b]
                names_of[a] += names_of[b]

    groups = defaultdict(list)
    for i in range(len(tenures)):
        groups[find(i)].append(i)

    coaches, ids = [], {}
    for cid, (root, members) in enumerate(sorted(groups.items(), key=lambda g: min(seasons_of[g[0]])), 1):
        names = Counter()
        teams = []
        for m in sorted(members, key=lambda m: min(tenures[m]["seasons"])):
            names += tenures[m]["names"]
            teams.append(f"{tenures[m]['team']} {min(tenures[m]['seasons'])}-{max(tenures[m]['seasons'])}")
            for r in tenures[m]["rows"]:
                ids[r] = cid
        # display name: the plainest common form (no quotes/initials), else most used
        plain = [n for n in names if '"' not in n and not re.search(r"\b[A-Z]\.", n)]
        disp = max(plain or names, key=lambda n: (names[n], -len(n)))
        ss = seasons_of[root]
        coaches.append([cid, disp, " | ".join(sorted(names)), "; ".join(teams), min(ss), max(ss), len(ss)])
        if len(names) > 1 and len({parts(n)[1] for n in names}) > 1:
            review.append(["merged spelling variants", disp, " | ".join(sorted(names)), "", ""])

    with open(os.path.join(FX, "college_coaches.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["Coach_ID", "Coach_Name", "Name_Variants", "Teams", "First", "Last", "Seasons"])
        w.writerows(coaches)
    with open(os.path.join(FX, "college_coach_seasons_ids.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["Team_Name", "Season", "Coach", "Role", "Source", "Agreement", "Coach_ID"])
        for i, r in enumerate(rows):
            w.writerow([r["Team_Name"], r["Season"], r["Coach"], r["Role"], r["Source"], r["Agreement"], ids[i]])
        # seasons with no head coach (early teams run by captains): kept, no Coach_ID
        for r in csv.DictReader(open(os.path.join(FX, "college_coach_seasons.csv"), encoding="utf-8")):
            if r["Role"] == "No coach":
                w.writerow([r["Team_Name"], r["Season"], r["Coach"], r["Role"], r["Source"], r["Agreement"], ""])
    with open(os.path.join(FX, "coach_id_review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["What", "Name_1", "Name_2", "Span_1", "Span_2"])
        seen = set()
        for r in review:
            if tuple(r) not in seen:
                seen.add(tuple(r)); w.writerow(r)
    review = [list(x) for x in {tuple(r) for r in review}]

    print(f"coach-season rows: {len(rows):,}  tenures: {len(tenures):,}  coaches (IDs): {len(coaches):,}")
    print(f"multi-school careers: {sum(1 for c in coaches if c[3].count(';') >= 1):,}")
    print(f"same-name coaches kept apart: {sum(1 for r in review if r[0].startswith('kept')):,}")
    for name in ["Todd Knight", "Bear Bryant", "Nick Saban", "Amos Alonzo Stagg", "Pop Warner", "John Gagliardi",
                 "Lou Holtz", "Dennis McCulloch", "Urban Meyer"]:
        hits = [c for c in coaches if name.split()[-1].lower() in c[1].lower() and name.split()[0].lower()[:3] in (c[1] + c[2]).lower()]
        for c in hits[:3]:
            print(f"   {c[0]:6d} {c[1]:28s} {c[4]}-{c[5]} {c[6]:3d} seasons | {c[3][:110]}")


if __name__ == "__main__":
    main()
