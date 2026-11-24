"""Generate Import_West_2026.sql (BC, AB, SK, MB) from west_2026_games_raw.csv.

Names: automatic best match against canada_db_names.csv (match_names.py), then the
OVERRIDES / CONTEXT tables below. Values are exact HS_Scores names; NEW marks a team
with no DB name yet. Skipped: JV games for BC/AB/SK (the DB has no JV teams there),
games vs US teams (MaxPreps carries those), and duplicates (same date + same two teams,
e.g. a Regina-Saskatoon game listed by both cities, or AAA-vs-AA listed in both BC leagues).
"""
import csv, re
from match_names import best

NEW = "NEW:"
OVERRIDES = {
    # ---- BC ----
    "Abbotsford": "Abbotsford (BC)", "Abbotsford AAA": "Abbotsford (BC)",
    "W.J. Mouat": "Abbotsford Mouat (BC)", "WJ Mouat AAA": "Abbotsford Mouat (BC)",
    "Mission AAA": "Mission Ecole Mission (BC)", "Chilliwack AAA": NEW + "Chilliwack (BC)",
    "Kalamalka/W.L.Seaton AA*": "Coldstream Kalamalka (BC)", "Seaton/Kalamalka AA*": "Coldstream Kalamalka (BC)",
    "Nanaimo District AAA": "Nanaimo (BC)", "Pleasant Valley AA": NEW + "Armstrong Pleasant Valley (BC)",
    "Spectrum AAA": "Saanich Spectrum (BC)", "Vancouver College": "Vancouver Collegiate (BC)",
    "Vancouver College AAA": "Vancouver Collegiate (BC)", "Vancouver College (BC)": "Vancouver Collegiate (BC)",
    "St. Roch (Toronto)": "Brampton St. Roch (ON)", "Notre Dame (Alberta)": "Calgary Notre Dame (AB)",
    # ---- AB ----
    "Bishop McNally": NEW + "Calgary Bishop McNally (AB)", "Bishop McNaly": NEW + "Calgary Bishop McNally (AB)",
    "Bishop O'Bryne": "Calgary Bishop O'Byrne (AB)", "Ermest Manning": "Calgary Ernest Manning (AB)",
    "Father Lacombe": NEW + "Calgary Father Lacombe (AB)", "Horseshoe Crossing": NEW + "Horseshoe Crossing (AB)",
    "Valleyview": NEW + "Valleyview (AB)", "J.C.S.": "Calgary Joane Cardinal-Schubert (AB)",
    "L.C.I.": "Lethbridge Collegiate Institute (AB)", "Lillian Osbore": "Edmonton Lillian Osborne (AB)",
    "W.H. Crosford": "Airdrie W.H. Croxford (AB)", "Stathcona": "Strathcona (AB)",
    "St. Francis Xavier": "Edmonton St. Xavier (AB)", "St. Jossph's": "Grande Prairie St. Joseph's Catholic (AB)",
    "Drayton Valley": "Drayton Valley Frank Maddock (AB)", "Frank Maddock": "Drayton Valley Frank Maddock (AB)",
    "Bishop Carroll": "Calgary Bishop Carroll (AB)", "McNally": "Edmonton McNally (AB)",
    "Medicine Hat": "Medicine Hat (AB)", "St. Albert": "Saint Albert (AB)",
    "St. Paul": "Saint Paul (AB)", "Lloydminster": "Lloydminster Comprehensive (AB)", "High Prairie": "High Prairie (AB)",
    "Cochrane": "Cochrane (AB)", "Camrose": "Camrose (AB)", "Notre Dame (RD)": "Red Deer Ecole Secondaire Notre Dame (AB)",
    "Notre Dame (CAL)": "Calgary Notre Dame (AB)", "Crescent Heights (CAL)": "Calgary Crescent Heights (AB)",
    "Crescent Heights (MH)": "Medicine Hat Crescent Heights (AB)", "Cres. Hgts. (MH)": "Medicine Hat Crescent Heights (AB)",
    "Crescent Heights": "Medicine Hat Crescent Heights (AB)",      # only game: vs Cardston (PSK)
    "St. Joseph": "Edmonton St. Joseph's (AB)", "Millwoods": "Edmonton Millwoods Christian (AB)",
    "Cranbrook (BC)": "Cranbrook Mt. Baker (BC)", "Nelson (ON)": "Burlington Nelson (ON)",
    "St. Joseph's (SK)": "St. Joseph (SK)", "Bishop Mahoney (SK)": "Saskatoon Bishop James Mahoney (SK)",
    # ---- SK ----
    "FWJ": "Regina F.W. Johnson Collegiate (SK)", "Regina F.W. Johnson": "Regina F.W. Johnson Collegiate (SK)",
    "WKC": "Regina Winston Knoll Collegiate (SK)", "Martin/Luther": "Regina Luther College (SK)",
    "Campbell": "Campbell (SK)", "Regina Campbell": "Campbell (SK)", "Regina Miller": "Regina Miller (SK)",
    "SWC": "SWC (SK)", "Thom": "Regina Thom (SK)",
    "Saskatoon Holy Cross": "Saskatoon Holy Cross (SK)", "Saskatoon Marion Graham": "Marion Graham (SK)",
    "Saskatoon St. Joseph": "St. Joseph (SK)", "Saskatoon St Joseph": "St. Joseph (SK)",
    "PA Carlton": "Prince Albert Carlton (SK)", "PA St. Mary": "Prince Albert St. Mary's (SK)",
    "North Battleford": "North Battleford (SK)",
    # ---- MB ----
    "Fort Frances Muskies": NEW + "Fort Frances (MB)", "Windsor Park Royals": NEW + "Winnipeg Windsor Park Collegiate (MB)",
    "Murdoch Mackay JV": NEW + "Winnipeg Murdoch MacKay JV (MB)", "St. Paul's Crusaders JV": NEW + "Winnipeg St. Paul's JV (MB)",
    "Vincent Massey Trojans": "Winnipeg Vincent Massey Collegiate (MB)", "Vincent Massey Vikings": "Brandon Vincent Massey (MB)",
    "Vincent Massey Trojans JV": "Winnipeg Vincent Massey Collegiate JV (MB)", "Vincent Massey Vikings JV": "Brandon Vincent Massey JV (MB)",
    "St. Paul's Crusaders": "Winnipeg St. Paul's AAA (MB)",
}
def context(prov, name, div):
    if name == "Centennial":
        return "Centennial (AB)" if prov == "AB" else None
    if prov == "AB" and name == "Notre Dame":
        return "Red Deer Ecole Secondaire Notre Dame (AB)" if div.startswith("CEN") else "Calgary Notre Dame (AB)"
    if prov == "AB" and name == "St. Joseph's":
        return "Grande Prairie St. Joseph's Catholic (AB)" if div[:3] in ("MPE", "WHE") else "Edmonton St. Joseph's (AB)"
    return None
US = re.compile(r"\((WY|WA|MT|ND|ID)\)$|^(Lynden Christian|Omak)$")
JV = re.compile(r"\bJV\b|\(JV\)|\(Jr\.\)")

def resolve(prov, name, div):
    c = context(prov, name, div)
    if c: return c
    if name in OVERRIDES: return OVERRIDES[name]
    m = re.search(r"\((SK|BC|AB|MB|ON|Alberta|Toronto)\)$", name)
    p = {"Alberta": "AB", "Toronto": "ON"}.get(m.group(1), m.group(1)) if m else prov
    cands = best(name, p, bool(JV.search(name)))
    if cands and cands[0][0] >= 1.0: return cands[0][3]
    return None

rows = list(csv.DictReader(open("west_2026_games_raw.csv", encoding="utf-8")))
games, skipped, unmapped, seen = [], {"JV (BC/AB/SK)": 0, "US opponent": 0, "duplicate": 0}, set(), set()
used = {}
for r in rows:
    if r["Prov"] in ("BC", "AB", "SK") and (r["Level"] == "JV" or JV.search(r["Home"]) or JV.search(r["Visitor"])):
        skipped["JV (BC/AB/SK)"] += 1; continue
    if US.search(r["Home"]) or US.search(r["Visitor"]):
        skipped["US opponent"] += 1; continue
    h, v = resolve(r["Prov"], r["Home"], r["Division"]), resolve(r["Prov"], r["Visitor"], r["Division"])
    if not h: unmapped.add((r["Prov"], r["Home"]))
    if not v: unmapped.add((r["Prov"], r["Visitor"]))
    if not (h and v): continue
    key = (r["Date"], frozenset((h, v)))
    if key in seen: skipped["duplicate"] += 1; continue
    seen.add(key)
    used[(r["Prov"], r["Home"])] = h; used[(r["Prov"], r["Visitor"])] = v
    games.append((r["Date"], h, v, int(r["Home_Score"]), int(r["Visitor_Score"]), r["Source"]))
assert not unmapped, f"UNMAPPED: {sorted(unmapped)}"

with open("west_2026_name_map.tsv", "w", encoding="utf-8") as f:
    for (p, s), d in sorted(used.items()): f.write(f"{p}\t{s}\t{d}\n")

q = lambda s: "N'" + s.replace("'", "''") + "'"
dbnames = sorted({x for g in games for x in g[1:3]})
L = ["USE [hs_football_database];", "SET NOCOUNT ON;",
     f"-- BC/AB/SK/MB 2026 import: {len(games)} games. Generated by canada_2026\\generate_import_west_2026.py.",
     "-- Safe to re-run: each game is skipped if that date + team pair is already in HS_Scores (either home/away order).", "",
     "IF OBJECT_ID('tempdb..#t') IS NOT NULL DROP TABLE #t;",
     "CREATE TABLE #t (DbName nvarchar(200) PRIMARY KEY, IsNew bit, Found int NULL);",
     "INSERT INTO #t (DbName, IsNew) VALUES"]
L.append(",\n".join(f"  ({q(n[len(NEW):] if n.startswith(NEW) else n)}, {1 if n.startswith(NEW) else 0})" for n in dbnames) + ";")
L += ["UPDATE t SET Found = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.DbName OR s.Visitor = t.DbName) FROM #t t;", "",
      "-- Review: existing teams should show Found > 0; NEW teams show 0",
      "SELECT DbName, IsNew, Found FROM #t ORDER BY RIGHT(DbName,4), DbName;", "",
      "IF EXISTS (SELECT 1 FROM #t WHERE IsNew = 0 AND Found = 0)",
      "BEGIN",
      "    SELECT 'NOT IMPORTED - existing name not found' AS Problem, DbName FROM #t WHERE IsNew = 0 AND Found = 0;",
      "    RAISERROR('Team name problem -- nothing was inserted.', 16, 1);",
      "    SET NOEXEC ON;",
      "END", "",
      "IF OBJECT_ID('tempdb..#g') IS NOT NULL DROP TABLE #g;",
      "CREATE TABLE #g ([Date] date, Home nvarchar(200), Visitor nvarchar(200), HS int, VS int, Src varchar(30));"]
strip = lambda n: n[len(NEW):] if n.startswith(NEW) else n
for i in range(0, len(games), 500):
    L.append("INSERT INTO #g VALUES")
    L.append(",\n".join(f"  ('{d}', {q(strip(h))}, {q(strip(v))}, {hs}, {vs}, '{s}')" for d, h, v, hs, vs, s in games[i:i+500]) + ";")
L += ["",
      "BEGIN TRAN;",
      "INSERT INTO dbo.HS_Scores ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added])",
      "SELECT NEWID(), 2026, g.[Date], g.Home, g.Visitor, g.HS, g.VS, g.HS - g.VS, 0, g.Src, GETDATE()",
      "FROM #g g",
      "WHERE NOT EXISTS (SELECT 1 FROM dbo.HS_Scores s WHERE s.Season = 2026 AND s.[Date] = g.[Date]",
      "                  AND ((s.Home = g.Home AND s.Visitor = g.Visitor) OR (s.Home = g.Visitor AND s.Visitor = g.Home)));",
      "PRINT CONCAT(@@ROWCOUNT, ' games inserted.');",
      "COMMIT;", "",
      "SELECT Src, COUNT(*) AS GamesInFile FROM #g GROUP BY Src;",
      "SELECT Source, COUNT(*) AS Games2026InDb FROM dbo.HS_Scores WHERE Season = 2026",
      "  AND Source IN ('BC_HS_Football','FootballAlberta','RHSAA_Regina','SSSAD_Saskatoon','WHSFL_Manitoba') GROUP BY Source;",
      "SET NOEXEC OFF;"]
open("Import_West_2026.sql", "w", encoding="utf-8-sig", newline="\r\n").write("\n".join(L) + "\n")
from collections import Counter
print(f"{len(games)} games, {len(dbnames)} teams ({sum(n.startswith(NEW) for n in dbnames)} new)  skipped: {skipped}")
print(Counter(g[5] for g in games))
print("NEW:", [n[len(NEW):] for n in dbnames if n.startswith(NEW)])
