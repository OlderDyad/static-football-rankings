"""Combine 2026 BC, AB, SK (Regina + Saskatoon) and MB games into west_2026_games_raw.csv.
Refresh sources first:  bash fetch_bc.sh ; then the curl lines in README section of this folder."""
import csv
from collections import Counter
from parse_bc import parse_bc
from parse_ab import parse_ab
from parse_sk_regina import parse_regina
from parse_sk_saskatoon import parse_saskatoon
from parse_mb import parse_mb
rows = []
for f in (parse_bc, parse_ab, parse_regina, parse_saskatoon, parse_mb):
    o, _ = f(); rows += o
with open("west_2026_games_raw.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows)); print(Counter((r["Prov"], r["Source"], r["Level"]) for r in rows))
names = sorted({(r["Prov"], r[k]) for r in rows for k in ("Home", "Visitor")})
with open("west_2026_team_names.txt", "w", encoding="utf-8") as fh:
    for p, n in names: fh.write(f"{p}\t{n}\n")
print(len(names), "distinct source names -> west_2026_team_names.txt")
