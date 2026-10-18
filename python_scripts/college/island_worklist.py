"""
island_worklist.py  -- run on Windows (reads SQL Server; changes nothing)

Diagnostic for "island" inflation: for every season, splits the schedule network into
clusters (teams that mostly play each other), then checks every top-N team-season:
how many games tie its cluster to the rest of college football, and whether the
cluster looks short of games (incomplete data). Output is a work list for targeted
data gathering -- a few crossover games tie a cluster back far more than extra
internal games do. Ratings are NOT changed.

One-opponent teams (athletic clubs, YMCAs, alumni, town and prep teams that played only
one college) stay in College_Scores and in the ratings, but they cannot tie a cluster to
anything, so by default they are set aside for this diagnosis: teams with fewer than 2
distinct opponents in a season are peeled off repeatedly (the graph's "2-core"). Each is
then reported as a Leaf team of the cluster it hangs on. --keep-leaves restores the old
counting.

Outputs (python_scripts/college/):
  island_worklist.csv        top-N team-seasons, most isolated first (Priority)
  island_clusters.csv        every cluster of every season with its link counts

Usage:  python island_worklist.py               (top 25, all seasons)
        python island_worklist.py --top 50 --from 1900
Needs:  pip install networkx
"""
import argparse, csv, os
from collections import defaultdict
from statistics import median

import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities
import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--from", dest="first", type=int, default=1869)
    ap.add_argument("--min-games", type=int, default=5)
    ap.add_argument("--keep-leaves", action="store_true",
                    help="count one-opponent teams as cluster members (old behaviour)")
    a = ap.parse_args()

    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    print("Reading games ...")
    games = cur.execute("SELECT Season, Home, Visitor FROM dbo.College_Scores WHERE Season >= ?", a.first).fetchall()
    print("Reading ratings (latest week per season) ...")
    rat = cur.execute("""
        SELECT r.Season, r.Home,
               -- Combined_Rating is only filled at the END of a recalc run; during a run use
               -- the same formula on the margin rating (identical order)
               ISNULL(r.Combined_Rating, 0.958 * r.Avg_Of_Avg_Of_Home_Modified_Score + 2.791)
        FROM dbo.College_Rankings r
        WHERE r.Season >= ? AND r.Week = (SELECT MAX(Week) FROM dbo.College_Rankings x WHERE x.Season = r.Season)
    """, a.first).fetchall()
    kinds = dict(cur.execute("SELECT Team_Name, Kind FROM dbo.College_Team_Names").fetchall())
    conn.close()

    by_season = defaultdict(nx.Graph)
    for s, h, v in games:
        g = by_season[s]
        if g.has_edge(h, v):
            g[h][v]["w"] += 1
        else:
            g.add_edge(h, v, w=1)
    ratings = defaultdict(list)
    for s, t, c in rat:
        if c is not None:
            ratings[s].append((float(c), t))

    work, clusters = [], []
    seasons = sorted(by_season)
    for n, s in enumerate(seasons, 1):
        full = by_season[s]
        full.remove_edges_from(list(nx.selfloop_edges(full)))
        deg = dict(full.degree(weight="w"))
        if a.keep_leaves:
            g = full
        else:
            g = nx.k_core(full, 2)                          # peel teams with < 2 distinct opponents
            if g.number_of_nodes() < 3:
                g = full
        core_deg = [d for t, d in deg.items() if t in g]
        med_games = median(core_deg) if core_deg else 0
        # each peeled team hangs on the nearest core team (multi-source BFS)
        hang, parent = {}, {}
        frontier = list(g.nodes)
        seen = set(frontier)
        root = {t: t for t in frontier}
        while frontier:
            nxt = []
            for t in frontier:
                for o in full[t]:
                    if o not in seen:
                        seen.add(o)
                        root[o] = root[t]
                        hang[o] = root[t]
                        parent[o] = t
                        nxt.append(o)
            frontier = nxt

        def below(t):                                       # peeled teams that reach the core through t
            out = set()
            for x in hang:
                p = parent.get(x)
                while p is not None:
                    if p == t:
                        out.add(x)
                        break
                    p = parent.get(p)
            return out
        comps = sorted(nx.connected_components(g), key=len, reverse=True)
        main = comps[0]
        comms = list(greedy_modularity_communities(g.subgraph(main), weight="w")) if len(main) > 2 else [main]
        comms += [c for c in comps[1:]]                     # detached components are clusters with 0 links
        info, cid = [], {}
        for i, c in enumerate(comms):
            inside = sum(d["w"] for _, _, d in g.subgraph(c).edges(data=True))
            out = sum(d["w"] for t in c for o, d in g[t].items() if o not in c)
            out_opp = len({o for t in c for o in g[t] if o not in c})
            gpt = 2 * inside / len(c) + out / len(c)        # games per team in the cluster
            top = sorted(c, key=lambda t: -deg.get(t, 0))[:6]
            info.append((len(c), inside, out, out_opp, gpt, top, i >= len(comms) - (len(comps) - 1)))
            for t in c:
                cid[t] = i
            leaves = [t for t, r in hang.items() if r in c]
            leaf_games = sum(full.degree(t, weight="w") for t in leaves)
            clusters.append([s, i + 1, len(c), inside, out, out_opp,
                             f"{out / (inside + out):.0%}" if inside + out else "", round(gpt, 1),
                             round(med_games, 1), "detached" if info[-1][6] else "",
                             len(leaves), leaf_games, "; ".join(top)])
        for t, r in hang.items():                           # peeled teams report their cluster
            if r in cid:
                cid[t] = cid[r]
        ranked = sorted((x for x in ratings.get(s, []) if deg.get(x[1], 0) >= a.min_games), reverse=True)[:a.top]
        for rank, (cr, t) in enumerate(ranked, 1):
            if t not in cid:
                continue
            size, inside, out, out_opp, gpt, top, detached = info[cid[t]]
            hangs = ""
            if t in hang:
                # the team itself has only one real path into the network: its rating rests on
                # the games against the team it hangs on, whatever its cluster looks like
                deps = below(t)
                link_opps = sorted(o for o in full[t] if o not in deps)
                hangs = "; ".join(link_opps)
                out = sum(full[t][o]["w"] for o in link_opps)
                out_opp = len(link_opps)
                inside = full.degree(t, weight="w") - out
                size = 1 + len(deps)
            share = out / (inside + out) if inside + out else 0
            short = gpt < 0.7 * med_games                       # cluster plays far fewer games than usual
            # higher priority: higher rank, fewer links, smaller share, signs of missing games
            priority = (a.top + 1 - rank) * (1 / (1 + out)) * (1.5 if share < 0.1 else 1) * (1.5 if short else 1) \
                       * (3 if detached else 1)
            work.append([round(priority, 3), s, rank, t, kinds.get(t, ""), round(cr, 1), deg.get(t, 0),
                         size, inside, out, out_opp, f"{share:.0%}", round(gpt, 1), round(med_games, 1),
                         "yes" if short else "", "detached" if detached else "", hangs, "; ".join(top)])
        if n % 25 == 0:
            print(f"  {n}/{len(seasons)} seasons")

    work.sort(key=lambda x: -x[0])
    with open(os.path.join(HERE, "island_worklist.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Priority", "Season", "Rank", "Team", "Kind", "Combined", "Team_Games", "Cluster_Teams",
                    "Cluster_Games_Inside", "Cluster_Links_Out", "Distinct_Outside_Opponents", "Link_Share",
                    "Cluster_Games_Per_Team", "Season_Median_Games", "Looks_Short_Of_Games", "Detached",
                    "Hangs_On", "Cluster_Main_Teams"])
        w.writerows(work)
    with open(os.path.join(HERE, "island_clusters.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Season", "Cluster", "Teams", "Games_Inside", "Links_Out", "Distinct_Outside_Opponents",
                    "Link_Share", "Games_Per_Team", "Season_Median_Games", "Detached",
                    "Leaf_Teams", "Leaf_Games", "Main_Teams"])
        w.writerows(clusters)
    weak = [x for x in work if x[9] < 15 or float(x[11].rstrip('%')) < 10]
    print(f"\n{len(work):,} top-{a.top} team-seasons checked; {len(weak):,} sit in weakly linked clusters "
          f"(<15 links or <10% of cluster games).")
    print("Written: island_worklist.csv, island_clusters.csv")
    det = [x for x in work if x[15]]
    if det:
        print(f"\n{len(det)} of them are in DETACHED clusters ({min(x[1] for x in det)}-{max(x[1] for x in det)}): "
              "regions that played no one else that season -- real for the early game, not missing data.")
    print("\nTop 20 weakly linked team-seasons that are NOT detached (best targets for finding games):")
    for x in [x for x in work if not x[15]][:20]:
        print(f"  {x[1]} #{x[2]:<2} {x[3]:24s} cluster {x[7]:3d} teams, {x[9]:3d} links ({x[11]}), "
              f"{'short of games' if x[14] else ''} {x[15]}"
              f"{'  HANGS ON ' + x[16] if x[16] else ''}")


if __name__ == "__main__":
    main()
