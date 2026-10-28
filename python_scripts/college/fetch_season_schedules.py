"""
fetch_season_schedules.py -- run on Windows (needs internet). Changes nothing in the database.

Pulls one team's Wikipedia season pages ("1962 Oregon State Beavers football team") through the
MediaWiki API and turns each page's schedule into rows of a standard schedule CSV, which
import_schedule_csv.py then matches against College_Scores.

Reads the {{CFB Schedule Entry}} templates most season pages use. Pages without them are listed
as "no schedule template" (fill those by hand or from another source).

Usage:
  python fetch_season_schedules.py --team "Oregon St" --years 1960-1984 \
         --page "{year} Oregon State Beavers football team"
Output: schedules/<team>_<first>-<last>.csv
  Team, Season, Date, Opponent_Raw, Site (H/A/N), Team_Score, Opp_Score, Result, Location, Source
"""
import argparse, csv, json, os, re, time, urllib.error, urllib.parse, urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "schedules")
API = "https://en.wikipedia.org/w/api.php"
UA = "McKnightFootballRankings/1.0 (historical football research; olderdyad.github.io/static-football-rankings)"
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


CACHE = os.path.join(OUT, "cache")


def wikitext(title, tries=6):
    """Page wikitext, cached on disk (schedules/cache) so reruns only fetch what is missing.
    Backs off and retries on 429 / 5xx, honouring Retry-After."""
    os.makedirs(CACHE, exist_ok=True)
    cf = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", title) + ".json")
    if os.path.exists(cf):
        d = json.load(open(cf, encoding="utf-8"))
        return d.get("wikitext")
    q = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext", "format": "json",
                                "formatversion": 2, "redirects": 1, "maxlag": 5})
    wait = 10
    for _ in range(tries):
        try:
            req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                ra = e.headers.get("Retry-After")
                pause = int(ra) if ra and ra.isdigit() else wait
                print(f"    rate limited ({e.code}) -- waiting {pause}s")
                time.sleep(pause)
                wait = min(wait * 2, 120)
                continue
            raise
    else:
        raise RuntimeError(f"gave up on {title} after {tries} tries -- rerun later (cached pages are kept)")
    text = None if "error" in d else d["parse"]["wikitext"]
    json.dump({"title": title, "wikitext": text}, open(cf, "w", encoding="utf-8"))
    return text


def category_pages(cat):
    """{year: title} for season pages ('1936 Slippery Rock ... football team') in a Wikipedia category,
    cached like pages. Subcategories are not followed."""
    os.makedirs(CACHE, exist_ok=True)
    cf = os.path.join(CACHE, "cat_" + re.sub(r"[^A-Za-z0-9]+", "_", cat) + ".json")
    if os.path.exists(cf):
        titles = json.load(open(cf, encoding="utf-8"))
    else:
        titles, cont = [], {}
        while True:
            q = urllib.parse.urlencode({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat,
                                        "cmlimit": 500, "cmtype": "page", "format": "json", **cont})
            req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            titles += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
            if "continue" not in d:
                break
            cont = {"cmcontinue": d["continue"]["cmcontinue"]}
            time.sleep(1.0)
        json.dump(titles, open(cf, "w", encoding="utf-8"))
    out = {}
    for t in titles:
        m = re.match(r"^(\d{4}) .*football team$", t)
        if m:
            out.setdefault(int(m.group(1)), t)
    return out


def templates(text, name):
    """Yield the body of every {{name ...}} template, nesting-aware."""
    low = text.lower()
    key = "{{" + name.lower()
    i = 0
    while True:
        i = low.find(key, i)
        if i < 0:
            return
        depth, j = 0, i
        while j < len(text):
            if text.startswith("{{", j):
                depth += 1
                j += 2
            elif text.startswith("}}", j):
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        yield text[i + 2:j - 2]
        i = j


def split_top(line):
    """Split a template row on '|' that are not inside {{ }} or [[ ]]."""
    out, cur, d = [], [], 0
    i = 0
    while i < len(line):
        two = line[i:i + 2]
        if two in ("{{", "[["):
            d += 1; cur.append(two); i += 2; continue
        if two in ("}}", "]]"):
            d -= 1; cur.append(two); i += 2; continue
        if line[i] == "|" and d == 0:
            out.append("".join(cur)); cur = []; i += 1; continue
        cur.append(line[i]); i += 1
    out.append("".join(cur))
    return out


RESULT_RE = re.compile(r"^\s*(?:\{\{\s*)?([WLT])(?:\s*\}\})?\s*,?\s*(\d+)\s*[-\u2013\u2014]\s*(\d+)", re.I)


def compact_rows(text):
    """Blocks of the positional {{CFB schedule ...}} table used on many older season pages, as
    [(heading, rows)] -- heading = the nearest section title above the table (a team on a conference
    page, a year on a multi-season page). Row:
    |date|at/n/vs|opponent|[rank]|stadium|city|result|[attendance]|[source]  -> (date, atvs, opp, loc, W/L/T, a, b)"""
    low = text.lower()
    out = []
    i = 0
    while True:
        i = low.find("{{cfb schedule", i)
        if i < 0:
            return out
        nxt = low[i + 14:i + 15]
        if nxt not in ("\n", " ", "|", "\r"):          # skip {{CFB schedule entry / {{CFB schedule end ...
            i += 14
            continue
        depth, j = 0, i
        while j < len(text):
            if text.startswith("{{", j):
                depth += 1; j += 2
            elif text.startswith("}}", j):
                depth -= 1; j += 2
                if depth == 0:
                    break
            else:
                j += 1
        body = text[i + 2:j - 2]
        hs = list(re.finditer(r"^(=+)\s*(.*?)\s*\1\s*$", text[:i], re.M))
        heading = plain(hs[-1].group(2)) if hs else ""
        out.append((heading, []))
        i = j
        opts = {m.group(1).lower(): m.group(2).strip().lower()
                for m in re.finditer(r"^\|\s*(\w+)\s*=\s*(.*)$", body, re.M)}
        av = 2 if opts.get("time", "").startswith("y") else 1       # optional time column after the date
        for line in body.split("\n"):
            line = line.strip()
            if not line.startswith("|") or re.match(r"^\|\s*[\w ]+=", line):
                continue
            f = split_top(line[1:])
            k = next((n for n, x in enumerate(f) if n > av + 1 and RESULT_RE.match(plain(x))), None)
            if k is None:
                continue
            m = RESULT_RE.match(plain(f[k]))
            loc = ", ".join(x for x in (plain(f[k - 2]) if k - 2 > av + 1 else "", plain(f[k - 1])) if x.strip())
            out[-1][1].append((plain(f[0]), plain(f[av]).lower().strip(), plain(f[av + 1]), loc,
                               m.group(1).upper(), int(m.group(2)), int(m.group(3))))


def norm(x):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", x.lower()).split())


def params(body):
    """Split a template body into {param: value} at top-level pipes."""
    parts, depth, cur = [], 0, ""
    k = 0
    while k < len(body):
        two = body[k:k + 2]
        if two in ("{{", "[["):
            depth += 1
            cur += two
            k += 2
            continue
        if two in ("}}", "]]"):
            depth -= 1
            cur += two
            k += 2
            continue
        if body[k] == "|" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += body[k]
        k += 1
    parts.append(cur)
    out = {}
    for p in parts[1:]:
        if "=" in p:
            a, b = p.split("=", 1)
            out[a.strip().lower()] = b.strip()
    return out


def plain(s):
    """Wikitext -> plain text: [[a|b]] -> b, [[a]] -> a, drop templates, refs and markup."""
    s = re.sub(r"<ref[^>]*/>", "", s or "")
    s = re.sub(r"<ref.*?</ref>", "", s, flags=re.S)
    def _link(m):                     # {{cfb link|year=..|team=Oregon Ducks|title=Oregon}} -> title, else team
        kv = dict(x.split("=", 1) for x in m.group(1).split("|") if "=" in x)
        kv = {k.strip().lower(): v.strip() for k, v in kv.items()}
        return kv.get("title") or kv.get("team", "")
    s = re.sub(r"\{\{(?:cfb link|college football link|cfb team link)\|([^{}]*)\}\}", _link, s, flags=re.I)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s).replace("'''", "").replace("''", "").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_date(txt, season):
    m = re.search(r"([A-Za-z]+)\.?\s+(\d{1,2})", plain(txt))
    if not m or m.group(1).lower()[:3] not in [k[:3] for k in MONTHS]:
        return ""
    mon = next(v for k, v in MONTHS.items() if k[:3] == m.group(1).lower()[:3])
    yr = season + 1 if mon <= 2 else season                      # January bowls
    try:
        return date(yr, mon, int(m.group(2))).isoformat()
    except ValueError:
        return ""


COLS = ["Team", "Season", "Date", "Opponent_Raw", "Site", "Team_Score", "Opp_Score", "Result", "Location", "Source"]


def conference(pattern, years):
    """Every team's schedule from conference season pages. Each game appears under both teams;
    import_schedule_csv.py keeps one copy (IN-FILE COPY) and resolves the section titles to our names."""
    rows, missing = [], []
    for yr in years:
        title = pattern.format(year=yr)
        cached = os.path.exists(os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", title) + ".json"))
        text = wikitext(title)
        if not cached:
            time.sleep(3.0)
        if text is None:
            missing.append(yr)
            continue
        src = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        n0, nteams = len(rows), 0
        for heading, games in compact_rows(text):
            if not heading or re.fullmatch(r"\d{4}", heading) or not games:
                continue
            nteams += 1
            for dt, atvs, opp, loc, wl, a1, b1 in games:
                hi, lo = max(a1, b1), min(a1, b1)
                ts, os_ = (hi, lo) if wl == "W" else (lo, hi) if wl == "L" else (hi, hi)
                site = "A" if atvs.startswith("at") else "N" if atvs in ("n", "vs", "vs.", "neutral") else "H"
                opp = re.sub(r"^(?:at|vs\.?|No\.\s*\d+|#\d+)\s+", "", opp, flags=re.I)
                opp = re.sub(r"\s*\(\d+\)$", "", re.sub(r"<[^>]*>", "", opp)).strip()
                rows.append(dict(Team=heading, Season=yr, Date=parse_date(dt, yr), Opponent_Raw=opp, Site=site,
                                 Team_Score=ts, Opp_Score=os_, Result=wl, Location=loc, Source=src))
        print(f"  {yr}: {nteams} teams, {len(rows) - n0} game rows")
    if not rows:
        print("No games found." + (" No page: " + ", ".join(map(str, missing)) if missing else ""))
        return
    slug = re.sub(r"[^A-Za-z0-9]+", "_", pattern.replace("{year}", "").strip())
    fn = os.path.join(OUT, f"conf_{slug.strip('_')}_{years[0]}-{years[-1]}.csv")
    with open(fn, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} game rows written to {fn} (each game usually twice -- once per team)")
    if missing:
        print("No page found: " + ", ".join(map(str, missing)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", help="College_Team_Names name, e.g. 'Oregon St' (not needed with --conference)")
    ap.add_argument("--conference", help="conference season page with {year}, e.g. '{year} Iowa Conference football "
                                         "season': every team section on the page becomes rows (Team = section title)")
    ap.add_argument("--years", required=True, help="e.g. 1960-1984 or 1962")
    ap.add_argument("--page", help="page title with {year}, e.g. '{year} Oregon State Beavers football team'")
    ap.add_argument("--category", action="append",
                    help="Wikipedia category of season pages, e.g. 'Slippery Rock The Rock football seasons' "
                         "(several allowed; finds pages whatever the nickname was that year)")
    a = ap.parse_args()
    y = [int(x) for x in a.years.split("-")]
    years = range(y[0], (y[1] if len(y) > 1 else y[0]) + 1)
    os.makedirs(OUT, exist_ok=True)
    if a.conference:
        conference(a.conference, years)
        return
    if not a.team:
        ap.error("give --team (or --conference)")
    if not a.page and not a.category:
        ap.error("give --page or --category")
    bycat = {}
    for c in a.category or []:
        found = category_pages(c)
        print(f"Category '{c}': {len(found)} season pages" + (f" ({min(found)}-{max(found)})" if found else ""))
        for yr, t in found.items():
            bycat.setdefault(yr, t)
    if a.category and not a.page:
        years = [yr for yr in years if yr in bycat]
        if not years:
            print("No season pages in that range.")
            return
    rows, missing, notmpl = [], [], []
    for yr in years:
        title = bycat.get(yr) or a.page.format(year=yr)
        cached = os.path.exists(os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", title) + ".json"))
        text = wikitext(title)
        if not cached:
            time.sleep(3.0)                                       # be polite to the API
        if text is None:
            missing.append(yr)
            continue
        n0 = len(rows)
        for body in templates(text, "CFB Schedule Entry"):
            p = params(body)
            wl = p.get("w/l", "").lower()[:1]
            sc = re.findall(r"\d+", plain(p.get("score", "")))
            if wl not in ("w", "l", "t") or len(sc) < 2:
                continue                                          # cancelled / not played / no score
            hi, lo = max(int(sc[0]), int(sc[1])), min(int(sc[0]), int(sc[1]))
            ts, os_ = (hi, lo) if wl == "w" else (lo, hi) if wl == "l" else (hi, hi)
            site = "N" if p.get("neutral", "").lower().startswith("y") else \
                   "A" if p.get("away", "").lower().startswith("y") else "H"
            opp = re.sub(r"^(?:at|vs\.?|No\.\s*\d+|#\d+)\s+", "", plain(p.get("opponent", "")), flags=re.I)
            opp = re.sub(r"\s*\(\d+\)$", "", opp).strip()
            loc = ", ".join(x for x in (plain(p.get("site_stadium", "")), plain(p.get("site_cityst", ""))) if x)
            rows.append(dict(Team=a.team, Season=yr, Date=parse_date(p.get("date", ""), yr), Opponent_Raw=opp,
                             Site=site, Team_Score=ts, Opp_Score=os_, Result=wl.upper(), Location=loc,
                             Source="https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))))
        if len(rows) == n0:
            src = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            blocks = compact_rows(text)
            if len(blocks) > 1:
                key = norm(re.sub(r"^\d{4}\s+|\s+football team$", "", title))
                blocks = [b for b in blocks if b[0] == str(yr) or (b[0] and not re.fullmatch(r"\d{4}", b[0])
                          and (norm(b[0]) in key or norm(b[0]) == norm(a.team) or norm(a.team) in norm(b[0])))]
                if len(blocks) != 1:
                    blocks = []
            for dt, atvs, opp, loc, wl, a1, b1 in (blocks[0][1] if blocks else []):
                hi, lo = max(a1, b1), min(a1, b1)
                ts, os_ = (hi, lo) if wl == "W" else (lo, hi) if wl == "L" else (hi, hi)
                site = "A" if atvs.startswith("at") else "N" if atvs in ("n", "vs", "vs.", "neutral") else "H"
                opp = re.sub(r"^(?:at|vs\.?|No\.\s*\d+|#\d+)\s+", "", opp, flags=re.I)
                opp = re.sub(r"\s*\(\d+\)$", "", re.sub(r"<[^>]*>", "", opp)).strip()
                rows.append(dict(Team=a.team, Season=yr, Date=parse_date(dt, yr), Opponent_Raw=opp, Site=site,
                                 Team_Score=ts, Opp_Score=os_, Result=wl, Location=loc if site == "N" else loc,
                                 Source=src))
        if len(rows) == n0:
            notmpl.append(yr)
        print(f"  {yr}: {len(rows) - n0} games")
    fn = os.path.join(OUT, f"{re.sub(r'[^A-Za-z0-9]+', '_', a.team)}_{years[0]}-{years[-1]}.csv")
    with open(fn, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["Team", "Season", "Date", "Opponent_Raw", "Site", "Team_Score", "Opp_Score",
                                           "Result", "Location", "Source"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} games written to {fn}")
    if missing:
        print("No page found: " + ", ".join(map(str, missing)))
    if notmpl:
        print("Page found but no schedule template (fill another way): " + ", ".join(map(str, notmpl)))


if __name__ == "__main__":
    main()
