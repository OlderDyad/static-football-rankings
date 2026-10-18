"""
match_hs_names.py  -- run on Windows (reads SQL Server; changes nothing)

Finds the HS_Team_Names record that is the same team as each college team name,
e.g.  Washington   -> University of Washington (WA)
      Notre Dame   -> Notre Dame University (IN)
      Beckley HS   -> Beckley (WV)

Input : name_fixes/college_team_profile.csv  (from build_team_profile.py)
        dbo.HS_Team_Names, game counts from dbo.HS_Scores
Output: college_hs_match_review.csv  (review; fill Your_HS_Team_ID to override,
        or put 0 to say "no HS match")

Usage:  python match_hs_names.py
"""
import csv, math, os, re, sys
from collections import defaultdict

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))

COLLEGE_WORDS = r"\b(university|univ|college|state|st|institute|inst|normal|teachers|polytechnic|poly|tech|a&m|seminary|academy|military|school of mines|mines)\b"
HS_WORDS = r"\b(hs|high school|high|h\.s\.)\b"
STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())


def norm(s, drop_college=False, drop_hs=False):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bstate\b", "st", s)
    s = re.sub(r"\b(the|of|at)\b", " ", s)
    if drop_hs:
        s = re.sub(HS_WORDS, " ", s)
    if drop_college:
        s = re.sub(r"\b(university|univ|college|institute|inst)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def split_hs(name):
    m = re.match(r"^(.*?)\s*\(([A-Za-z]{2,3})\)\s*$", name)
    return (m.group(1).strip(), m.group(2).upper()) if m else (name.strip(), "")


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def main():
    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    print("Reading HS_Team_Names ...")
    hs = cur.execute("SELECT ID, Team_Name, City, State, Latitude, Longitude FROM dbo.HS_Team_Names").fetchall()
    print("Counting HS games per team (a minute or two) ...")
    gcount = dict(cur.execute(
        "SELECT Team, COUNT(*) FROM (SELECT Home AS Team FROM dbo.HS_Scores UNION ALL "
        "SELECT Visitor FROM dbo.HS_Scores) x GROUP BY Team").fetchall())
    conn.close()

    # Team names used in HS_Scores but missing from HS_Team_Names (e.g. college-vs-college
    # games from newspaper OCR: "University of Illinois (IL)") are candidates too, with no ID.
    class Row:
        pass
    known = {r.Team_Name for r in hs}
    extra = []
    for name in gcount:
        if name and name not in known:
            x = Row(); x.ID = ""; x.Team_Name = name; x.City = None
            x.State = None; x.Latitude = None; x.Longitude = None
            extra.append(x)
    print(f"{len(extra):,} team names appear in HS_Scores but not in HS_Team_Names")
    hs = list(hs) + extra

    idx_plain, idx_college = defaultdict(list), defaultdict(list)
    for r in hs:
        base, st = split_hs(r.Team_Name)
        rec = dict(id=r.ID, name=r.Team_Name, base=base, st=(r.State or st or "").upper()[:2],
                   ll=(float(r.Latitude), float(r.Longitude)) if r.Latitude and r.Longitude else None,
                   games=gcount.get(r.Team_Name, 0),
                   collegey=bool(re.search(COLLEGE_WORDS, base.lower())))
        idx_plain[norm(base, drop_hs=True)].append(rec)
        if rec["collegey"]:
            idx_college[norm(base, drop_college=True)].append(rec)
        # HS records are usually "City School (ST)": also index the name without
        # the leading 1-2 city words (state must then agree -- see city_dropped)
        words = base.split()
        city = (r.City or "").strip().lower()
        for k in (1, 2, 3):
            # only drop words that ARE the record's city ("Milledgeville Georgia Military
            # College" with City = Milledgeville) -- never "Northern", "West", "University of"
            if len(words) > k and city and " ".join(words[:k]).lower() == city:
                rest = " ".join(words[k:])
                cd = dict(rec, city_dropped=True)
                idx_plain[norm(rest, drop_hs=True)].append(cd)
                if rec["collegey"]:
                    idx_college[norm(rest, drop_college=True)].append(cd)

    with open(os.path.join(HERE, "hs_college_like_names.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["HS_Team_ID", "Team_Name", "State", "HS_Games"])
        for r in hs:
            base, st = split_hs(r.Team_Name)
            if re.search(COLLEGE_WORDS + r"|\bu\.? of\b|\buniv", base.lower()):
                w.writerow([r.ID, r.Team_Name, r.State, gcount.get(r.Team_Name, 0)])

    out = []
    for t in csv.DictReader(open(os.path.join(HERE, "name_fixes", "college_team_profile.csv"), encoding="utf-8")):
        name, kind, st = t["Team_Name"], t["Kind"], t["State"]
        ll = (float(t["Latitude"]), float(t["Longitude"])) if t["Latitude"] else None
        m = re.search(r"\s+([A-Z]{2})$", name)           # "St Francis PA" -> "St Francis" (real states only;
        core = name[:m.start()] if m and m.group(1) in STATES else name   #  "Bucknell JV" stays)
        cands = {}
        if kind in ("HS/Prep", "Academy"):
            for c in idx_plain.get(norm(core, drop_hs=True), []):
                cands.setdefault(c["name"], (c, "same name (HS)"))
        else:
            for c in idx_college.get(norm(core, drop_college=True), []):
                cands.setdefault(c["name"], (c, "college-style HS record"))
            for c in idx_college.get(norm(core), []):
                cands.setdefault(c["name"], (c, "college-style HS record"))
            # no plain-name fallback: "Sterling" (college) must not match Sterling HS

        scored = []
        for c, why in cands.values():
            if c.get("city_dropped") and not (st and c["st"] == st):
                continue          # city-prefix matches only count in the same state
            if c.get("city_dropped"):
                why += ", city prefix"
            s = 0
            if st and c["st"]:
                s += 3 if st == c["st"] else -5
            d = km(ll, c["ll"]) if ll and c["ll"] else None
            if d is not None:
                s += 2 if d < 60 else (0 if d < 300 else -2)
            s += 2 if why.startswith("college-style") else (1 if why.startswith("same name (HS)") else 0)
            if why.startswith("college-style"):
                cb = c["base"].lower()
                if norm(core) == norm(c["base"]):
                    s += 3                      # exact, e.g. "Colorado College" = "Colorado College (CO)"
                elif re.search(r"\bcollege\b", core.lower()) and "college" not in cb:
                    s -= 3                      # "Texas College" is not Texas University
                elif not re.search(COLLEGE_WORDS, core.lower()):
                    # bare "Mississippi" is the University, not Mississippi College;
                    # bare "Boston" stays ambiguous (Boston College vs Boston University)
                    if re.match(r"^(the )?university of\b", cb) or re.search(r"\buniversity$", cb):
                        s += 2
                    elif re.search(r"\bcollege$", cb):
                        s -= 1
            s += 1 if c["games"] else 0
            scored.append((s, d, c, why))
        scored.sort(key=lambda x: (-x[0], -x[2]["games"]))
        best = scored[0] if scored and scored[0][0] >= 3 else None
        conf = ""
        if best:
            gap = best[0] - (scored[1][0] if len(scored) > 1 else -99)
            conf = "high" if best[0] >= 5 and gap >= 2 else "check"
            # several HS records for the same school (renames, stray spaces): if the
            # runner-up is in the same state and the top has clearly more games, accept
            if conf == "check" and len(scored) > 1 and scored[1][2]["st"] == best[2]["st"] == st \
                    and best[2]["games"] >= 2 * max(1, scored[1][2]["games"]) and best[0] >= 4:
                conf = "high"
        row = [name, kind, st, t["Games"], t["First_Season"], t["Last_Season"],
               (best[2]["id"] or "not in HS_Team_Names") if best else "", best[2]["name"] if best else "", best[2]["games"] if best else "",
               f"{best[1]:.0f}" if best and best[1] is not None else "", best[3] if best else "", conf,
               len(scored), " | ".join(f'{c["id"] or "no-ID"}:{c["name"]} ({c["games"]}g, s{s})' for s, d, c, w in scored[:4]), ""]
        out.append(row)

    path = os.path.join(HERE, "college_hs_match_review.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["College_Team", "Kind", "State", "College_Games", "First", "Last",
                    "Proposed_HS_Team_ID", "Proposed_HS_Team_Name", "HS_Games", "Km", "Basis", "Confidence",
                    "Candidates", "Top_Candidates", "Your_HS_Team_ID"])
        w.writerows(out)
    cc = [r for r in out if r[11] and r[7]]
    print(f"HS records linked to college teams: {len(cc):,} "
          f"({sum(1 for r in cc if r[6] == 'not in HS_Team_Names'):,} exist only as names in HS_Scores)")
    n = len(out)
    hi = sum(1 for r in out if r[11] == "high"); ck = sum(1 for r in out if r[11] == "check")
    print(f"\n{n:,} college teams: {hi:,} high-confidence HS matches, {ck:,} to check, {n - hi - ck:,} no match")
    print(f"Written: {path}")


if __name__ == "__main__":
    main()
