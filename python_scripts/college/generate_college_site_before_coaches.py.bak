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
    for t, s, c, role in cur.execute("SELECT Team_Name, Season, Coach, Role FROM dbo.College_Coach_Seasons"):
        name = "No coach" if role == "No coach" else c
        if name and name not in coach[(t, s)]:
            coach[(t, s)].append(name)
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
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
