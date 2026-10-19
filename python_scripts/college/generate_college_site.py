"""
generate_college_site.py  -- run on Windows (reads SQL Server; writes JSON for the college pages)

Writes docs/data/college/:
  current-season.json      latest rated season, every college team (rank among eligible teams)
  all-time-teams.json      top team-seasons of all time
  all-time-programs.json   program averages (college programs with 10+ ranked seasons)
  national-champions.json  McKnight's #1 for every season, with runner-up
  programs-index.json      every college program (search list)
  programs/<slug>.json     one file per program: season-by-season ratings, record, coach, games

The pages themselves (docs/pages/public/college/*.html, docs/js/college/college.js) are
static; rerun this after each rating run (or the weekly current-season run).

Eligibility for season ranks: Kind = 'College' and games >= max(5, 60% of a full schedule), where a
full schedule = the 75th percentile of college teams' games that season; never more than that
(the 1870s had 1-3 game seasons).
Keeps one-game and partial-schedule teams (e.g. 3-game wartime seasons) out of ranks, champions
and the all-time list.

Teams not connected by any chain of games to the season's main network (e.g. a junior-college
group that played no college) are rated but not ranked.

Island notes: if island_worklist.csv (from island_worklist.py) is present, team-seasons it flags
as detached, weakly linked (3 or fewer connecting games) or resting on one opponent get a Note.

Program files carry no timestamp and are only rewritten when their content changes, so a
weekly run only touches the programs that played.

Usage:  python generate_college_site.py
        python generate_college_site.py --top-teams 3000 --no-games
"""
import argparse, json, os, re, shutil
from collections import defaultdict
from datetime import datetime
from statistics import median

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "docs", "data", "college")

LEVELS = {"1A": "FBS", "1AA": "FCS", "I": "Division I", "Major College": "Major College",
          "Small College": "Small College", "II": "Division II", "NAIA": "NAIA",
          "NCAA": "College", "College": "College", "JC": "Junior College", "NJCAA": "Junior College"}
NOTE = ("Ratings use the same method as the high school ratings: every game, every level, one network. "
        "Early seasons and regions that seldom played outsiders (detached or island clusters) rest on few "
        "connecting games, so their ratings are less certain; data for many small schools before 1999 is incomplete.")


def slug(name):
    n = re.sub(r"['’`.]", "", name.lower().replace("&", " and "))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", n)).strip("-")


def level_name(div):
    if not div:
        return ""
    if div.startswith("III"):
        return "Division III"
    return LEVELS.get(div, div)


def division_map(history):
    out = {}
    for part in (history or "").split(";"):
        m = re.match(r"\s*(\d{4})-(\d{4})\s+(.+?)\s*$", part)
        if m:
            for s in range(int(m.group(1)), int(m.group(2)) + 1):
                out[s] = m.group(3)
    return out


def r1(x):
    return None if x is None else round(float(x), 2)


def dump(path, obj):
    """write only if the content changed (keeps git diffs small); returns True if written"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


def island_notes():
    fn = os.path.join(HERE, "island_worklist.csv")
    notes = {}
    if not os.path.exists(fn):
        return notes
    import csv
    for r in csv.DictReader(open(fn, encoding="utf-8")):
        try:
            key = (r["Team"], int(r["Season"]))
            links = int(r["Cluster_Links_Out"] or 0)
        except (KeyError, ValueError):
            continue
        hang = (r.get("Hangs_On") or "").strip()
        if r.get("Detached"):
            notes[key] = "Detached region: played no one outside its group that season"
        elif hang and ";" not in hang:
            notes[key] = f"Rating rests on games against {hang}"
        elif links <= 3:
            notes[key] = f"Weakly linked: its group is tied to the rest by {links} game" + ("s" if links != 1 else "")
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-teams", type=int, default=2000)
    ap.add_argument("--no-games", action="store_true", help="leave game lists out of program files")
    a = ap.parse_args()

    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    print("Reading teams, ratings, games, coaches ...")
    teams = {}
    for t, k, st, ld, h in cur.execute(
            "SELECT Team_Name, Kind, State, Latest_Division, Division_History FROM dbo.College_Team_Names"):
        teams[t] = dict(kind=k or "", state=st or "", latest=level_name(ld), divs=division_map(h))

    rat = {}
    for s, t, c, m, o, d, w in cur.execute("""
        SELECT r.Season, r.Home,
               ISNULL(r.Combined_Rating, 0.958 * r.Avg_Of_Avg_Of_Home_Modified_Score + 2.791),
               r.Avg_Of_Avg_Of_Home_Modified_Score, r.Offense, r.Defense, r.Week
        FROM dbo.College_Rankings r
        JOIN (SELECT Season, MAX(Week) AS W FROM dbo.College_Rankings GROUP BY Season) x
          ON x.Season = r.Season AND x.W = r.Week"""):
        rat[(t, s)] = (r1(c), r1(m), r1(o), r1(d), w)

    cols = {r[0] for r in cur.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'College_Scores'")}
    neutral = "Neutral" if "Neutral" in cols else "CAST(0 AS BIT)"
    games = cur.execute(f"""
        SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, {neutral}
        FROM dbo.College_Scores
        WHERE Home_Score IS NOT NULL AND Visitor_Score IS NOT NULL""").fetchall()
    coach = defaultdict(list)
    coach_ids = defaultdict(list)                      # (team, season) -> [(Coach_ID, name)]
    for t, s, c, role, cid in cur.execute(
            "SELECT Team_Name, Season, Coach, Role, Coach_ID FROM dbo.College_Coach_Seasons"):
        name = "No coach" if role == "No coach" else c
        if name and name not in coach[(t, s)]:
            coach[(t, s)].append(name)
        if cid is not None and role != "No coach" and all(x[0] != cid for x in coach_ids[(t, s)]):
            coach_ids[(t, s)].append((int(cid), c))
    conn.close()

    # per team-season record
    rec = defaultdict(lambda: [0, 0, 0, 0, 0])            # W L T PF PA
    glist = defaultdict(list)
    for s, d, h, hs, v, vs, n in games:
        for t, o, f, ag, site in ((h, v, hs, vs, "N" if n else "H"), (v, h, vs, hs, "N" if n else "A")):
            r = rec[(t, s)]
            r[0 if f > ag else 1 if f < ag else 2] += 1
            r[3] += f
            r[4] += ag
            if not a.no_games:
                aug1 = d is not None and d.month == 8 and d.day == 1
                glist[(t, s)].append(("" if (d is None or aug1) else d.isoformat(), o, site, f, ag))

    def is_college(t):
        return teams.get(t, {}).get("kind") == "College"

    # one unique file name per college program (two names could reduce to the same slug)
    slugs, used = {}, set()
    for t in sorted(teams):
        if teams[t]["kind"] == "College":
            b, i = slug(t) or "team", 2
            sl = b
            while sl in used:
                sl, i = f"{b}-{i}", i + 1
            used.add(sl)
            slugs[t] = sl
    sl_of = lambda t: slugs.get(t, "")

    seasons = sorted({s for (_, s) in rec})
    min_games = {}
    for s in seasons:
        gs = [sum(rec[(t, s)][:3]) for (t, ss) in rec if ss == s and is_college(t)]
        # 75th percentile = a typical full schedule; the median is dragged down by the many
        # small schools whose records are incomplete
        full = sorted(gs)[int(0.75 * (len(gs) - 1))] if gs else 3
        min_games[s] = int(min(full, max(5, round(0.6 * full))))

    # main network per season: teams not connected (through any chain of games) to the season's
    # largest group cannot be compared with it -- their level only reflects the seed, so they
    # are rated but not ranked
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for s_, d_, h_, hs_, v_, vs_, n_ in games:
        a_, b_ = find((h_, s_)), find((v_, s_))
        if a_ != b_:
            parent[a_] = b_
    comp_size = defaultdict(int)
    for k in list(parent):
        comp_size[find(k)] += 1
    main_root = {}
    for k in parent:
        r_ = find(k)
        if comp_size[r_] > comp_size.get(main_root.get(k[1]), 0):
            main_root[k[1]] = r_
    detached = {k for k in parent if find(k) != main_root.get(k[1])}

    def level(t, s):
        info = teams.get(t)
        if not info:
            return ""
        lv = level_name(info["divs"].get(s, ""))
        if not lv and info["divs"] and s > max(info["divs"]):
            lv = info["latest"]                         # history ends early: use current level
        return lv or info["kind"]

    # season ranks among eligible college teams
    season_rank, n_ranked = {}, {}
    by_season = defaultdict(list)
    for (t, s), r in rat.items():
        g = sum(rec[(t, s)][:3])
        if is_college(t) and g >= min_games.get(s, 3) and r[0] is not None and (t, s) not in detached:
            by_season[s].append((r[0], t))
    for s, lst in by_season.items():
        lst.sort(reverse=True)
        n_ranked[s] = len(lst)
        for i, (_, t) in enumerate(lst, 1):
            season_rank[(t, s)] = i

    def row(t, s):
        w, l, ti, pf, pa = rec[(t, s)]
        c, m, o, d, wk = rat.get((t, s), (None,) * 5)
        return dict(team=t, slug=sl_of(t), season=s, level=level(t, s),
                    state=teams.get(t, {}).get("state", ""), games=w + l + ti,
                    record=f"{w}-{l}" + (f"-{ti}" if ti else ""), w=w, l=l, t=ti, pf=pf, pa=pa,
                    combined=c, margin=m, offense=o, defense=d, rank=season_rank.get((t, s)),
                    of=n_ranked.get(s), coach=" / ".join(coach.get((t, s), [])),
                    coach_links=[[n_, cid_] for cid_, n_ in coach_ids.get((t, s), [])],
                    note=notes.get((t, s), "") or ("Not connected to the main college network this season "
                                                   "(rated, not ranked)" if (t, s) in detached else ""))

    notes = island_notes()
    print(f"island notes: {len(notes):,} team-seasons" if notes else "island notes: none (run island_worklist.py)")
    stamp = datetime.now().strftime("%B %d, %Y %I:%M %p").replace(" 0", " ")
    meta = lambda desc: dict(generated=stamp, description=desc, note=NOTE)

    written_programs, keep_files = 0, set()

    # current season
    cur_season = max(s for (_, s) in rat)
    cur_rows = [row(t, s) for (t, s) in rat if s == cur_season and is_college(t)]
    cur_rows.sort(key=lambda x: (x["rank"] is None, x["rank"] or 0, -(x["combined"] or -999)))
    week = max(v[4] for (t, s), v in rat.items() if s == cur_season)
    dump(os.path.join(OUT, "current-season.json"),
         dict(metadata=dict(meta(f"{cur_season} college ratings"), season=cur_season, week=week,
                            min_games=min_games.get(cur_season, 3)), items=cur_rows))
    print(f"current-season.json: {cur_season} (week {week}), {len(cur_rows):,} teams")

    # all-time team-seasons
    elig = [(rat[k][0], k) for k in season_rank]
    elig.sort(reverse=True)
    top = []
    for i, (_, (t, s)) in enumerate(elig[:a.top_teams], 1):
        x = row(t, s)
        x["alltime"] = i
        top.append(x)
    dump(os.path.join(OUT, "all-time-teams.json"), dict(metadata=meta("Greatest college team-seasons"), items=top))
    print(f"all-time-teams.json: {len(top):,} team-seasons")

    # national champions
    champs = []
    final_week = {}
    for (t, s_), v in rat.items():
        final_week[s_] = max(final_week.get(s_, 0), v[4] or 0)
    for s in sorted(by_season):
        lst = by_season[s]
        if not lst or final_week.get(s, 52) < 52:
            continue                                  # season still in progress: no champion yet
        c1, t1 = lst[0]
        x = row(t1, s)
        x["teams_ranked"] = len(lst)
        if len(lst) > 1:
            c2, t2 = lst[1]
            x["runner_up"], x["runner_up_slug"], x["runner_up_rating"] = t2, sl_of(t2), r1(c2)
            x["gap"] = r1(c1 - c2)
        champs.append(x)
    dump(os.path.join(OUT, "national-champions.json"),
         dict(metadata=meta("McKnight's college national champions (highest rating each season)"), items=champs))
    print(f"national-champions.json: {len(champs)} seasons")

    # programs
    titles = defaultdict(int)
    for x in champs:
        titles[x["team"]] += 1
    prog_seasons = defaultdict(list)
    for (t, s) in rec:
        if is_college(t):
            prog_seasons[t].append(s)
    index, programs = [], []
    for t, ss in prog_seasons.items():
        ss.sort()
        rows = [row(t, s) for s in ss]
        ranked = [x for x in rows if x["rank"] is not None]
        W = sum(x["w"] for x in rows); L = sum(x["l"] for x in rows); T = sum(x["t"] for x in rows)
        best = max(ranked, key=lambda x: x["combined"]) if ranked else None
        info = teams.get(t, {})
        entry = dict(team=t, slug=sl_of(t), state=info.get("state", ""), level=info.get("latest", ""),
                     first=ss[0], last=ss[-1], seasons=len(ss), ranked_seasons=len(ranked),
                     w=W, l=L, t=T, record=f"{W}-{L}" + (f"-{T}" if T else ""),
                     pct=round((W + 0.5 * T) / (W + L + T), 3) if W + L + T else None,
                     avg=r1(sum(x["combined"] for x in ranked) / len(ranked)) if ranked else None,
                     best_season=best["season"] if best else None, best=best["combined"] if best else None,
                     titles=titles.get(t, 0))
        index.append({k: entry[k] for k in ("team", "slug", "state", "level", "first", "last", "seasons")})
        if len(ranked) >= 10:
            programs.append(entry)
        for x in rows:
            if not a.no_games:
                x["games_list"] = [dict(date=g[0], opp=g[1], opp_slug=sl_of(g[1]),
                                        site=g[2], pf=g[3], pa=g[4]) for g in glist[(t, x["season"])]]
                x["games_list"].sort(key=lambda g: g["date"] or "9999")
        keep_files.add(sl_of(t) + ".json")
        written_programs += dump(os.path.join(OUT, "programs", sl_of(t) + ".json"),
                                 dict(metadata=dict(description=t, note=NOTE), program=entry, seasons=rows))
    index.sort(key=lambda x: x["team"])
    programs.sort(key=lambda x: -(x["avg"] or -999))
    for i, p in enumerate(programs, 1):
        p["rank"] = i
    dump(os.path.join(OUT, "programs-index.json"), dict(metadata=meta("College programs"), items=index))
    dump(os.path.join(OUT, "all-time-programs.json"),
         dict(metadata=meta("College programs ranked by average rating (10+ ranked seasons)"), items=programs))
    stale = [f for f in os.listdir(os.path.join(OUT, "programs")) if f.endswith(".json") and f not in keep_files]
    for f in stale:                                   # programs renamed or merged away
        os.remove(os.path.join(OUT, "programs", f))
    print(f"programs: {len(index):,} program files ({written_programs:,} changed, {len(stale)} removed); "
          f"all-time-programs.json {len(programs):,} programs")
    write_coaches(rec, rat, season_rank, n_ranked, coach_ids, titles, row, final_week, meta, stamp)
    write_rivalries(games, season_rank, n_ranked, final_week, sl_of, meta)
    print(f"\nWritten to {OUT}")


def write_coaches(rec, rat, season_rank, n_ranked, coach_ids, titles, row, final_week, meta, stamp):
    """Coach careers, straight average and value added.

    Straight average = mean rating of the coach's seasons as SOLE head coach in completed,
    ranked seasons (min 10 such seasons for the main list).
    Value added = for each tenure (consecutive seasons at one school), the school's average
    rating during the tenure minus its average in the 5 ranked seasons before and the 5 after
    (other coaches only). Career value added = season-weighted mean over tenures that have a
    baseline of at least 2 seasons.
    """
    WINDOW = 5
    complete = lambda s: final_week.get(s, 52) >= 52
    sole = {}                                           # (team, season) -> coach id when one coach
    seasons_of = defaultdict(list)                      # coach id -> [(season, team, shared)]
    names = defaultdict(lambda: defaultdict(int))
    for (t, s), lst in coach_ids.items():
        for cid, n in lst:
            seasons_of[cid].append((s, t, len(lst) > 1))
            names[cid][n] += 1
        if len(lst) == 1:
            sole[(t, s)] = lst[0][0]

    def rated(t, s):
        return (t, s) in season_rank and complete(s)

    champs_by = defaultdict(int)
    for (t, s), r in season_rank.items():
        if r == 1 and complete(s) and sole.get((t, s)):
            champs_by[sole[(t, s)]] += 1

    index, n_files = [], 0
    keep = set()
    out_dir = os.path.join(OUT, "coaches")
    for cid, lst in seasons_of.items():
        lst.sort()
        name = max(names[cid].items(), key=lambda x: x[1])[0]
        # tenures: consecutive seasons at one school
        tenures = []
        for s, t, shared in lst:
            if tenures and tenures[-1]["team"] == t and s - tenures[-1]["last"] <= 1:
                tenures[-1]["last"] = s
                tenures[-1]["seasons"].append(s)
            else:
                tenures.append(dict(team=t, first=s, last=s, seasons=[s]))
        sole_vals, va_num, va_den, pcts = [], 0.0, 0, []
        for tn in tenures:
            t = tn["team"]
            mine = [s for s in tn["seasons"] if sole.get((t, s)) == cid and rated(t, s)]
            vals = [rat[(t, s)][0] for s in mine]
            sole_vals += vals
            # era-neutral: place in that season's ranking, 100 = best team, 0 = last
            pcts += [100.0 * (1 - (season_rank[(t, s)] - 1) / max(1, n_ranked[s] - 1)) for s in mine]
            before = [rat[(t, y)][0] for y in range(tn["first"] - WINDOW, tn["first"])
                      if rated(t, y) and sole.get((t, y)) != cid]
            after = [rat[(t, y)][0] for y in range(tn["last"] + 1, tn["last"] + 1 + WINDOW)
                     if rated(t, y) and sole.get((t, y)) != cid]
            base = before + after
            W = sum(rec[(t, s)][0] for s in tn["seasons"]); L = sum(rec[(t, s)][1] for s in tn["seasons"])
            T = sum(rec[(t, s)][2] for s in tn["seasons"])
            tn.update(record=f"{W}-{L}" + (f"-{T}" if T else ""), w=W, l=L, t=T,
                      avg=r1(sum(vals) / len(vals)) if vals else None, rated_seasons=len(vals),
                      before=r1(sum(before) / len(before)) if before else None, n_before=len(before),
                      after=r1(sum(after) / len(after)) if after else None, n_after=len(after))
            tn["value_added"] = r1(tn["avg"] - sum(base) / len(base)) if vals and len(base) >= 2 else None
            if tn["value_added"] is not None:
                va_num += tn["value_added"] * len(vals)
                va_den += len(vals)
            tn["slug"] = row(t, tn["first"])["slug"]
            del tn["seasons"]
        W = sum(x["w"] for x in tenures); L = sum(x["l"] for x in tenures); T = sum(x["t"] for x in tenures)
        best = max(((rat[(t, s)][0], s, t) for s, t, _ in lst if sole.get((t, s)) == cid and rated(t, s)),
                   default=None)
        schools = []
        for x in tenures:
            if x["team"] not in schools:
                schools.append(x["team"])
        entry = dict(id=cid, coach=name, first=lst[0][0], last=lst[-1][0], seasons=len({s for s, _, _ in lst}),
                     rated_seasons=len(sole_vals), schools=", ".join(schools), n_schools=len(schools),
                     w=W, l=L, t=T, record=f"{W}-{L}" + (f"-{T}" if T else ""),
                     pct=round((W + 0.5 * T) / (W + L + T), 3) if W + L + T else None,
                     avg=r1(sum(sole_vals) / len(sole_vals)) if sole_vals else None,
                     era_pct=r1(sum(pcts) / len(pcts)) if pcts else None,
                     value_added=r1(va_num / va_den) if va_den else None, va_seasons=va_den,
                     best=best[0] if best else None, best_season=f"{best[1]} {best[2]}" if best else "",
                     titles=champs_by.get(cid, 0))
        index.append(entry)
        season_rows = []
        for s, t, shared in lst:
            x = row(t, s)
            season_rows.append(dict(season=s, team=t, slug=x["slug"], level=x["level"], record=x["record"],
                                    w=x["w"], combined=x["combined"], rank=x["rank"], of=x["of"],
                                    shared="yes" if shared else "", coach=x["coach"]))
        fn = f"{cid}.json"
        keep.add(fn)
        n_files += dump(os.path.join(out_dir, fn), dict(metadata=dict(description=name, note=NOTE),
                                                         coach=entry, tenures=tenures, seasons=season_rows))
    os.makedirs(out_dir, exist_ok=True)
    stale = [f for f in os.listdir(out_dir) if f.endswith(".json") and f not in keep]
    for f in stale:
        os.remove(os.path.join(out_dir, f))
    index.sort(key=lambda x: -(x["avg"] if x["avg"] is not None else -999))
    dump(os.path.join(OUT, "coaches-index.json"),
         dict(metadata=dict(meta("College head coaches"), window=WINDOW), items=index))
    print(f"coaches: {len(index):,} coaches ({n_files:,} files changed, {len(stale)} removed); "
          f"{sum(1 for x in index if x['rated_seasons'] >= 10):,} with 10+ rated seasons")



# ---------------------------------------------------------------------------------------------
# Greatest rivalries -- the high school method (generate_greatest_rivalries_json.py) with an
# era-neutral quality measure: college ratings rise over the decades, so "elite" and the game
# score use each team's place in that season's ranking (percentile, 100 = #1) instead of the
# raw rating.
RIV_ELITE_PCT = 75        # team in the top 25% of ranked college teams that season ...
RIV_ELITE_AVG = 70        # ... and averaging top-30% over that season and the 4 before (2+ seasons)
RIV_MAX_MARGIN = 8
RIV_MIN_MEETINGS = 5
RIV_TOP = 100


def closeness(m):
    m = abs(m)
    return 0.85 if m == 0 else 1.00 if m == 1 else 0.90 if m <= 3 else 0.75 if m <= 7 else 0.60 if m == 8 else 0.0


def write_rivalries(games, season_rank, n_ranked, final_week, sl_of, meta):
    complete = lambda s: final_week.get(s, 52) >= 52
    pct = {}
    for (t, s), r in season_rank.items():
        if complete(s):
            pct[(t, s)] = 100.0 * (1 - (r - 1) / max(1, n_ranked[s] - 1))

    def elite(t, s):
        p = pct.get((t, s))
        if p is None or p < RIV_ELITE_PCT:
            return False
        window = [pct[(t, y)] for y in range(s - 4, s + 1) if (t, y) in pct]
        return len(window) >= 2 and sum(window) / len(window) >= RIV_ELITE_AVG

    series = {}                                         # pair -> [a_wins, b_wins, ties, n, first, last]
    qual = defaultdict(list)
    for s, d, h, hs, v, vs, n in games:
        if h == v:
            continue
        a, b = sorted((h, v))
        fa, fb = (hs, vs) if a == h else (vs, hs)
        x = series.setdefault((a, b), [0, 0, 0, 0, s, s])
        x[0 if fa > fb else 1 if fb > fa else 2] += 1
        x[3] += 1
        x[4] = min(x[4], s)
        x[5] = max(x[5], s)
        if complete(s) and abs(hs - vs) <= RIV_MAX_MARGIN and elite(h, s) and elite(v, s):
            pri = (pct[(h, s)] + pct[(v, s)]) / 2 * closeness(hs - vs)
            qual[(a, b)].append(dict(season=s, date="" if d is None or (d.month == 8 and d.day == 1) else d.isoformat(),
                                     home=h, visitor=v, home_score=hs, visitor_score=vs,
                                     margin=hs - vs, pri=round(pri, 1)))
    items = []
    for (a, b), gl in qual.items():
        if len(gl) < RIV_MIN_MEETINGS:
            continue
        aw, bw, ti, n, first, last = series[(a, b)]
        total = sum(g["pri"] for g in gl)
        leader = (f"{a} leads {aw}-{bw}" if aw > bw else f"{b} leads {bw}-{aw}" if bw > aw
                  else f"Series tied {aw}-{bw}") + (f"-{ti}" if ti else "")
        gl.sort(key=lambda g: (g["season"], g["date"]))
        items.append(dict(team_a=a, slug_a=sl_of(a), team_b=b, slug_b=sl_of(b),
                          rivalry=f"{a} vs {b}", qualifying=len(gl), total=round(total, 1),
                          avg=round(total / len(gl), 1), q_first=gl[0]["season"], q_last=gl[-1]["season"],
                          meetings=n, first=first, last=last, a_wins=aw, b_wins=bw, ties=ti,
                          series=leader, games=gl))
    items.sort(key=lambda x: -x["total"])
    items = items[:RIV_TOP]
    for i, x in enumerate(items, 1):
        x["rank"] = i
    dump(os.path.join(OUT, "greatest-rivalries.json"),
         dict(metadata=dict(meta("Greatest college rivalries"), elite_pct=RIV_ELITE_PCT, elite_avg=RIV_ELITE_AVG,
                            max_margin=RIV_MAX_MARGIN, min_meetings=RIV_MIN_MEETINGS), items=items))
    print(f"greatest-rivalries.json: {len(items)} rivalries "
          f"({sum(1 for v in qual.values() if len(v) >= RIV_MIN_MEETINGS):,} pairs qualified)")


if __name__ == "__main__":
    main()
