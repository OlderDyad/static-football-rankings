"""
check_dropped_digits.py  -- reads dropped_digit_candidates.csv, changes nothing in SQL

For each 1912-1950 game where a score is 1, 4 or 5 (not a 1-0 forfeit), fetch the Winsipedia
season page of one of the two teams (cache: schedules/cache_winsipedia/<slug>/) and compare.

Output dropped_digit_results.csv:
  CONFIRMED  Winsipedia has the same score (real 4/5 scores)
  FIX        Winsipedia's score for that team starts with our digit and the other score matches
             (our score lost a digit)  -> New_Home / New_Visitor filled in
  DIFFERENT  game found, other difference -- check by hand
  NOT FOUND  no page / game not on the page

Usage: python check_dropped_digits.py [--delay 10] [--limit N]
"""
import argparse, csv, json, os, re, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_winsipedia as fw

SCHED = os.path.join(HERE, "schedules")


def slug_guess(name, inv, rev):
    c = []
    for disp in [rev.get(name), name]:
        if disp and disp in inv:
            c.append(inv[disp])
    base = name.replace("&", "and").replace("'", "").replace("`", "").replace(".", "")
    base = re.sub(r"\bSt\b", "State", base)
    c.append(re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-"))
    c.append(re.sub(r"[^a-z0-9]+", "-", name.replace("&", "").replace("'", "").replace(".", "").lower()).strip("-"))
    out = []
    for s in c:
        if s and s not in out:
            out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=10)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    inv = {v: k for k, v in json.load(open(os.path.join(SCHED, "winsipedia_slugs.json"), encoding="utf-8")).items()}
    rev = {}
    for r in csv.reader(open(os.path.join(SCHED, "schedule_name_map.csv"), encoding="utf-8-sig")):
        if len(r) >= 2 and r[1] not in ("SKIP", "Team_Name"):
            rev.setdefault(r[1], r[0])
    rows = list(csv.reader(open(os.path.join(HERE, "dropped_digit_candidates.csv"), encoding="utf-8-sig")))
    out, bad_slugs, n = [], set(), 0
    for r in rows:
        aid, season, d, H, hs, V, vs = r[0], int(r[1]), r[2], r[3], int(r[4]), r[5], int(r[6])
        if {hs, vs} == {0, 1}:
            continue
        n += 1
        if a.limit and n > a.limit:
            break
        # fetch the side with the suspicious score first
        sides = [(H, hs, vs, True), (V, vs, hs, False)]
        sides.sort(key=lambda s: 0 if s[1] in (1, 4, 5) else 1)
        res = ("NOT FOUND", "", "", "", "")
        for team, ts, os_, is_home in sides:
            for slug in slug_guess(team, inv, rev):
                if slug in bad_slugs:
                    continue
                try:
                    page, fetched = fw.get(slug, season, a.delay, os.path.join(SCHED, "cache_winsipedia", slug))
                except Exception as e:
                    print(f"  {slug} {season}: {e}")
                    page = ""
                if not page or "Page Not Found" in page[:3000]:
                    bad_slugs.add(slug)
                    continue
                gs = fw.games(page, season, "")
                try:
                    our = date.fromisoformat(d)
                except ValueError:
                    our = None
                best = None
                for gd, opp, site, wts, wos, rr, loc in gs:
                    if our and gd:
                        if abs((date.fromisoformat(gd) - our).days) > 7:
                            continue
                    elif our and our.month == 8 and our.day == 1:
                        pass                                   # undated row: compare by score only
                    if wos == os_ or wts == ts or (str(wts).startswith(str(ts)) and wos == os_):
                        best = (gd, opp, wts, wos)
                        if wts == ts and wos == os_:
                            break
                if best:
                    gd, opp, wts, wos = best
                    if wts == ts and wos == os_:
                        st = "CONFIRMED"
                    elif wos == os_ and str(wts).startswith(str(ts)) and wts != ts:
                        st = "FIX"
                    else:
                        st = "DIFFERENT"
                    nh, nv = (wts, wos) if is_home else (wos, wts)
                    res = (st, f"{slug} {gd} vs {opp} {wts}-{wos}", nh if st == "FIX" else "", nv if st == "FIX" else "", slug)
                    break
            if res[0] != "NOT FOUND":
                break
        out.append([aid, season, d, H, hs, V, vs, res[0], res[2], res[3], res[1], r[7]])
        print(f"{res[0]:10} {season} {H} {hs}-{vs} {V}   {res[1]}")
    with open(os.path.join(HERE, "dropped_digit_results.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Season", "Date", "Home", "Home_Score", "Visitor", "Visitor_Score",
                    "Status", "New_Home_Score", "New_Visitor_Score", "Winsipedia", "Source"])
        w.writerows(out)
    from collections import Counter
    print(Counter(o[7] for o in out))
    print("Written: dropped_digit_results.csv")


if __name__ == "__main__":
    main()
