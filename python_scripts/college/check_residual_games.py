"""
check_residual_games.py  -- reads game_residuals.csv, changes nothing in SQL

Takes the top games of game_residuals.csv (worst misses first) and looks each one up on the
Winsipedia season page of either team (cache: schedules/cache_winsipedia/<slug>/, 10 s between
new pages). Output residual_check.csv, one row per game:

  CONFIRMED      same score on Winsipedia (the blowout/upset is real -- leave it)
  SWAPPED        Winsipedia has the two scores the other way round  -> New_Home/New_Visitor
  DIGIT          one of our scores is the first digit of Winsipedia's, the other matches -> New_*
  DIFFERENT      same game (date and opponent agree), different score -> New_* for review
  OTHER SCHOOL   Winsipedia's opponent carries another state, e.g. 'Christian Brothers (TN)'
  WRONG OPPONENT team's page has a game that day, against someone else (misnamed opponent?)
  NOT ON PAGE    page read, no game that week (Winsipedia may just lack it)
  NOT FOUND      no Winsipedia page for either team that season

Usage: python check_residual_games.py [--top 400] [--delay 10] [--min-impact 0]
"""
import argparse, csv, os, re, sys
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_winsipedia as fw
from check_dropped_digits import slug_guess, SCHED
import json


def norm(x):
    x = x.lower().replace("&", "and").replace("state", "st").replace("saint", "st")
    x = re.sub(r"\(.*?\)", " ", x)
    return re.sub(r"[^a-z0-9]+", " ", x).strip()


def same_team(ours, theirs, rev):
    a, b = norm(ours), norm(theirs)
    r = norm(rev.get(ours, ours))
    if not a or not b:
        return False
    if a == b or r == b or a in b or b in a or r in b:
        return True
    return a.split()[0] == b.split()[0] and len(a.split()[0]) > 3


def same_school(ours, title, rev):
    a, b, r = norm(ours), norm(title), norm(rev.get(ours, ours))
    a2 = re.sub(r" [a-z]{2}$", "", a)                         # 'cornell ia' -> 'cornell'
    return b in (a, r, a2) or a in b or r in b or b in a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=400)
    ap.add_argument("--delay", type=float, default=10)
    ap.add_argument("--min-impact", type=float, default=0)
    a = ap.parse_args()
    inv = {v: k for k, v in json.load(open(os.path.join(SCHED, "winsipedia_slugs.json"), encoding="utf-8")).items()}
    rev = {}
    for r in csv.reader(open(os.path.join(SCHED, "schedule_name_map.csv"), encoding="utf-8-sig")):
        if len(r) >= 2 and r[1] not in ("SKIP", "Team_Name"):
            rev.setdefault(r[1], r[0])
    games = list(csv.DictReader(open(os.path.join(HERE, "game_residuals.csv"), encoding="utf-8-sig")))
    games = [g for g in games if float(g["Impact"] or 0) >= a.min_impact][:a.top]
    out, bad = [], set()
    for i, g in enumerate(games, 1):
        season = int(g["Season"])
        H, V = g["Home"], g["Visitor"]
        hs, vs = int(g["Home_Score"]), int(g["Visitor_Score"])
        try:
            our = date.fromisoformat(g["Date"])
        except ValueError:
            our = None
        undated = our is None or (our.month == 8 and our.day == 1)
        status, new_h, new_v, note = "NOT FOUND", "", "", ""
        for team, opp, is_home in ((H, V, True), (V, H, False)):
            for slug in slug_guess(team, inv, rev):
                if slug in bad:
                    continue
                try:
                    page, _ = fw.get(slug, season, a.delay, os.path.join(SCHED, "cache_winsipedia", slug))
                except Exception as e:
                    print(f"  {slug} {season}: {e}")
                    page = ""
                if not page or "Page Not Found" in page[:3000]:
                    bad.add(slug)
                    continue
                m = re.search(r"<title>\s*(.*?)\s+Football Schedule", page)
                if m and not same_school(team, fw.strip(m.group(1)), rev):
                    bad.add(slug)                              # slug belongs to another school
                    continue
                rows = fw.games(page, season, "")
                if not rows:
                    continue
                near = [r for r in rows if r[0] and our and not undated
                        and abs((date.fromisoformat(r[0]) - our).days) <= 3]
                named = [r for r in rows if same_team(opp, r[1], rev)]
                cand = [r for r in near if same_team(opp, r[1], rev)] or named
                datediff = bool(cand) and not undated and not [r for r in near if same_team(opp, r[1], rev)]
                ts, os_ = (hs, vs) if is_home else (vs, hs)
                if cand:
                    best = min(cand, key=lambda r: abs(r[3] - ts) + abs(r[4] - os_))
                    d, oname, site, wts, wos = best[0], best[1], best[2], best[3], best[4]
                    nh, nv = (wts, wos) if is_home else (wos, wts)
                    if wts == ts and wos == os_:
                        status = "CONFIRMED"
                    elif wts == os_ and wos == ts:
                        status, new_h, new_v = "SWAPPED", nh, nv
                    elif (str(wts).startswith(str(ts)) and wts != ts and wos == os_) or \
                         (str(wos).startswith(str(os_)) and wos != os_ and wts == ts):
                        status, new_h, new_v = "DIGIT", nh, nv
                    else:
                        status, new_h, new_v = "DIFFERENT", nh, nv
                    note = f"{slug} {d} vs {oname} {wts}-{wos}" + ("  (date differs)" if datediff else "")
                    ost = (g["Visitor_State"] if is_home else g["Home_State"]) or ""
                    pm = re.search(r"\(([A-Z]{2})\)", oname)
                    if pm and ost and pm.group(1) != ost:
                        status = "OTHER SCHOOL"            # e.g. Christian Brothers (TN) vs our MO school
                elif near:
                    r = near[0]
                    status = "WRONG OPPONENT"
                    note = f"{slug} {r[0]} vs {r[1]} {r[3]}-{r[4]}"
                else:
                    status = "NOT ON PAGE"
                    note = f"{slug} read, {len(rows)} games"
                break
            if status not in ("NOT FOUND", "NOT ON PAGE"):
                break
        out.append([g["Impact"], g["Access_ID"], season, g["Date"], H, hs, V, vs, status, new_h, new_v, note, g["Hints"]])
        print(f"{i:4} {status:14} {season} {H} {hs}-{vs} {V}   {note}")
    with open(os.path.join(HERE, "residual_check.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Impact", "Access_ID", "Season", "Date", "Home", "Home_Score", "Visitor", "Visitor_Score",
                    "Status", "New_Home_Score", "New_Visitor_Score", "Winsipedia", "Hints"])
        w.writerows(out)
    print(Counter(o[8] for o in out))
    print("Written: residual_check.csv")


if __name__ == "__main__":
    main()
