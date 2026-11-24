"""Parse every *2026*.txt / hwdsb.txt in this folder (association viewScores pages copied as text)
into ontario_2026_games_raw.csv. Forfeits (1-0 scores or 'forfeit' in notes) are dropped."""
import csv, glob, os, re
from collections import Counter
from parse_wecssaa import parse_wecssaa
SRC = {"wecssaa": "WECSSAA", "lkssaa": "LKSSAA", "tvra": "TVRA", "cossa": "COSSA", "hwdsb": "HWDSB_Hamilton",
       "kassaa": "KASSAA", "sdssaa": "SDSSAA", "wcssaa": "WCSSAA"}
rows, forfeits = [], 0
for f in sorted(glob.glob("*.txt")):
    key = re.sub(r"[^a-z]", "", os.path.basename(f).lower().replace("2026", "").replace(".txt", ""))
    src = SRC.get(key, key.upper())
    games = parse_wecssaa(f, src)
    for g in games:
        if "forfeit" in g["Note"].lower() or {g["Home_Score"], g["Visitor_Score"]} == {0, 1}:
            forfeits += 1; continue
        rows.append(g)
    print(f"{f:22} {src:16} {len(games):4} games  {min(x['Date'] for x in games)} .. {max(x['Date'] for x in games)}  {Counter(x['Level'] for x in games)}")
with open("ontario_2026_games_raw.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "games kept,", forfeits, "forfeits dropped")
print(Counter(r["Note"] for r in rows).most_common(12))
