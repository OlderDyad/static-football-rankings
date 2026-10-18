"""
fetch_current_coaches.py  -- run on Windows (needs internet; changes nothing in SQL)

Downloads Wikipedia's "List of current ... football coaches" pages for all five
college levels and writes one table:

    name_fixes/current_coaches_raw.csv
    Level, Team_Wiki, Conference, Head_Coach, First_Season, School_W, School_L, Fetched_At

Re-run once a year after the coaching carousel (Jan-Feb), then run
build_current_coach_fill.py.

Usage:  python fetch_current_coaches.py
Needs:  pip install requests pandas lxml
"""
import csv, os, re, sys
from datetime import datetime
from io import StringIO

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "name_fixes", "current_coaches_raw.csv")
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "McKnightFootballRankings/1.0 (personal research)"}
PAGES = {
    "FBS":   "List of current NCAA Division I FBS football coaches",
    "FCS":   "List of current NCAA Division I FCS football coaches",
    "D-II":  "List of current NCAA Division II football coaches",
    "D-III": "List of current NCAA Division III football coaches",
    "NAIA":  "List of current NAIA football coaches",
}


def flat(col):
    if isinstance(col, tuple):
        parts = [str(c) for c in col if c and not str(c).startswith("Unnamed")]
        # keep order, drop repeats ("Team", "Team")
        seen = []
        for p in parts:
            if p not in seen:
                seen.append(p)
        return " | ".join(seen)
    return str(col)


def pick(cols, *keys, avoid=()):
    for c in cols:
        lc = c.lower()
        if all(k in lc for k in keys) and not any(a in lc for a in avoid):
            return c
    return None


def clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    v = re.sub(r"\[[^\]]*\]", "", str(v))          # footnote markers [a] [1]
    v = v.replace("\xa0", " ").replace("†", "").replace("*", "")
    return re.sub(r"\s+", " ", v).strip()


def year(v):
    m = re.search(r"(18|19|20)\d\d", clean(v))
    return m.group(0) if m else ""


def main():
    rows = []
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    for level, title in PAGES.items():
        r = requests.get(API, headers=HEADERS, timeout=60, params={
            "action": "parse", "page": title, "prop": "text", "format": "json",
            "formatversion": 2, "redirects": 1})
        r.raise_for_status()
        html = r.json()["parse"]["text"]
        tables = pd.read_html(StringIO(html))
        n_level = 0
        for t in tables:
            t.columns = [flat(c) for c in t.columns]
            cols = list(t.columns)
            team_c = pick(cols, "team") or pick(cols, "school") or pick(cols, "program")
            coach_c = pick(cols, "head coach") or pick(cols, "coach", avoid=("coordinator",))
            if not team_c or not coach_c:
                continue
            first_c = pick(cols, "first") or pick(cols, "since") or pick(cols, "hired") or pick(cols, "year")
            conf_c = pick(cols, "conference")
            # record at this school: the first W / L columns (the second pair is usually career)
            w_cols = [c for c in cols if re.search(r"(^|\| )w$", c.lower()) or c.lower() in ("w", "wins")]
            l_cols = [c for c in cols if re.search(r"(^|\| )l$", c.lower()) or c.lower() in ("l", "losses")]
            for _, row in t.iterrows():
                team, coach = clean(row[team_c]), clean(row[coach_c])
                if not team or not coach or team.lower() in ("team", "school") or coach.lower() == "head coach":
                    continue
                rows.append([level, team, clean(row[conf_c]) if conf_c else "", coach,
                             year(row[first_c]) if first_c else "",
                             clean(row[w_cols[0]]) if w_cols else "", clean(row[l_cols[0]]) if l_cols else "",
                             stamp])
                n_level += 1
        print(f"{level:6s} {n_level:4d} programs  ({title})")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Level", "Team_Wiki", "Conference", "Head_Coach", "First_Season", "School_W", "School_L", "Fetched_At"])
        w.writerows(rows)
    print(f"\n{len(rows)} programs written to {OUT}")
    if len(rows) < 600:
        print("WARNING: fewer programs than expected (~700) -- a page layout may have changed.")
        sys.exit(2)


if __name__ == "__main__":
    main()
