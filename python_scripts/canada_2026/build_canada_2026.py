"""Build 2026 game lists for New Brunswick (Gridiron NB) and Quebec (RSEQ D1/D2 juvenile).

Refresh the source files (from this folder) and re-run:
  curl -sL https://gridironnewbrunswick.org/highschoolsched.php -o nb_2026_highschoolsched.html
  curl -sL "https://s1.rseq.ca/api/LeagueApi/GetLeagueDiffusion/?leagueId=e3e61ac3-6c2c-4987-ac8e-78e587ebe919" -o rseq_juv_d1.json
  curl -sL "https://s1.rseq.ca/api/LeagueApi/GetLeagueDiffusion/?leagueId=277af8d7-1a53-4bb3-bd94-4432be324894" -o rseq_juv_d2.json
  python build_canada_2026.py

Writes canada_2026_games_raw.csv (source team names, before mapping to DB names).
"""
import csv, html, json, re, sys
from datetime import datetime

SEASON = 2026
rows = []

# ---- New Brunswick ----------------------------------------------------------
s = open("nb_2026_highschoolsched.html", encoding="utf-8", errors="replace").read()
division = ""
for m in re.finditer(r"<tr class='(division|data)'>(.*?)</tr>", s, flags=re.S):
    kind, body = m.group(1), m.group(2)
    if kind == "division":
        division = re.sub("<[^>]+>", "", body).strip()
        continue
    tds = re.findall(r"<td[^>]*>(.*?)</td>", body, flags=re.S)
    if len(tds) < 3 or "BYE" in body:
        continue
    def team_score(cell):
        sc = re.search(r"<b>(\d+)</b>", cell)
        name = html.unescape(re.sub("<[^>]+>", "", cell.split("<font")[0]))
        return re.sub(r"\s+", " ", name).strip(), (int(sc.group(1)) if sc else None)
    away, ascore = team_score(tds[1])
    home, hscore = team_score(tds[2])
    d = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", tds[0]))).split(",", 1)[-1].replace(".", "").strip()
    date = datetime.strptime(f"{d} {SEASON}", "%b %d %Y").strftime("%Y-%m-%d")
    if ascore is None or hscore is None:
        continue
    rows.append(dict(Prov="NB", Source="GridironNB", Level=("9-man" if "9" in division else "12-man"),
                     Division=division, Date=date, Home=home, Visitor=away,
                     Home_Score=hscore, Visitor_Score=ascore, Neutral=0, Note=""))

# ---- Quebec (RSEQ) ----------------------------------------------------------
for tag in ("d1", "d2"):
    d = json.load(open(f"rseq_juv_{tag}.json", encoding="utf-8-sig"))
    for sec in ("PreSeasonGames", "RegularSeasonGames", "PostSeasonGames", "ChampionshipGames",
                "ConferenceChampionshipGames"):
        for g in d.get(sec) or []:
            if g.get("IsDeleted") or g.get("IsCancelledAfterTeamWithdraw") or not g.get("GameResultFormatted"):
                continue
            forfeit = g.get("IsVisitingTeamForfeit") or g.get("IsHomeTeamForfeit")
            home = g["HomeTeamName"] or g["FakeHomeTeamName"]
            vis = g["VisitingTeamName"] or g["FakeVisitingTeamName"]
            rows.append(dict(Prov="QC", Source="RSEQ", Level=f"Juv {tag.upper()}",
                             Division=f"{d['LeagueName']} {sec.replace('Games','')}",
                             Date=g["GameDateText"], Home=home, Visitor=vis,
                             Home_Score=g["HomeTeamScore"], Visitor_Score=g["VisitingTeamScore"],
                             Neutral=1 if sec != "RegularSeasonGames" and "Bol" in (g.get("Description") or "") else 0,
                             Note=("FORFEIT " if forfeit else "") + (g.get("Description") or "")))

with open("canada_2026_games_raw.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

from collections import Counter
print(Counter((r["Prov"], r["Level"]) for r in rows))
print("teams:", {p: len({r[k] for r in rows if r["Prov"] == p for k in ("Home", "Visitor")}) for p in ("NB", "QC")})
print("dates:", min(r["Date"] for r in rows), "to", max(r["Date"] for r in rows))
print("forfeits/notes:", [(r["Date"], r["Visitor"], r["Home"], r["Note"]) for r in rows if r["Note"]])
