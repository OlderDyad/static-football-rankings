"""
build_dup_actions.py -- turns duplicate_review.csv into name_fixes/college_dup_actions.csv

Decisions (2026-10-15):
  A  same date/teams/score                -> keep proposed copy, move the rest
  B  bad-score copy (0-0 / 1-2 marker)   -> keep the good copy, move the bad one
  B  real score conflict                 -> keep OLDEST Access_ID, move the rest,
                                            flag the kept game Score_Disputed = 1
  C  Aug-1 date, same score              -> keep proposed copy, move the rest
  C  Aug-1 date, different scores        -> keep all (two real games)
  D  same score, dates <= 7 days apart   -> keep oldest Access_ID, move the other
  E  team vs itself                      -> move out of staging (held for repair)
A non-blank Your_Action column (KEEP / MOVE) in duplicate_review.csv overrides.
"""
import csv, os
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))

rows = list(csv.DictReader(open(os.path.join(HERE, "duplicate_review.csv"), encoding="utf-8")))
groups = defaultdict(list)
for r in rows:
    groups[r["Group"]].append(r)

REASON = {"A": "Same date, teams and score (entered twice)",
          "Bbad": "Same game; this copy has 0-0 or a 1/2 win-marker score",
          "B": "Same game, score conflict: kept oldest Access_ID, flagged Score_Disputed",
          "C": "Date unknown (Aug 1), same teams and score (entered twice)",
          "D": "Same season, teams and score, dates within 7 days (date typo)",
          "E": "Team listed as playing itself -- held for repair"}

out = []
for g, m in groups.items():
    cls = m[0]["Class"]
    oldest = min(m, key=lambda r: int(r["Access_ID"]))
    for r in m:
        mine = (r["Your_Action"] or "").strip().upper()
        act, reason, disputed = r["Proposed_Action"], REASON.get(cls, ""), 0
        if cls == "B" and r["Proposed_Action"] in ("KEEP", "MOVE"):
            reason = REASON["Bbad"] if act == "MOVE" else ""
        elif cls in ("B", "D") and act == "REVIEW":
            act = "KEEP" if r is oldest else "MOVE"
            disputed = 1 if (cls == "B" and act == "KEEP") else 0
        elif cls == "E":
            act = "MOVE"
        if mine in ("KEEP", "MOVE"):
            act = mine
        kept = next((x for x in m if x is not r and ((x["Proposed_Action"] == "KEEP") or
                                                       (x is oldest and cls in ("B", "D")))), None)
        if act == "MOVE":
            out.append([r["Access_ID"], "MOVE", kept["Access_ID"] if kept and cls != "E" else "", g, reason])
        elif disputed:
            out.append([r["Access_ID"], "FLAG_DISPUTED", "", g, reason])

# A team-vs-itself game (E) can also sit in a B/A group; the E decision wins.
self_ids = {r[0] for r in out if r[3].startswith("E")}
out = [r for r in out if r[0] not in self_ids or r[3].startswith("E")]

with open(os.path.join(HERE, "name_fixes", "college_dup_actions.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["Access_ID", "Action", "Kept_Access_ID", "Review_Group", "Reason"])
    w.writerows(out)
print(Counter((r[1], r[3][0]) for r in out))
print("total MOVE:", sum(1 for r in out if r[1] == "MOVE"), " FLAG_DISPUTED:", sum(1 for r in out if r[1] == "FLAG_DISPUTED"))
