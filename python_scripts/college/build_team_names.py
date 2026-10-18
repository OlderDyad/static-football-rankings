"""
build_team_names.py -> name_fixes/college_team_names.csv  (load file for dbo.College_Team_Names)

Combines college_team_profile.csv with college_hs_match_review.csv.
HS link: Your_HS_Team_ID if filled (0 = no link; a non-numeric value = an HS_Scores
name with no HS_Team_Names record), otherwise the proposal (high or check).
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
prof = list(csv.DictReader(open(os.path.join(HERE, "name_fixes", "college_team_profile.csv"), encoding="utf-8")))
match = {r["College_Team"]: r for r in csv.DictReader(open(os.path.join(HERE, "college_hs_match_review.csv"), encoding="utf-8"))}

out = []
for p in prof:
    m = match.get(p["Team_Name"], {})
    mine = (m.get("Your_HS_Team_ID") or "").strip()
    hs_id, hs_name, conf = "", "", ""
    if mine == "0":
        conf = "none (reviewed)"
    elif mine.isdigit():
        hs_id, conf = mine, "reviewed"
    elif mine:
        hs_name, conf = mine, "reviewed"
    elif m.get("Confidence"):
        pid = m["Proposed_HS_Team_ID"]
        hs_id = pid if pid.isdigit() else ""
        hs_name, conf = m["Proposed_HS_Team_Name"], m["Confidence"]
    out.append([p["Team_Name"], p["Kind"], p["State"], p["State_Source"], p["First_Season"], p["Last_Season"],
                p["Games"], p["Latest_Division"], p["Division_Years"], p["Latitude"], p["Longitude"],
                hs_id, hs_name, conf])

with open(os.path.join(HERE, "name_fixes", "college_team_names.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["Team_Name", "Kind", "State", "State_Source", "First_Season", "Last_Season", "Games",
                "Latest_Division", "Division_History", "Latitude", "Longitude",
                "HS_Team_ID", "HS_Team_Name", "HS_Link_Confidence"])
    w.writerows(out)
print(len(out), "teams;", sum(1 for r in out if r[11] or r[12]), "with HS link;",
      sum(1 for r in out if r[12] and not r[11]), "linked by name only")
print("max lengths:", max(len(r[0]) for r in out), max(len(r[8]) for r in out), max(len(r[12]) for r in out))
