"""
build_coach_seasons.py -- expand the Access coach tenures (College_Coach_Tenures /
access_export/access_coaches.csv) into one row per team per season per coach.

Output: name_fixes/college_coach_seasons_access.csv
  Team_Name, Season, Coach, Coaches_In_Season, Source, Tenure_Access_ID, School_As_Listed, Match
and name_fixes/coach_school_unmatched.csv for schools that could not be matched.

Seasons with more than one coach (mid-season change, co-coaches) keep one row per
coach with Coaches_In_Season > 1; their split records come from the scores later.
"""
import csv, os, re
from collections import defaultdict, Counter
from college_names import Matcher

HERE = os.path.dirname(os.path.abspath(__file__))


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ").strip())


def main():
    M = Matcher()
    rows = list(csv.DictReader(open(os.path.join(HERE, "access_export", "access_coaches.csv"), encoding="utf-8")))
    # The last tenure of most schools was carried to 2023 in Access although the data
    # was only maintained until ~2005-2009 (e.g. Bob Stoops, Oklahoma 1999-"2023", Years = 7).
    # For those, keep only the seasons the tenure's Years count supports.
    last_end = {}
    for r in rows:
        k = clean(r["School"])
        last_end[k] = max(last_end.get(k, 0), int(r["Year_ End"]) if r["Year_ End"].isdigit() else 0)
    truncated = 0
    out, unmatched, how_count = [], Counter(), Counter()
    for r in rows:
        school, coach = clean(r["School"]), clean(r["Coach"])
        try:
            y0, y1 = int(r["Year_ Start"]), int(r["Year_ End"])
        except ValueError:
            unmatched[(school, "bad years")] += 1
            continue
        # Some tenures list the year the coach LEFT as Year_End (Years = span - 1):
        # then the last listed season belongs to the successor.
        try:
            yrs = int(float(r["Years"]))
        except ValueError:
            yrs = None
        if yrs is not None and y1 > y0 and yrs == (y1 - y0 + 1) - 1:
            y1 -= 1
        if y1 == 2023 and last_end.get(school) == 2023:
            if yrs and yrs > 0 and y0 + yrs - 1 < y1:
                y1 = y0 + yrs - 1
            elif not yrs:
                y1 = min(y1, 2005)          # no Years count: Access data entry era
            truncated += 1
        if coach in ("", "0", "Unknown", "unknown", "?"):
            coach = "Unknown"
        team, how, alt = M.match(school, y0)
        how_count[how] += 1
        if not team:
            unmatched[(school, how)] += 1
            continue
        for season in range(y0, y1 + 1):
            out.append([team, season, coach, r["ID"], school, how + (" (alt: " + "; ".join(alt) + ")" if alt else "")])

    per = Counter((o[0], o[1]) for o in out)
    dup = Counter((o[0], o[1], o[2]) for o in out)
    final, seen = [], set()
    for o in out:
        key = (o[0], o[1], o[2])
        if key in seen:          # same coach listed twice for a season (overlapping tenure rows)
            continue
        seen.add(key)
        final.append([o[0], o[1], o[2], per[(o[0], o[1])] - (dup[key] - 1), "Access", o[3], o[4], o[5]])

    fx = os.path.join(HERE, "name_fixes")
    with open(os.path.join(fx, "college_coach_seasons_access.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Team_Name", "Season", "Coach", "Coaches_In_Season", "Source", "Tenure_Access_ID",
                    "School_As_Listed", "Match"])
        w.writerows(sorted(final, key=lambda x: (x[0], x[1], x[2])))
    with open(os.path.join(fx, "coach_school_unmatched.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["School", "Reason", "Tenure_Rows", "Your_Team_Name"])
        for (s, why), n in unmatched.most_common():
            w.writerow([s, why, n, ""])

    teams = {o[0] for o in final}
    multi = Counter(o[3] > 1 for o in final)
    print(f"tenures: {len(rows):,}  match: {dict(how_count)}")
    print(f"open-ended last tenures cut back to their Years count: {truncated}")
    print(f"coach-season rows: {len(final):,}  teams: {len(teams)}  seasons {min(o[1] for o in final)}-{max(o[1] for o in final)}")
    print(f"rows in seasons with 2+ coaches: {multi[True]:,}")
    print(f"unmatched schools: {len(unmatched)} ({sum(unmatched.values())} tenure rows)")
    for (s, why), n in unmatched.most_common(15):
        print("   ", s, why, n)


if __name__ == "__main__":
    main()
