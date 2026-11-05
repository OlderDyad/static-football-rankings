"""
audit_vs_winsipedia_cache.py  -- run on Windows (reads SQL Server; changes nothing)

Compares EVERY game in College_Scores with the Winsipedia season pages already cached in
schedules/cache_winsipedia/<slug>/<year>.html (no web requests). For each cached team-season,
each Winsipedia game is matched to our game of that team within +/-2 days (opponent name not
needed), and the scores are compared from that team's side:

  SWAPPED    our two scores are the other way round
  DIGIT      one of ours is the first digit of Winsipedia's, the other matches
  DIFFERENT  other score difference
(matches are not written)

Output:
  winsipedia_cache_audit.csv          one row per mismatched game (Access_ID, scores, Winsipedia's)
  winsipedia_cache_audit_blocks.csv   mismatches grouped by Source and Access_ID block of 1,000,
                                      with the block's checked-game count -> a block with a high
                                      SWAPPED share is a reversed source block (like Austin Peay 89xxx)

Parsed pages are kept in schedules/cache_winsipedia_parsed.pkl so reruns are fast.
Usage: python audit_vs_winsipedia_cache.py   (first run parses ~1 GB of cached pages: 10-20 min)
"""
import csv, json, os, pickle, re, sys
from collections import defaultdict, Counter
from datetime import date

import pyodbc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_winsipedia as fw
from check_dropped_digits import slug_guess, SCHED
from check_residual_games import same_school

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;")
CACHE = os.path.join(SCHED, "cache_winsipedia")
PKL = os.path.join(SCHED, "cache_winsipedia_parsed.pkl")


def parsed_cache():
    old = {}
    if os.path.exists(PKL):
        old = pickle.load(open(PKL, "rb"))
    out, n = {}, 0
    for slug in sorted(os.listdir(CACHE)):
        d = os.path.join(CACHE, slug)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith(".html"):
                continue
            key = (slug, int(f[:4]))
            p = os.path.join(d, f)
            mt = os.path.getmtime(p)
            if key in old and old[key][0] == mt:
                out[key] = old[key]
                continue
            page = open(p, encoding="utf-8", errors="replace").read()
            m = re.search(r"<title>\s*(.*?)\s+Football Schedule", page)
            title = fw.strip(m.group(1)) if m else ""
            try:
                games = fw.games(page, key[1], "") if title else []
            except Exception:
                games = []
            out[key] = (mt, title, [(g[0], g[1], g[3], g[4]) for g in games])
            n += 1
            if n % 2000 == 0:
                print(f"  parsed {n:,} new pages ...")
    pickle.dump(out, open(PKL, "wb"))
    return out


def main():
    print("Reading cached Winsipedia pages ...")
    pages = parsed_cache()
    print(f"  {len(pages):,} team-season pages")
    inv = {v: k for k, v in json.load(open(os.path.join(SCHED, "winsipedia_slugs.json"), encoding="utf-8")).items()}
    rev = {}
    for r in csv.reader(open(os.path.join(SCHED, "schedule_name_map.csv"), encoding="utf-8-sig")):
        if len(r) >= 2 and r[1] not in ("SKIP", "Team_Name"):
            rev.setdefault(r[1], r[0])

    print("Reading games ...")
    cur = pyodbc.connect(CONN).cursor()
    by_team = defaultdict(list)        # (team, season) -> games
    info = {}
    for aid, season, d, h, hs, v, vs, src in cur.execute(
            "SELECT Access_ID, Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source "
            "FROM dbo.College_Scores WHERE Home_Score IS NOT NULL AND Visitor_Score IS NOT NULL "
            "AND ISNULL(Forfeit, 0) = 0"):
        if d is None:
            continue
        info[aid] = (season, d, h, hs, v, vs, src or "")
        by_team[(h, season)].append(aid)
        by_team[(v, season)].append(aid)

    # our team name -> slug whose page title is that school
    slugs_with_pages = defaultdict(set)
    for (slug, yr) in pages:
        slugs_with_pages[slug].add(yr)
    team_slug = {}
    for team in {t for t, _ in by_team}:
        for s in slug_guess(team, inv, rev):
            if s in slugs_with_pages:
                yr = next(iter(slugs_with_pages[s]))
                if same_school(team, pages[(s, yr)][1], rev):
                    team_slug[team] = s
                    break
    print(f"  {len(team_slug):,} of our teams have cached pages")

    checked, result = set(), {}
    for (team, season), aids in by_team.items():
        s = team_slug.get(team)
        if not s or (s, season) not in pages:
            continue
        for gd, opp, wts, wos in pages[(s, season)][2]:
            if not gd:
                continue
            g = date.fromisoformat(gd)
            near = [a for a in aids if abs((info[a][1] - g).days) <= 2]
            if len(near) != 1:
                continue
            a = near[0]
            se, d, h, hs, v, vs, src = info[a]
            ts, os_ = (hs, vs) if team == h else (vs, hs)
            checked.add(a)
            if (ts, os_) == (wts, wos):
                result[a] = "OK"
                continue
            if result.get(a) == "OK":
                continue
            if (ts, os_) == (wos, wts):
                st = "SWAPPED"
            elif (str(wts).startswith(str(ts)) and wts != ts and wos == os_) or \
                 (str(wos).startswith(str(os_)) and wos != os_ and wts == ts):
                st = "DIGIT"
            else:
                st = "DIFFERENT"
            nh, nv = (wts, wos) if team == h else (wos, wts)
            result[a] = (st, nh, nv, f"{s} {gd} vs {opp} {wts}-{wos}")

    bad = {a: r for a, r in result.items() if r != "OK"}
    print(f"\n{len(checked):,} games checked against Winsipedia; {len(bad):,} differ:",
          dict(Counter(r[0] for r in bad.values())))
    with open(os.path.join(HERE, "winsipedia_cache_audit.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Season", "Date", "Home", "Home_Score", "Visitor", "Visitor_Score",
                    "Status", "New_Home_Score", "New_Visitor_Score", "Winsipedia", "Source"])
        for a in sorted(bad):
            se, d, h, hs, v, vs, src = info[a]
            st, nh, nv, note = bad[a]
            w.writerow([a, se, d, h, hs, v, vs, st, nh, nv, note, src])
    blocks = defaultdict(Counter)
    for a in checked:
        k = (info[a][6][:40], a // 1000)
        blocks[k]["checked"] += 1
        r = result.get(a)
        if r and r != "OK":
            blocks[k][r[0]] += 1
    rows = []
    for (src, b), c in blocks.items():
        if c["SWAPPED"] + c["DIGIT"] + c["DIFFERENT"]:
            rows.append([src, f"{b*1000}-{b*1000+999}", c["checked"], c["SWAPPED"], c["DIGIT"], c["DIFFERENT"],
                         round(c["SWAPPED"] / c["checked"], 2)])
    rows.sort(key=lambda r: (-r[3], -r[6]))
    with open(os.path.join(HERE, "winsipedia_cache_audit_blocks.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Source", "Access_ID_Block", "Checked", "Swapped", "Digit", "Different", "Swapped_Share"])
        w.writerows(rows)
    print("\nBlocks with the most swapped games:")
    for r in rows[:15]:
        print(f"  {r[1]:>17}  {r[0][:28]:28}  checked {r[2]:4}  swapped {r[3]:3}  digit {r[4]:3}  diff {r[5]:3}")
    print("Written: winsipedia_cache_audit.csv, winsipedia_cache_audit_blocks.csv")


if __name__ == "__main__":
    main()
