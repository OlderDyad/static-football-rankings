"""
fetch_winsipedia.py -- run on Windows (needs internet). Changes nothing in the database.

Season schedule pages from winsipedia.com/<slug>/schedule/<year> (one table per season: Result, Date,
Opponent, Score, Location, Notes) -> the standard schedule CSV for import_schedule_csv.py.
robots.txt (2026-10-26) allows these pages and sets no crawl delay; this script still waits --delay
seconds (default 10) between pages and caches every page in schedules/cache_winsipedia/<slug>/, so a
rerun only fetches what is missing. CHECK THE SITE'S TERMS OF USE BEFORE BULK USE.

Home/away: the site shows a location for some games only. Site = A when a location is shown that is not
the team's home town (--home "Greeley"), H when it is, U (unknown) when no location is shown.
import_schedule_csv.py --no-new-unknown leaves U games out of the inserts (they still repair / match).

Usage:  python fetch_winsipedia.py --slug northern-colorado --team "Northern Colorado" --home Greeley --years 1925-2000
Output: schedules/<team>_winsipedia_<first>-<last>.csv
"""
import argparse, csv, html, json, os, re, time, urllib.error, urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "schedules")
UA = "McKnightFootballRankings/1.0 (historical football research; olderdyad.github.io/static-football-rankings)"
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b", re.I)
SCORE_RE = re.compile(r"^\s*(\d{1,3})\s*[-–]\s*(\d{1,3})\s*$")


def strip(x):
    x = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", x, flags=re.S | re.I)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x))).strip()


def get(slug, year, delay, cache):
    os.makedirs(cache, exist_ok=True)
    cf = os.path.join(cache, f"{year}.html")
    if os.path.exists(cf):
        return open(cf, encoding="utf-8").read(), False
    url = f"https://www.winsipedia.com/{slug}/schedule/{year}"
    wait = 30
    for _ in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                page = r.read().decode("utf-8", "replace")
            break
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if isinstance(e, urllib.error.HTTPError):
                if e.code == 404:
                    page = ""
                    break
                if e.code not in (429, 500, 502, 503, 504):
                    raise
            print(f"    network error ({e}) -- waiting {wait}s")
            time.sleep(wait)
            wait = min(wait * 2, 300)
            continue
        except urllib.error.HTTPError as e:
            if e.code == 404:
                page = ""
                break
            if e.code in (429, 500, 502, 503, 504):
                print(f"    HTTP {e.code} -- waiting {wait}s")
                time.sleep(wait)
                wait = min(wait * 2, 300)
                continue
            raise
    else:
        raise RuntimeError(f"gave up on {url}")
    open(cf, "w", encoding="utf-8").write(page)
    time.sleep(delay)
    return page, True


def ld_homes(page):
    """{date: home team name} from the page's JSON-LD SportsEvent entries (they name homeTeam/awayTeam even
    when the table shows no location), plus the page school's own name."""
    homes, me = {}, ""
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        items = data.get("@graph", [data]) if isinstance(data, dict) else data
        for it in items if isinstance(items, list) else []:
            if not isinstance(it, dict):
                continue
            if it.get("@type") == "WebPage" and isinstance(it.get("mainEntity"), dict):
                me = it["mainEntity"].get("name", me)
            if it.get("@type") == "SportsEvent" and it.get("startDate"):
                h = (it.get("homeTeam") or {}).get("name", "")
                if h:
                    homes.setdefault(it["startDate"][:10], h)
    return homes, me


def games(page, year, home):
    out = []
    homes, me = ld_homes(page)
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = [strip(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
        si = next((i for i, c in enumerate(cells) if SCORE_RE.match(c)), None)
        if si is None or si < 1:
            continue
        res = next((c[:1].upper() for c in cells[:si] if re.match(r"^[WLT]\b", c)), "")
        dm = next((DATE_RE.search(c) for c in cells[:si] if DATE_RE.search(c)), None)
        a, b = (int(v) for v in SCORE_RE.match(cells[si]).groups())
        hi, lo = max(a, b), min(a, b)
        if res == "W":
            ts, os_ = hi, lo
        elif res == "L":
            ts, os_ = lo, hi
        elif res == "T" or a == b:
            ts, os_, res = a, b, "T"
        else:
            ts, os_ = a, b                                   # no result letter: page order (team first)
            res = "W" if a > b else "L"
        opp = re.sub(r"^(?:vs\.?|at|@)\s+", "", cells[si - 1]).strip()
        opp = re.sub(r"^#?\d+\s+", "", opp)                    # ranking prefix
        neutral = bool(re.search(r"\(N\)\s*$", opp))
        opp = re.sub(r"\s*\(N\)\s*$", "", opp)
        loc = cells[si + 1] if si + 1 < len(cells) and cells[si + 1] not in ("-", "—", "") else ""
        site = "N" if neutral else "U" if not loc else ("H" if home and home.lower() in loc.lower() else
                                    "N" if "neutral" in loc.lower() else "A")
        d = ""
        if dm:
            m = MON[dm.group(1).lower()[:3]]
            d = date(year + (1 if m <= 2 else 0), m, int(dm.group(2))).isoformat()
        if site in ("U", "A") and d in homes and me:        # JSON-LD names the home team
            site = "H" if homes[d] == me else ("A" if site == "U" or homes[d] == opp else site)
        out.append((d, opp, site, ts, os_, res, loc))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="winsipedia school slug, e.g. northern-colorado")
    ap.add_argument("--team", required=True, help="College_Team_Names name")
    ap.add_argument("--home", default="", help="home town as it appears in the Location column, e.g. Greeley")
    ap.add_argument("--years", required=True, help="e.g. 1925-2000")
    ap.add_argument("--delay", type=float, default=10)
    a = ap.parse_args()
    y = [int(x) for x in a.years.split("-")]
    years = range(y[0], (y[1] if len(y) > 1 else y[0]) + 1)
    cache = os.path.join(OUT, "cache_winsipedia", a.slug)
    probe, _ = get(a.slug, years[-1], a.delay, cache)       # wrong slug -> stop now, not after 100+ empty pages
    if not probe or "/schedule/" not in probe:
        print(f"{a.slug}: no page for {years[-1]} -- slug probably wrong (check winsipedia.com/{a.slug})")
        return
    rows, empty = [], []
    for yr in years:
        page, fetched = get(a.slug, yr, a.delay, cache)
        g = games(page, yr, a.home)
        if not g:
            empty.append(yr)
        for d, opp, site, ts, os_, res, loc in g:
            rows.append(dict(Team=a.team, Season=yr, Date=d, Opponent_Raw=opp, Site=site, Team_Score=ts,
                             Opp_Score=os_, Result=res, Location=loc,
                             Source=f"https://www.winsipedia.com/{a.slug}/schedule/{yr}"))
        print(f"  {yr}: {len(g)} games" + ("" if fetched else " (cached)"))
    fn = os.path.join(OUT, f"{re.sub(r'[^A-Za-z0-9]+', '_', a.team)}_winsipedia_{years[0]}-{years[-1]}.csv")
    with open(fn, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["Team", "Season", "Date", "Opponent_Raw", "Site", "Team_Score", "Opp_Score",
                                           "Result", "Location", "Source"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} games written to {fn}")
    if empty:
        print("No games read for: " + ", ".join(map(str, empty)) + "  (no season, or the page layout differs -- tell Claude)")


if __name__ == "__main__":
    main()
