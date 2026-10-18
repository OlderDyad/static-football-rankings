"""
split_ambiguous_names.py  (analysis only -- writes review CSVs, changes nothing)

Bare names "St Mary's", "St John's", "St Francis", "St Thomas" (and "Saint ..."
spellings) cover several schools. Each game is assigned to the candidate
school whose campus is nearest the OPPONENT (opponent coordinates from the
Access Location table). Then each season is smoothed: a team plays a regional
schedule, so a game only stays with a different candidate if its opponent is
much closer to that campus and that candidate has >= 2 games that season.

Outputs:
  ambiguous_split_review.csv   one row per game (Override_Name column for fixes)
  ambiguous_split_seasons.csv  one row per name/season/assigned school (review this)
"""
import csv, math, re
from collections import Counter, defaultdict

EXP = "access_export"

# Candidate schools: Wolfe-style coded name -> campus (lat, lon). NEW = not yet in the data.
CANDIDATES = {
    "St Francis": {"St Francis PA": (40.50, -78.63), "St Francis NY": (40.69, -73.99),
                   "St Francis IN": (41.08, -85.14), "St Francis IL": (41.52, -88.08)},
    "St John's":  {"St John's MN": (45.58, -94.39), "St John's NY": (40.72, -73.79),
                   "St John's Maryland": (38.98, -76.49), "St John's OH": (41.65, -83.54)},
    "St Mary's":  {"St Mary's CA": (37.84, -122.11), "St Mary KS": (39.19, -96.07),
                   "St Mary's MN": (44.05, -91.69), "St Mary's TX": (29.45, -98.56),
                   "St Mary's MI": (42.58, -83.37)},
    "St Thomas":  {"St Thomas MN": (44.94, -93.19), "St Thomas FL": (25.94, -80.24),
                   "St Thomas TX": (29.74, -95.39), "St Thomas PA": (41.41, -75.66)},
}
EXISTING = {"St Francis PA", "St Francis NY", "St Francis IN", "St Francis IL", "St John's MN",
            "St John's NY", "St John's Maryland", "St Mary's CA", "St Mary KS", "St Mary's MN",
            "St Thomas MN", "St Thomas FL"}
BASE_OF = {"st francis": "St Francis", "saint francis": "St Francis",
           "st john's": "St John's", "saint john's": "St John's",
           "st mary's": "St Mary's", "saint mary's": "St Mary's",
           "st thomas": "St Thomas", "saint thomas": "St Thomas"}


def clean(n):
    return re.sub(r"\s+", " ", (n or "").strip())


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def main():
    loc = {}
    for r in csv.DictReader(open(f"{EXP}/access_location.csv", encoding="utf-8")):
        try:
            lat, lon = float(r["Latitude"]), float(r["Longitude"])
        except ValueError:
            continue
        if lon > 0 and lat > 20:
            lon = -lon            # some longitudes are stored without the minus sign
        loc[clean(r["Location"]).lower()] = (lat, lon)

    all_rows = list(csv.DictReader(open(f"{EXP}/access_scores.csv", encoding="utf-8")))
    for r in all_rows:
        EXISTING.add(clean(r["Home"])); EXISTING.add(clean(r["Visitor"]))
    on_date = defaultdict(list)       # (date, team) -> opponents that day
    in_season = defaultdict(set)      # (team, season) -> opponents that season
    for r in all_rows:
        h, v, d, se = clean(r["Home"]), clean(r["Visitor"]), r["Date"][:10], int(float(r["Season"]))
        on_date[(d, h.lower())].append(v); on_date[(d, v.lower())].append(h)
        in_season[(h.lower(), se)].add(v); in_season[(v.lower(), se)].add(h)

    def coded_match(names, base):
        word = base.split()[1].lower()
        return [t for t in names if t in CANDIDATES[base] or
                (re.match(r"^(st|saint) " + re.escape(word), t.lower()) and t.lower() not in BASE_OF)]

    games = []
    for r in all_rows:
        h, v = clean(r["Home"]), clean(r["Visitor"])
        for side, me, opp in (("Home", h, v), ("Visitor", v, h)):
            base = BASE_OF.get(me.lower())
            if not base:
                continue
            p = loc.get(opp.lower())
            dist = {c: km(p, xy) for c, xy in CANDIDATES[base].items()} if p else {}
            se, d = int(float(r["Season"])), r["Date"][:10]
            dup = coded_match(on_date[(d, opp.lower())], base)
            sea = coded_match(in_season[(opp.lower(), se)], base)
            games.append(dict(id=r["ID"], season=se, date=d, side=side,
                              raw=me, base=base, opp=opp, dist=dist,
                              dup=dup[0] if dup else None, link=sea[0] if sea else None,
                              near=min(dist, key=dist.get) if dist else None,
                              loc2=clean(r["Location2"])))

    by_season = defaultdict(list)
    for g in games:
        by_season[(g["base"], g["season"])].append(g)

    for (base, season), gs in by_season.items():
        linked = Counter(g["dup"] or g["link"] for g in gs if g["dup"] or g["link"])
        votes_geo = Counter(g["near"] for g in gs if g["near"] and not g["dup"] and not g["link"])
        votes = linked if linked else Counter(g["near"] for g in gs if g["near"])
        dom = votes.most_common(1)[0][0] if votes else None
        share = votes[dom] / sum(votes.values()) if votes else 0
        for g in gs:
            if g["dup"]:
                g["assigned"], g["why"] = g["dup"], "DUPLICATE of same-date game under coded name"
            elif g["link"]:
                g["assigned"], g["why"] = g["link"], "opponent played coded team same season"
            elif linked and g["near"] and g["near"] != dom and votes_geo[g["near"]] >= 2 \
                    and g["dist"][g["near"]] * 3 < g["dist"].get(dom, 1e9):
                g["assigned"], g["why"] = g["near"], "split: second school this season (geography)"
            elif linked:
                g["assigned"], g["why"] = dom, "season linked to coded team"
            elif not g["near"]:
                g["assigned"], g["why"] = dom, "unlocated opponent -> season majority" if dom else "UNKNOWN"
            elif g["near"] == dom:
                g["assigned"], g["why"] = dom, "nearest campus"
            else:
                d_dom, d_near = g["dist"].get(dom, 1e9), g["dist"][g["near"]]
                if votes[g["near"]] >= 2 and d_near * 3 < d_dom:
                    g["assigned"], g["why"] = g["near"], "split: second school this season"
                else:
                    g["assigned"], g["why"] = dom, "smoothed to season majority"
            a = g["assigned"]
            # A regional opponent near another candidate campus (<400 km) and far from the
            # assigned one is almost always the other school, unless the game itself is linked.
            if (not g["dup"] and not g["link"] and g["near"] and a and g["near"] != a
                    and g["dist"][g["near"]] < 400 and g["dist"][g["near"]] * 3 < g["dist"].get(a, 1e9)):
                g["assigned"], g["why"] = g["near"], "regional opponent near this campus"
                a = g["assigned"]
            g["alt"] = ""
            if not g["dup"] and g["near"] and a and g["near"] != a and g["dist"][g["near"]] * 3 < g["dist"].get(a, 1e9):
                g["alt"] = g["near"]
            g["conf"] = "check" if g["alt"] else "high" if (g["dup"] or (linked and share >= 0.8) or share >= 0.8) else ("check" if dom else "low")
            g["share"] = share

    with open("ambiguous_split_review.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Access_ID", "Season", "Date", "Side", "Raw_Name", "Opponent", "Nearest_Campus",
                    "Km_to_Assigned", "Assigned_Name", "New_Name", "Duplicate", "Reason", "Geography_Suggests", "Confidence", "Override_Name"])
        for g in sorted(games, key=lambda g: (g["base"], g["season"], g["date"])):
            a = g["assigned"] or ""
            w.writerow([g["id"], g["season"], g["date"], g["side"], g["raw"], g["opp"], g["near"] or "",
                        f'{g["dist"][a]:.0f}' if a in g["dist"] else "", a,
                        "NEW" if a and a not in EXISTING else "", "Y" if g["dup"] else "", g["why"], g["alt"], g["conf"], ""])

    summ = defaultdict(lambda: dict(n=0, dups=0, opps=Counter(), conf=None, share=0))
    for g in games:
        s = summ[(g["base"], g["season"], g["assigned"] or "?")]
        s["n"] += 1; s["dups"] += 1 if g["dup"] else 0; s["opps"][g["opp"]] += 1; s["conf"] = g["conf"]; s["share"] = g["share"]
    with open("ambiguous_split_seasons.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Bare_Name", "Season", "Assigned_Name", "New_Name", "Games", "Duplicates", "Season_Agreement",
                    "Confidence", "Opponents", "Override_Name"])
        for (b, se, a), s in sorted(summ.items()):
            w.writerow([b, se, a, "NEW" if a not in EXISTING else "", s["n"], s["dups"], f'{s["share"]:.0%}',
                        s["conf"], "; ".join(o for o, _ in s["opps"].most_common(8)), ""])

    tot = Counter((g["base"], g["assigned"] or "?") for g in games)
    print(f"{len(games)} games, {len(summ)} name/season rows")
    for (b, a), n in sorted(tot.items()):
        print(f"  {b:11s} -> {a:20s} {n:4d}{'  NEW' if a not in EXISTING else ''}")
    print("confidence by game:", Counter(g["conf"] for g in games))
    print("duplicates of coded-name games:", sum(1 for g in games if g["dup"]))


if __name__ == "__main__":
    main()
