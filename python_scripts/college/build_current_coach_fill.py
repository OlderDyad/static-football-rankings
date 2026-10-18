"""
build_current_coach_fill.py -- turn name_fixes/current_coaches_raw.csv (Wikipedia
current-coach lists) into coach-season rows for the seasons after the Access data.

Team matching: candidate college names from the Wikipedia name (mascot dropped);
when several fit (two Lincolns, two Wayne States...), the candidate that played the
most 2024-2026 games against the other teams of the same Wikipedia conference wins.

Outputs (name_fixes/):
  current_coach_match_review.csv   one row per Wikipedia program (check / fix Your_Team_Name)
  college_coach_seasons_current.csv coach-season rows to load
Fill rules per program (coach C, first season F):
  * seasons max(F, last Access season + 1) .. 2026 -> C   (Source = Wikipedia current)
  * Access coach in the last Access season continues up to F-1 -> marked 'assumed', to be
    confirmed from the carousel pages
  * F <= last Access season but Access has another coach then -> listed as a conflict
"""
import csv, os, re
from collections import defaultdict, Counter
from college_names import norm

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "name_fixes")
CURRENT = 2026

# Wikipedia program name (start of the "Team" cell, before the mascot) -> Wolfe name.
# None = program not in the college scores yet (new / not covered by Wolfe).
WIKI_MAP = {
    "UAB": "Alabama-Birmingham", "UTSA": "Texas-San Antonio",
    "NC State": "North Carolina St", "BYU": "Brigham Young", "UCF": "Central Florida",
    "USC": "Southern Cal", "UConn": "Connecticut", "Ole Miss": "Mississippi",
    "Cal Poly": "Cal Poly SLO", "UT Martin": "Tennessee-Martin",
    "UTRGV": "Texas-Rio Grande Valley", "UT Permain Basin": "Texas-Permian Basin",
    "UT Permian Basin": "Texas-Permian Basin", "Northwest Missouri State": "NW Missouri St",
    "IUP": "Indiana PA", "CSU Pueblo": "Colorado St-Pueblo", "UVA Wise": "Virginia-Wise",
    "Minnesota State": "Minn St-Mankato", "Minnesota State–Moorhead": "Minn St-Moorhead",
    "New England (ME)": "U of New England", "New England (NH)": "New England Coll", "Mount St. Joseph": "Mt St Joseph",
    "Fairleigh Dickinson–Florham": "FDU-Florham", "TCNJ": "New Jersey", "OUAZ": "Ottawa AZ", 
    "Northwestern Oklahoma State": "NW Oklahoma St", "Oklahoma Panhandle State": "OK Panhandle St",
    "Texas A&M–Kingsville": "TAMU-Kingsville", "South Dakota Mines": "South Dakota Tech",
    "College of Idaho": "Coll of Idaho", "Washington & Jefferson": "Wash & Jeff", "Washington (St. Louis)": "Washington MO",
    "West Virginia Wesleyan": "WV Wesleyan", "Concordia (NE)": "Concordia NE",
    # single generic words: matched on the full Wikipedia name only
    "Eastern Eagles": "Eastern U.", "Southern Jaguars": "Southern U.", "Penn Quakers": "Pennsylvania",
    "Louisiana Ragin' Cajuns": "Louisiana-Lafayette", "Point Skyhawks": "Point U.", "Midland Warriors": "Midland U.",
    "Warner Royals": "Warner U.", "Charlotte 49ers": "UNC-Charlotte", "Wheeling Cardinals": "Wheeling U.",
    "UMass Minutemen": "Massachusetts", "Maritime Privateers": "SUNY-Maritime",
    "Miami Hurricanes": "Miami FL", "Miami RedHawks": "Miami OH", "California Vulcans": "California PA",
    "Anderson Trojans": "Anderson SC", "Anderson Ravens": "Anderson IN", "Union Garnet Chargers": "Union NY",
    "Union Commonwealth": "Union KY", "Concordia Golden Bears": "Concordia-St Paul",
    "Massachusetts Maritime": "Mass Maritime", "UMass Dartmouth": "UMass-Dartmouth",
    "Texas State": "Texas St-San Marcos", "Bridgewater State": "Bridgewater St MA",
    "Notre Dame Fighting Irish": "Notre Dame", "Ohio Bobcats": "Ohio",
    "Shawnee State": None, "Bismarck State": None, "Texas A&M–Texarkana": None,
}
for _u in ["Eau Claire", "La Crosse", "Oshkosh", "Platteville", "River Falls", "Stevens Point", "Stout", "Whitewater"]:
    WIKI_MAP["Wisconsin–" + _u] = "UW-" + _u
# words that are part of a school name, never a mascot: stop dropping words here
KEEP = {"state", "st.", "tech", "a&m", "wesleyan", "christian", "baptist", "lutheran", "mines", "panhandle",
        "college", "university", "of", "methodist", "southern", "northern", "eastern", "western", "central"}


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ").strip())


def main():
    teams = {r["Team_Name"]: r for r in csv.DictReader(open(os.path.join(FX, "college_team_names.csv"), encoding="utf-8"))}
    alias = {r["Alias_Name"]: r["Canonical_Name"] for r in csv.DictReader(open(os.path.join(FX, "college_team_aliases.csv"), encoding="utf-8"))}
    recent = {t for t, r in teams.items() if int(r["Last_Season"] or 0) >= 2022}
    by_norm = defaultdict(set)
    for t in recent:
        by_norm[norm(t)].add(t)
    for a, c in alias.items():
        if c in recent:
            by_norm[norm(a)].add(c)

    # recent games (export + name fixes, duplicates removed) for the conference check
    fix, gone = {}, set()
    for r in csv.DictReader(open(os.path.join(FX, "college_name_fixes.csv"), encoding="utf-8")):
        fix[(r["Access_ID"], r["Side"])] = r["New_Name"]
        if r["Is_Duplicate"] == "1":
            gone.add(r["Access_ID"])
    gone |= {r["Access_ID"] for r in csv.DictReader(open(os.path.join(FX, "college_dup_actions.csv"), encoding="utf-8")) if r["Action"] == "MOVE"}
    opp = defaultdict(Counter)
    for r in csv.DictReader(open(os.path.join(HERE, "access_export", "access_scores.csv"), encoding="utf-8")):
        if r["ID"] in gone or int(float(r["Season"])) < 2023:
            continue
        h = clean(fix.get((r["ID"], "Home"), r["Home"])); v = clean(fix.get((r["ID"], "Visitor"), r["Visitor"]))
        h = {"Sep-25 TCU": "TCU"}.get(h, h); v = {"Sep-25 TCU": "TCU"}.get(v, v)
        opp[h][v] += 1; opp[v][h] += 1

    raw = list(csv.DictReader(open(os.path.join(FX, "current_coaches_raw.csv"), encoding="utf-8")))

    def candidates(wiki):
        w0 = clean(wiki)
        for key in sorted(WIKI_MAP, key=len, reverse=True):
            if w0 == key or w0.startswith(key + " "):
                t = WIKI_MAP[key]
                return ([t] if t in teams else []), key
        words = w0.replace("–", "-").split()
        for k in range(len(words), 0, -1):            # longest prefix first: drop mascot words
            if any(x.lower() in KEEP for x in words[k:]):
                break                                 # never drop "State", "Tech", ...
            n = norm(" ".join(words[:k]))
            found = set(by_norm.get(n, set()))
            if found:   # also state-coded twins ("Miami" + "Miami FL"/"Miami OH"); conference games decide
                for st in "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split():
                    found |= by_norm.get(n + st.lower(), set())
                return sorted(found), " ".join(words[:k])
            for suf in ["st"] + [s.lower() for s in "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()]:
                found |= by_norm.get(n + suf, set())
            if found:
                return sorted(found), " ".join(words[:k])
        return [], ""

    # pass 1: unambiguous matches per conference
    first = {}
    for i, r in enumerate(raw):
        c, core = candidates(r["Team_Wiki"])
        first[i] = (c, core)
    conf_members = defaultdict(set)
    for i, r in enumerate(raw):
        if len(first[i][0]) == 1:
            conf_members[(r["Level"], r["Conference"])].add(first[i][0][0])

    review, chosen = [], {}
    for i, r in enumerate(raw):
        c, core = first[i]
        mates = conf_members[(r["Level"], r["Conference"])]
        scored = sorted(((sum(opp[t][m] for m in mates if m != t), t) for t in c), reverse=True)
        if not c:
            pick, conf = "", "no match"
        elif len(c) == 1:
            pick = c[0]
            conf = "high" if scored[0][0] >= 2 or not mates else "check (few conference games)"
        else:
            pick = scored[0][1]
            conf = "high" if scored[0][0] >= 3 and scored[0][0] >= 2 * max(1, scored[1][0]) else "check (ambiguous)"
        chosen[i] = pick
        review.append([r["Level"], r["Conference"], r["Team_Wiki"], r["Head_Coach"], r["First_Season"],
                       pick, conf, " | ".join(f"{t} ({s} conf games)" for s, t in scored[:4]), ""])

    # Access coach seasons
    acc = defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(FX, "college_coach_seasons_access.csv"), encoding="utf-8")):
        acc[r["Team_Name"]].setdefault(int(r["Season"]), []).append(r["Coach"])

    fill, conflicts, gaps = [], [], []
    for i, r in enumerate(raw):
        t = chosen[i]
        if not t:
            continue
        coach, F = clean(r["Head_Coach"]), int(r["First_Season"] or CURRENT)
        seasons = acc.get(t, {})
        last = max(seasons) if seasons else None
        start = max(F, (last + 1) if last else F)
        for s in range(start, CURRENT + 1):
            fill.append([t, s, coach, "Wikipedia current", "listed", r["Level"]])
        if last is not None and F > last + 1:
            gaps.append([t, r["Level"], last, F, F - last - 1, "/".join(seasons[last]), coach])
        elif last is None and F > 1869:
            gaps.append([t, r["Level"], "", F, "", "", coach])
        if last is not None and F <= last and coach.split()[-1].lower() not in " ".join(seasons.get(F, [])).lower():
            conflicts.append([t, coach, F, "; ".join(f"{y}: {'/'.join(seasons[y])}" for y in sorted(seasons) if y >= F - 1)[:250]])

    with open(os.path.join(FX, "current_coach_match_review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Level", "Conference", "Team_Wiki", "Head_Coach", "First_Season", "Matched_Team",
                    "Confidence", "Candidates", "Your_Team_Name"])
        w.writerows(review)
    with open(os.path.join(FX, "college_coach_seasons_current.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Team_Name", "Season", "Coach", "Source", "Status", "Level"])
        w.writerows(sorted(fill))
    with open(os.path.join(FX, "current_coach_conflicts.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Team_Name", "Wiki_Coach", "Wiki_First_Season", "Access_Coaches_From_Then"])
        w.writerows(conflicts)

    with open(os.path.join(FX, "coach_history_gaps.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Team_Name", "Level", "Last_Access_Season", "Current_Coach_First_Season", "Missing_Seasons",
                    "Last_Access_Coach", "Current_Coach"])
        w.writerows(gaps)
    print("teams with a gap before the current coach:", len(gaps),
          " missing seasons (teams with Access data):", sum(g[4] for g in gaps if g[4] != ""))
    print("programs:", len(raw), Counter(x[6].split(" (")[0] for x in review))
    print("matched to a team already in Access coach data:", sum(1 for i in chosen if chosen[i] in acc))
    print("fill rows:", len(fill), Counter(f[4] for f in fill))
    print("conflicts:", len(conflicts))
    dupe = Counter(chosen[i] for i in chosen if chosen[i])
    print("teams matched twice:", [t for t, n in dupe.items() if n > 1])


if __name__ == "__main__":
    main()
