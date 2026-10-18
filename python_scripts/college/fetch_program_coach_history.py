"""
fetch_program_coach_history.py  -- run on Windows (needs internet; changes nothing in SQL)

For every current college program (name_fixes/current_coach_match_review.csv), finds its
Wikipedia head-coach history and writes the raw rows:

    name_fixes/program_coach_history_raw.csv
    Team_Name, Level, Article, Coach, Years_Text, Year_Start, Year_End, Fetched_At

Where it looks, per program:
  1. "List of <Program> head football coaches"   (most FBS/FCS programs)
  2. "<Program> football"                        (coach table in the program article)
  3. Wikipedia search "<Program> football head coaches" as a fallback
Programs with no usable table are listed in program_coach_history_missing.csv.

Takes ~10-20 minutes (one or two pages per program, polite 0.5 s pause).
Resumable: results are written as it goes; a rerun skips programs already done.
Usage:  python fetch_program_coach_history.py --fresh    (start over: all ~770 programs)
        python fetch_program_coach_history.py            (continue an interrupted run)
        python fetch_program_coach_history.py --limit 20 (quick test)
"""
import argparse, csv, os, re, sys, time
from datetime import datetime
from io import StringIO

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "name_fixes")
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "McKnightFootballRankings/1.0 (personal research)"}
S = requests.Session()
S.headers.update(HEADERS)


def api(**params):
    params.update(format="json", formatversion=2)
    for attempt in range(3):
        try:
            r = S.get(API, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 + attempt * 3)
    return {}


def page_html(title):
    j = api(action="parse", page=title, prop="text", redirects=1)
    if "parse" not in j:
        return None, None
    return j["parse"]["title"], j["parse"]["text"]


def clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    v = re.sub(r"\[[^\]]*\]", "", str(v)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", v).strip()


def flat(col):
    if isinstance(col, tuple):
        out = []
        for c in col:
            c = str(c)
            if c and not c.startswith("Unnamed") and c not in out:
                out.append(c)
        return " | ".join(out)
    return str(col)


YEAR = r"(18[6-9]\d|19\d\d|20\d\d)"


def parse_years(text):
    """'1999–2016' -> [(1999, 2016)]; '2017–present' -> [(2017, None)];
    '1906, 1908–1910' -> [(1906, 1906), (1908, 1910)]"""
    t = clean(text).replace("—", "–").replace("-", "–")
    spans = []
    for part in re.split(r"[,;/]| and ", t):
        m = re.search(YEAR + r"(?:\s*–\s*(" + YEAR[1:-1] + r"|present|current|\d\d)\b)?", part, re.I)
        if not m:
            continue
        a = int(m.group(1))
        b = m.group(2)
        if b is None:
            spans.append((a, a))
        elif b.lower() in ("present", "current"):
            spans.append((a, None))
        elif len(b) == 2:
            spans.append((a, int(str(a)[:2] + b)))
        else:
            spans.append((a, int(b)))
    return spans


def coach_rows(html):
    """Rows from tables that have a coach column and a years column."""
    try:
        tables = pd.read_html(StringIO(html))
    except Exception:          # unparseable page (or a missing optional parser): skip it
        return []
    found = []
    for t in tables:
        t.columns = [flat(c) for c in t.columns]
        cols = list(t.columns)
        lc = [c.lower() for c in cols]
        coach_i = next((i for i, c in enumerate(lc) if ("coach" in c or c in ("name", "head coach"))
                        and "coordinator" not in c and "assistant" not in c), None)
        years_i = next((i for i, c in enumerate(lc) if any(k in c for k in ("year", "tenure", "season", "term"))
                        and "seasons" != c.strip()), None)
        if years_i is None:
            years_i = next((i for i, c in enumerate(lc) if "seasons" in c), None)
        if coach_i is None or years_i is None:
            continue
        rows = []
        for _, r in t.iterrows():
            coach, yrs = clean(r.iloc[coach_i]), clean(r.iloc[years_i])
            if not coach or coach.lower() in ("coach", "name", "totals", "total") or not parse_years(yrs):
                continue
            rows.append((coach, yrs))
        if len(rows) >= 2:
            found.append(rows)
    # The head-coach history covers the most distinct seasons. Row count alone picks
    # the wrong table on pages with a long conference-championships list (Year | Coach),
    # which only covers the title years.
    def seasons_covered(rows):
        yrs = set()
        for _, y in rows:
            for a, b in parse_years(y):
                yrs.update(range(a, (b or 2026) + 1))
        return len(yrs)
    return max(found, key=seasons_covered) if found else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--fresh", action="store_true", help="start over (delete earlier results)")
    args = ap.parse_args()

    programs = [r for r in csv.DictReader(open(os.path.join(FX, "current_coach_match_review.csv"), encoding="utf-8"))
                if (r["Your_Team_Name"] or r["Matched_Team"])]
    if args.limit:
        programs = programs[:args.limit]
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    raw_path = os.path.join(FX, "program_coach_history_raw.csv")
    miss_path = os.path.join(FX, "program_coach_history_missing.csv")
    if args.fresh:
        for f in (raw_path, miss_path):
            if os.path.exists(f):
                os.remove(f)
    # resume: skip programs already written by an earlier (interrupted) run
    done = set()
    for f in (raw_path, miss_path):
        if os.path.exists(f):
            done |= {r["Team_Name"] for r in csv.DictReader(open(f, encoding="utf-8"))}
    new_raw = not os.path.exists(raw_path)
    new_miss = not os.path.exists(miss_path)
    fr = open(raw_path, "a", newline="", encoding="utf-8")
    fm = open(miss_path, "a", newline="", encoding="utf-8")
    wr, wm = csv.writer(fr), csv.writer(fm)
    if new_raw:
        wr.writerow(["Team_Name", "Level", "Article", "Coach", "Years_Text", "Year_Start", "Year_End", "Fetched_At"])
    if new_miss:
        wm.writerow(["Team_Name", "Level", "Wikipedia_Program"])
    if done:
        print(f"Resuming: {len(done)} programs already done, skipping them.")
    out, missing = [], []
    for n, p in enumerate(programs, 1):
        team = (p["Your_Team_Name"] or p["Matched_Team"]).strip()
        if team in done:
            continue
        before_out, before_miss = len(out), len(missing)
        prog = p["Team_Wiki"]
        rows, used = [], ""
        for title in (f"List of {prog} head football coaches", f"{prog} football"):
            real, html = page_html(title)
            time.sleep(0.5)
            if html:
                rows = coach_rows(html)
                if rows:
                    used = real
                    break
        if not rows:
            j = api(action="query", list="search", srsearch=f"{prog} football head coaches", srlimit=3)
            for hit in (j.get("query", {}).get("search", []) if j else []):
                real, html = page_html(hit["title"])
                time.sleep(0.5)
                if html:
                    rows = coach_rows(html)
                    if rows:
                        used = real
                        break
        if not rows:
            missing.append([team, p["Level"], prog])
        for coach, yrs in rows:
            for a, b in parse_years(yrs):
                out.append([team, p["Level"], used, coach, yrs, a, b if b else "", stamp])
        wr.writerows(out[before_out:]); wm.writerows(missing[before_miss:])
        fr.flush(); fm.flush()
        if n % 25 == 0:
            print(f"  {n}/{len(programs)} programs, {len(out):,} coach spans, {len(missing)} without a table")

    fr.close(); fm.close()
    print(f"\nDone this run: {len(out):,} coach spans added, {len(missing)} programs without a coach table.")


if __name__ == "__main__":
    main()
