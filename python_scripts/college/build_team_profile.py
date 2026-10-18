"""
build_team_profile.py -- one row per college team name as it now stands in
College_Scores_Staging (export + name fixes - duplicates moved out).

Writes name_fixes/college_team_profile.csv:
  Team_Name, Games, First_Season, Last_Season,
  State, State_Source (location table / name suffix / opponents), Latitude, Longitude,
  Latest_Division, Division_Years, Kind (HS / Military / Club / JC / College ...)
Used to load College_Team_Names and by match_hs_names.py.
"""
import csv, os, re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "access_export")
FIX = os.path.join(HERE, "name_fixes")
STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())
FULL = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}


def clean(n):
    return re.sub(r"\s+", " ", (n or "").strip())


def main():
    fix = {}
    for r in csv.DictReader(open(os.path.join(FIX, "college_name_fixes.csv"), encoding="utf-8")):
        fix[(r["Access_ID"], r["Side"])] = r["New_Name"]
    gone = {r["Access_ID"] for r in csv.DictReader(open(os.path.join(FIX, "college_name_fixes.csv"), encoding="utf-8"))
            if r["Is_Duplicate"] == "1"}
    gone |= {r["Access_ID"] for r in csv.DictReader(open(os.path.join(FIX, "college_dup_actions.csv"), encoding="utf-8"))
             if r["Action"] == "MOVE"}
    case = {}
    alias = {r["Alias_Name"].lower(): r["Canonical_Name"]
             for r in csv.DictReader(open(os.path.join(FIX, "college_team_aliases.csv"), encoding="utf-8"))}

    games = []
    for r in csv.DictReader(open(os.path.join(EXP, "access_scores.csv"), encoding="utf-8")):
        if r["ID"] in gone:
            continue
        h = clean(fix.get((r["ID"], "Home"), r["Home"]))
        v = clean(fix.get((r["ID"], "Visitor"), r["Visitor"]))
        games.append((int(float(r["Season"])), h, v))
    teams = Counter(); first = {}; last = {}; opps = defaultdict(Counter)
    for s, h, v in games:
        for me, op in ((h, v), (v, h)):
            teams[me] += 1; first[me] = min(first.get(me, 9999), s); last[me] = max(last.get(me, 0), s)
            opps[me][op] += 1
            case[me.lower()] = me

    def canon(n):
        n = clean(n)
        n = alias.get(n.lower(), n)
        return case.get(n.lower(), n)

    loc = {}
    for r in csv.DictReader(open(os.path.join(EXP, "access_location.csv"), encoding="utf-8")):
        try:
            lat, lon = float(r["Latitude"]), float(r["Longitude"])
        except ValueError:
            continue
        if lon > 0 and lat > 20:
            lon = -lon
        st = (r["State ID"] or "").strip().upper()
        if st not in STATES:
            st = FULL.get((r["State"] or "").strip(), "")
        loc[canon(r["Location"])] = (st, lat, lon)

    state, src, ll = {}, {}, {}
    for t in teams:
        m = re.search(r"\b([A-Z]{2})$", t)
        lead = next((FULL[k] for k in sorted(FULL, key=len, reverse=True)
                     if t == k or t.startswith(k + " ")), None)
        if m and m.group(1) in STATES:
            state[t], src[t] = m.group(1), "name suffix"
        elif lead and not re.search(r"\b(Wesleyan|Christian|Lutheran|Baptist|Methodist|Central|Southern|Northern|Eastern|Western)\b", t):
            state[t], src[t] = lead, "state name"
        elif t in loc and loc[t][0]:
            state[t], src[t], ll[t] = loc[t][0], "location table", loc[t][1:]
        if t in loc and t not in ll:
            ll[t] = loc[t][1:]
    for _ in range(2):   # opponents' majority state, two passes so it can spread
        for t in teams:
            if t in state:
                continue
            c = Counter()
            for o, n in opps[t].items():
                if o in state:
                    c[state[o]] += n
            if c:
                st, n = c.most_common(1)[0]
                if n / sum(c.values()) >= 0.5:
                    state[t], src[t] = st, f"opponents ({n}/{sum(c.values())})"

    div = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(EXP, "access_division_alignment.csv"), encoding="utf-8")):
        try:
            y0, y1 = int(r["YearStart"]), int(r["YearEnd"])
        except ValueError:
            continue
        if y0 < 1860:          # 1805 rows are placeholders
            continue
        div[canon(r["School"])].append((y0, y1, clean(r["Division"])))

    COLLEGE_DIVS = {"NCAA", "Small College", "III", "II", "I", "1AA", "1A", "NAIA", "Major College", "College"}

    def kind(t, d):
        tl = t.lower()
        if d in COLLEGE_DIVS or d.startswith("III-"):
            return "College"
        if re.search(r"\b(hs|high school|high|prep|academy|school|seminary|institute)\b", tl) or d == "HS":
            return "HS/Prep" if "academy" not in tl else "Academy"
        if d in ("Military",) or re.search(r"\b(army|navy base|naval|air base|field|camp|fort|cavalry|infantry|marines|pre-flight|coast guard)\b", tl):
            return "Military"
        if d in ("Club",) or re.search(r"\b(ac|a\.c\.|athletic club|alumni|all-stars|ymca)\b", tl):
            return "Club"
        if d in ("JC", "NJCAA") or re.search(r"\b(jc|junior college|cc)\b", tl):
            return "JC"
        if re.search(r"\bfreshmen\b", tl):
            return "Freshmen"
        return "College"

    rows = []
    for t in sorted(teams, key=str.lower):
        d = sorted(div.get(t, []))
        latest = d[-1][2] if d else ""
        rows.append([t, teams[t], first[t], last[t], state.get(t, ""), src.get(t, ""),
                     f"{ll[t][0]:.5f}" if t in ll else "", f"{ll[t][1]:.5f}" if t in ll else "",
                     latest, "; ".join(f"{a}-{b} {x}" for a, b, x in d), kind(t, latest)])
    with open(os.path.join(FIX, "college_team_profile.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Team_Name", "Games", "First_Season", "Last_Season", "State", "State_Source",
                    "Latitude", "Longitude", "Latest_Division", "Division_Years", "Kind"])
        w.writerows(rows)
    print("teams:", len(rows))
    print("with state:", sum(1 for r in rows if r[4]), Counter(r[5].split(" (")[0] for r in rows))
    print("with division:", sum(1 for r in rows if r[8]))
    print("kind:", Counter(r[10] for r in rows))
    print("active 2020+ without division:", [r[0] for r in rows if r[3] >= 2020 and not r[8]][:30])


if __name__ == "__main__":
    main()
