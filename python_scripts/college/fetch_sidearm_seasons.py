"""
fetch_sidearm_seasons.py  -- reads the web only (safe during a rerate)

Reads a school's Sidearm SEASON schedule pages, <site>/sports/football/schedule/<year>, and writes
the same schedule CSV as the other fetchers -> import_schedule_csv.py. Season pages list each game
under its real opponent (opponent-history pages can lump one-off opponents together -- see the
Missouri S&T / Christian Brothers case), so prefer these when a school has them.

Home/away from the game's class (sidearm-schedule-home-game / -away-game / -neutral-game).
Pages are cached in schedules/cache_sidearm_seasons/<host>/<year>.html; 30 s between new pages
(Sidearm robots.txt crawl delay). Years with no page (redirect to the current schedule) are skipped.

Usage: python fetch_sidearm_seasons.py --site https://ephsports.williams.edu --team Williams --years 1965-1999
"""
import argparse, csv, html, os, re, time, urllib.request, urllib.error
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "McKnightFootballRankings/1.0 (historical football research; olderdyad.github.io/static-football-rankings)"
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def tx(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def get(site, year, cache, delay):
    host = re.sub(r"^https?://", "", site).strip("/")
    d = os.path.join(cache, host)
    os.makedirs(d, exist_ok=True)
    cf = os.path.join(d, f"{year}.html")
    if os.path.exists(cf):
        return open(cf, encoding="utf-8").read()
    url = f"{site.rstrip('/')}/sports/football/schedule/{year}"
    page = ""
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                if not r.geturl().rstrip("/").endswith(str(year)):
                    page = "REDIRECT"                       # no archive page for this year
                else:
                    page = r.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                page = "REDIRECT"
                break
            time.sleep(60)
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(60)
    open(cf, "w", encoding="utf-8").write(page)
    time.sleep(delay)
    return page


def games(page, year):
    out = []
    lis = re.findall(r'<li[^>]*class="([^"]*sidearm-schedule-game[ "][^"]*)"[^>]*>(.*?)</li>\s*'
                     r'(?=<li[^>]*class="[^"]*sidearm-schedule-game[ "]|</ul>)', page, re.S)
    for cls, b in lis:
        dm = re.search(r"sidearm-schedule-game-opponent-date[^>]*>(.*?)</div>", b, re.S)
        om = re.search(r"sidearm-schedule-game-opponent-name[^>]*>(.*?)</div>", b, re.S)
        rm = re.search(r"sidearm-schedule-game-result[^>]*>(.*?)</div>", b, re.S)
        lm = re.search(r"sidearm-schedule-game-location[^>]*>(.*?)</div>", b, re.S)
        if not (dm and om and rm):
            continue
        d = re.match(r"([A-Za-z]{3})\w*\.?\s+(\d{1,2})", tx(dm.group(1)))
        res = re.match(r"([WLT])\s*,?\s*(\d+)\s*-\s*(\d+)", tx(rm.group(1)))
        if not d or not res:
            continue
        m = MON[d.group(1).lower()]
        gd = date(year + (1 if m <= 2 else 0), m, int(d.group(2))).isoformat()
        a, bb = int(res.group(2)), int(res.group(3))
        wl = res.group(1)
        ts, os_ = (max(a, bb), min(a, bb)) if wl == "W" else (min(a, bb), max(a, bb)) if wl == "L" else (a, bb)
        site = "H" if "home-game" in cls else "A" if "away-game" in cls else "N" if "neutral-game" in cls else "U"
        opp = re.sub(r"^(?:#\d+\s+)", "", tx(om.group(1)))
        out.append((gd, opp, site, ts, os_, wl, tx(lm.group(1)) if lm else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--team", required=True)
    ap.add_argument("--years", required=True)
    ap.add_argument("--delay", type=float, default=30)
    a = ap.parse_args()
    y1, y2 = (int(x) for x in a.years.split("-"))
    cache = os.path.join(HERE, "schedules", "cache_sidearm_seasons")
    rows, empty = [], []
    for y in range(y1, y2 + 1):
        page = get(a.site, y, cache, a.delay)
        gs = games(page, y) if page and page != "REDIRECT" else []
        if not gs:
            empty.append(y)
        for gd, opp, site, ts, os_, wl, loc in gs:
            rows.append([a.team, y, gd, opp, site, ts, os_, wl, loc,
                         f"{a.site.rstrip('/')}/sports/football/schedule/{y}"])
        print(f"  {y}: {len(gs)} games")
    out = os.path.join(HERE, "schedules", f"{a.team.replace(' ', '_').replace('&', '')}_sidearm_{y1}-{y2}.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Team", "Season", "Date", "Opponent_Raw", "Site", "Team_Score", "Opp_Score", "Result", "Location", "Source"])
        w.writerows(rows)
    print(f"\n{len(rows)} games written to {out}")
    if empty:
        print("No games read for:", ", ".join(map(str, empty)))


if __name__ == "__main__":
    main()
