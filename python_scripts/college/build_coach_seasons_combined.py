"""
build_coach_seasons_combined.py -- one coach table from three sources.

Sources (name_fixes/):
  college_coach_seasons_access.csv   Access tenures, trustworthy seasons only
  program_coach_history_raw.csv      Wikipedia program head-coach histories
  current_coach_match_review.csv /   Wikipedia current-coach lists (coach + first season)
    college_coach_seasons_current.csv

A program's Wikipedia table is TRUSTED only if it checks out: it names the current
coach near his first season, or agrees with Access on >= 60% of shared seasons.
(Some pages yielded the wrong table -- e.g. notable alumni who became coaches.)

Priority per team-season: Access (where it exists) > trusted Wikipedia history >
current-coach list. Disagreements between sources -> coach_source_conflicts.csv.

Outputs:
  name_fixes/college_coach_seasons.csv     Team_Name, Season, Coach, Role, Source, Agreement
  name_fixes/coach_wiki_table_check.csv    per program: trusted or not, and why
  name_fixes/coach_source_conflicts.csv
  name_fixes/coach_coverage.csv            per level / era: team-seasons with games vs with a coach
"""
import csv, os, re
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "name_fixes")
CURRENT = 2026
SKIP = re.compile(r"^(unknown|no (teams?|programs?|coach(es)?|football)|none|vacant|n/?a|totals?|program|season|tbd|did not|\d+)\b", re.I)


def clean_coach(c):
    c = re.sub(r"\[[^\]]*\]", "", c or "")
    role = "Interim" if re.search(r"\binterim\b|\bacting\b", c, re.I) else "Head"
    c = re.sub(r"\((interim|acting|\d+)\)", "", c, flags=re.I)
    c = re.sub(r"[†‡*#^§¶]", "", c)
    c = re.sub(r"\s+", " ", c).strip(" ,;")
    return c, role


def last_name(c):
    c = re.sub(r"\b(jr|sr|ii|iii|iv)\.?$", "", c.lower()).strip(" ,.")
    parts = re.findall(r"[a-z'\-]+", c)
    return parts[-1] if parts else ""


def same_person(a, b):
    """last names equal or nearly so (Biesoit/Biesiot, Kelly/Kelley, Elliot/Elliott)"""
    from difflib import SequenceMatcher
    a, b = last_name(a), last_name(b)
    return bool(a) and bool(b) and (a == b or SequenceMatcher(None, a, b).ratio() >= 0.8)


def plausible(c):
    return bool(c) and not SKIP.match(c) and len(c) <= 40 and not re.search(r"\d", c) \
        and not re.search(r"\b(conference|football|university|college)\b", c, re.I)


def main():
    acc = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(os.path.join(FX, "college_coach_seasons_access.csv"), encoding="utf-8")):
        if r["Coach"] != "Unknown":
            acc[r["Team_Name"]][int(r["Season"])].append(r["Coach"])

    cur = {}
    for r in csv.DictReader(open(os.path.join(FX, "current_coach_match_review.csv"), encoding="utf-8")):
        t = (r["Your_Team_Name"] or r["Matched_Team"]).strip()
        if t:
            cur[t] = (r["Head_Coach"], int(r["First_Season"] or CURRENT), r["Level"])

    wiki = defaultdict(lambda: defaultdict(list))
    level_of = {t: v[2] for t, v in cur.items()}
    wiki_name = {}
    for r in csv.DictReader(open(os.path.join(FX, "current_coach_match_review.csv"), encoding="utf-8")):
        t = (r["Your_Team_Name"] or r["Matched_Team"]).strip()
        if t:
            wiki_name[t] = r["Team_Wiki"]

    def article_is_teams(article, team):
        """The search fallback sometimes returned a page about another program, a coach,
        or a 'List of current ... coaches' page. Keep only articles named for this program."""
        a = article.lower()
        if a.startswith("list of current") or "(american football coach)" in a:
            return False
        words = [w for w in re.findall(r"[a-z]+", (wiki_name.get(team) or team).lower())
                 if w not in ("university", "college", "of", "the", "state", "st")]
        return bool(words) and words[0] in a

    rejected_articles = Counter()
    for r in csv.DictReader(open(os.path.join(FX, "program_coach_history_raw.csv"), encoding="utf-8")):
        if not article_is_teams(r["Article"], r["Team_Name"]):
            rejected_articles[(r["Team_Name"], r["Article"])] += 1
            continue
        c, role = clean_coach(r["Coach"])
        if not plausible(c):
            continue
        a = int(float(r["Year_Start"]))
        b = int(float(r["Year_End"])) if r["Year_End"] else CURRENT
        if b < a or b - a > 60:
            continue
        for s in range(a, min(b, CURRENT) + 1):
            if (c, role) not in wiki[r["Team_Name"]][s]:
                wiki[r["Team_Name"]][s].append((c, role))

    # ---- trust check per program ----
    trust, checks = {}, []
    for t, seasons in wiki.items():
        reasons = []
        ok_current = False
        if t in cur:
            cc, F, _ = cur[t]
            ln = last_name(cc)
            near = [x for s in range(F - 1, F + 2) for x in seasons.get(s, [])]
            ok_current = any(last_name(x[0]) == ln for x in near)
            reasons.append("current coach found" if ok_current else "current coach NOT found")
        shared = [s for s in seasons if s in acc[t]]
        agree = sum(1 for s in shared if any(same_person(x[0], y) for x in seasons[s] for y in acc[t][s]))
        rate = agree / len(shared) if shared else None
        if shared:
            reasons.append(f"Access agreement {agree}/{len(shared)}")
        # a real coach history covers its span densely with one coach per season;
        # a wrong table (e.g. alumni who became coaches elsewhere) is sparse or crowded
        span = max(seasons) - min(seasons) + 1
        density = len(seasons) / span
        crowded = sum(1 for v in seasons.values() if len(v) > 1) / len(seasons)
        shape_ok = len(seasons) >= 8 and density >= 0.6 and crowded <= 0.2
        reasons.append(f"density {density:.0%}, multi-coach seasons {crowded:.0%}")
        if rate is not None and len(shared) >= 5:
            ok = rate >= 0.6 or (ok_current and rate >= 0.4)
        else:
            ok = ok_current or shape_ok
        trust[t] = ok
        checks.append([t, level_of.get(t, ""), "TRUSTED" if ok else "rejected", min(seasons), max(seasons),
                       len(seasons), "; ".join(reasons)])

    # ---- combine ----
    out, conflicts = [], []
    teams = set(acc) | {t for t in wiki if trust[t]} | set(cur)
    for t in sorted(teams):
        w = wiki[t] if trust.get(t) else {}
        seasons = set(acc[t]) | set(w)
        if t in cur:
            seasons |= set(range(cur[t][1], CURRENT + 1))
        for s in sorted(seasons):
            a_list = acc[t].get(s, [])
            w_list = w.get(s, [])
            if a_list and w_list and not any(same_person(x, y[0]) for x in a_list for y in w_list):
                # sources disagree: Access coach tenures were often stretched (data kept
                # only to ~2005-09); a verified Wikipedia history wins, Access kept for review
                conflicts.append([t, s, " / ".join(a_list), " / ".join(x[0] for x in w_list), ""])
                for c, role in w_list:
                    out.append([t, s, c, role, "Wikipedia history", "DISAGREE (Access: " + " / ".join(a_list)[:60] + ")"])
            elif a_list:
                agree = "agree" if w_list else "n/a"
                for c in a_list:
                    no = c.strip().lower() in ("no coach", "none")
                    out.append([t, s, "No Coach" if no else c, "No coach" if no else "Head", "Access", agree])
            elif w_list:
                for c, role in w_list:
                    out.append([t, s, c, role, "Wikipedia history", "n/a"])
            elif t in cur and s >= cur[t][1]:
                out.append([t, s, cur[t][0], "Head", "Wikipedia current", "n/a"])

    with open(os.path.join(FX, "college_coach_seasons.csv"), "w", newline="", encoding="utf-8") as fh:
        wtr = csv.writer(fh); wtr.writerow(["Team_Name", "Season", "Coach", "Role", "Source", "Agreement"]); wtr.writerows(out)
    with open(os.path.join(FX, "coach_wiki_table_check.csv"), "w", newline="", encoding="utf-8") as fh:
        wtr = csv.writer(fh); wtr.writerow(["Team_Name", "Level", "Status", "First", "Last", "Seasons", "Why"]); wtr.writerows(sorted(checks))
    with open(os.path.join(FX, "coach_source_conflicts.csv"), "w", newline="", encoding="utf-8") as fh:
        wtr = csv.writer(fh); wtr.writerow(["Team_Name", "Season", "Access_Coach", "Wikipedia_Coach", "Your_Coach"]); wtr.writerows(conflicts)

    # ---- coverage vs games (team-seasons that actually played) ----
    played = defaultdict(set)
    fix, gone = {}, set()
    for r in csv.DictReader(open(os.path.join(FX, "college_name_fixes.csv"), encoding="utf-8")):
        fix[(r["Access_ID"], r["Side"])] = r["New_Name"]
        if r["Is_Duplicate"] == "1":
            gone.add(r["Access_ID"])
    gone |= {r["Access_ID"] for r in csv.DictReader(open(os.path.join(FX, "college_dup_actions.csv"), encoding="utf-8")) if r["Action"] == "MOVE"}
    for r in csv.DictReader(open(os.path.join(HERE, "access_export", "access_scores.csv"), encoding="utf-8")):
        if r["ID"] in gone:
            continue
        s = int(float(r["Season"]))
        for side in ("Home", "Visitor"):
            played[re.sub(r"\s+", " ", fix.get((r["ID"], side), r[side]).strip())].add(s)
    covered = {(o[0], o[1]) for o in out}
    cov = defaultdict(lambda: [0, 0])
    for t in cur:                       # current programs only (the ones coach ratings are about)
        lvl = cur[t][2]
        for s in played.get(t, ()):
            era = "2010-26" if s >= 2010 else ("1980-2009" if s >= 1980 else ("1946-79" if s >= 1946 else "pre-1946"))
            cov[(lvl, era)][0] += 1
            cov[(lvl, era)][1] += (t, s) in covered
    with open(os.path.join(FX, "coach_coverage.csv"), "w", newline="", encoding="utf-8") as fh:
        wtr = csv.writer(fh); wtr.writerow(["Level", "Era", "Team_Seasons_Played", "With_Coach", "Pct"])
        for (lvl, era), (n, k) in sorted(cov.items()):
            wtr.writerow([lvl, era, n, k, f"{k / n:.0%}" if n else ""])

    print("wikipedia rows dropped (article not about this program):", sum(rejected_articles.values()),
          "from", len(rejected_articles), "team/article pairs")
    print("coach-season rows:", len(out), Counter(o[4] for o in out))
    print("wikipedia tables:", Counter(c[2] for c in checks))
    print("Access vs Wikipedia:", Counter(o[5][:8] for o in out if o[4] == "Access" or o[5].startswith("DISAGREE")))
    print("conflicts (team-seasons):", len(conflicts))
    print("coverage of current programs (team-seasons with games):")
    for (lvl, era), (n, k) in sorted(cov.items(), key=lambda x: (["FBS", "FCS", "D-II", "D-III", "NAIA"].index(x[0][0]), x[0][1])):
        print(f"   {lvl:6s} {era:10s} {k:6,}/{n:6,}  {k / n:.0%}")


if __name__ == "__main__":
    main()
