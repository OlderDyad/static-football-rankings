"""Generate Import_Ontario_2026.sql from ontario/ontario_2026_games_raw.csv.
Every source name is mapped explicitly (MAP, keyed by source association + name), because Ontario
names repeat across cities (St. Joseph's, Holy Cross, Catholic Central...). NEW marks a school
with no HS_Scores name yet. Rebuild the raw CSV first: cd ontario; python build_ontario_2026.py"""
import csv
NEW = "NEW:"
MAP = {
 "WECSSAA": {"Belle River": "Lakeshore Belle River (ON)", "Brennan": "Windsor F. J. Brennan Catholic (ON)",
   "Cardinal Carter": NEW + "Leamington Cardinal Carter (ON)", "Catholic Central": "Windsor Catholic Central (ON)",
   "Essex": "Essex (ON)", "Herman": "Windsor W. F. Herman (ON)", "Holy Names": "Windsor Holy Names (ON)",
   "Kennedy": "Windsor W. C. Kennedy (ON)", "L'Essor": "Tecumseh ecole secondaire catholique l'Essor (ON)",
   "Massey": "Windsor Vincent Massey (ON)", "North Star": NEW + "Amherstburg North Star (ON)",
   "Riverside": "Windsor Riverside (ON)", "Sandwich": "LaSalle Sandwich (ON)", "St. Anne": "Lakeshore St. Anne Catholic (ON)",
   "St. Joseph's": "Windsor St. Joseph Catholic (ON)", "Tecumseh Vista Academy": "Tecumseh Vista Academy (ON)",
   "Villanova": "LaSalle St. Thomas of Villanova (ON)"},
 "LKSSAA": {"Northern": "Sarnia Northern (ON)", "St. Pat's": "Sarnia St. Patrick's (ON)",
   "Ursuline College": "Chatham Ursuline College The Pines (ON)"},
 "TVRA": {"A.B. Lucas S.S.": "London A. B. Lucas (ON)", "Catholic Central H.S.": "London Catholic Central (ON)",
   "Clarke Road S.S.": "London Clarke Road (ON)", "College Avenue S.S.": "Woodstock College Avenue (ON)",
   "East Elgin S.S.": "Aylmer East Elgin (ON)", "Glendale H.S.": "Tillsonburg Glendale (ON)",
   "H.B. Beal S.S.": "London H.B. Beal (ON)", "Ingersoll D.C.I.": "Ingersoll (ON)", "Medway H.S.": "Arva Medway (ON)",
   "Montcalm S.S.": "London Montcalm (ON)", "Mother Teresa C.H.S.": "London Mother Teresa Catholic (ON)",
   "Oakridge S.S.": "London Oakridge (ON)", "Parkside C.I.": "St. Thomas Parkside (ON)",
   "Regina Mundi C.H.S.": "London Regina Mundi (ON)", "Saunders S.S.": "London Saunders (ON)",
   "Sir Frederick Banting S.S.": "London Sir Frederick Banting (ON)", "Sir Wilfrid Laurier S.S.": "London Sir Wilfrid Laurier (ON)",
   "South C.I.": "London South (ON)", "St. Andre Bessette": "London St. Andre Bessette Catholic (ON)",
   "St. Joseph's C.H.S.": "Saint Thomas St. Joseph's (ON)", "St. Thomas Aquinas C.S.S.": "London St. Thomas Aquinas Catholic (ON)",
   "Strathroy D.C.I.": "Strathroy (ON)", "Westminster S.S.": "London Westminster (ON)"},
 "HWDSB_Hamilton": {"Ancaster HS": "Hamilton Ancaster (ON)", "Bernie Custis SS": NEW + "Hamilton Bernie Custis (ON)",
   "Dundas Valley SS": "Dundas Valley (ON)", "Glendale SS": "Hamilton Glendale (ON)",
   "Nora Frances Henderson SS": "Hamilton Nora Henderson (ON)", "Saltfleet DHS": "Hamilton Saltfleet (ON)",
   "Sherwood SS": "Hamilton Sherwood (ON)", "Sir Allan MacNab SS": "Hamilton Sir Allan Macnab (ON)",
   "Sir Winston Churchill SS": "Hamilton Sir Winston Churchill (ON)", "Waterdown DHS": "Waterdown (ON)",
   "Westdale SS": "Hamilton Westdale (ON)", "Westmount SS": "Hamilton Westmount (ON)"},
 "KASSAA": {"Bayridge SS": "Kingston Bayridge (ON)", "Frontenac SS": "Kingston Frontenac (ON)",
   "Holy Cross CSS": "Kingston Holy Cross (ON)", "LaSalle SS": "Kingston La Salle (ON)",
   "Regiopolis-Notre Dame CHS": "Kingston Regiopolis-Notre Dame Catholic (ON)", "Sydenham HS": "Sydenham (ON)"},
 "SDSSAA": {"Confederation": "Valley East Confederation (ON)", "Lively": "Lively Walden (ON)",
   "Lo-Ellen": "Sudbury Lo-Ellen Park (ON)", "Lockerby": "Sudbury Lockerby (ON)",
   "St Benedict": "Sudbury St. Benedict Catholic (ON)", "St Charles": "Sudbury St. Charles (ON)"},
 "COSSA": {"Adam Scott": "Peterborough Adam Scott (ON)", "Crestwood": "Peterborough Crestwood (ON)",
   "Fenelon Falls": "Kawartha Lakes Fenelon Falls (ON)", "Holy Cross": "Peterborough Holy Cross (ON)",
   "Thomas A Stewart": "Peterborough Thomas A. Stewart (ON)"},
 "WCSSAA": {"BCI": "Waterloo Bluevale (ON)", "CHCI": "Kitchener Cameron Heights (ON)", "EDSS": "Elmira Waterloo District (ON)",
   "GCI": "Cambridge Galt (ON)", "GRCI": "Kitchener Grand River (ON)", "HHSS": "Kitchener Huron Heights (ON)",
   "JHSS": "Cambridge Jacob Hespeler (ON)", "KCI": NEW + "Kitchener-Waterloo Collegiate (ON)",
   "LHSS": NEW + "Waterloo Laurel Heights (ON)", "PHS": "Cambridge Preston (ON)", "WCI": "Waterloo (ON)",
   "WODSS": "Baden Waterloo-Oxford (ON)"},
}
rows = list(csv.DictReader(open("ontario/ontario_2026_games_raw.csv", encoding="utf-8")))
missing = sorted({(r["Source"], r[k]) for r in rows for k in ("Home", "Visitor") if r[k] not in MAP.get(r["Source"], {})})
assert not missing, f"UNMAPPED: {missing}"
strip = lambda n: n[len(NEW):] if n.startswith(NEW) else n
games, seen, dup = [], set(), 0
for r in rows:
    h, v = MAP[r["Source"]][r["Home"]], MAP[r["Source"]][r["Visitor"]]
    key = (r["Date"], frozenset((strip(h), strip(v))))
    if key in seen: dup += 1; continue
    seen.add(key); games.append((r["Date"], h, v, int(r["Home_Score"]), int(r["Visitor_Score"]), r["Source"]))
q = lambda s: "N'" + s.replace("'", "''") + "'"
names = sorted({x for g in games for x in g[1:3]}, key=strip)
L = ["USE [hs_football_database];", "SET NOCOUNT ON;",
     f"-- Ontario 2026 import: {len(games)} games from WECSSAA, LKSSAA, TVRA, HWDSB, KASSAA, SDSSAA, COSSA, WCSSAA.",
     "-- Generated by canada_2026\\generate_import_ontario_2026.py. Safe to re-run (date + team pair guard).", "",
     "IF OBJECT_ID('tempdb..#t') IS NOT NULL DROP TABLE #t;",
     "CREATE TABLE #t (DbName nvarchar(200) PRIMARY KEY, IsNew bit, Found int NULL);",
     "INSERT INTO #t (DbName, IsNew) VALUES",
     ",\n".join(f"  ({q(strip(n))}, {1 if n.startswith(NEW) else 0})" for n in names) + ";",
     "UPDATE t SET Found = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.DbName OR s.Visitor = t.DbName) FROM #t t;",
     "SELECT DbName, IsNew, Found FROM #t ORDER BY DbName;",
     "IF EXISTS (SELECT 1 FROM #t WHERE IsNew = 0 AND Found = 0)",
     "BEGIN",
     "    SELECT 'NOT IMPORTED - existing name not found' AS Problem, DbName FROM #t WHERE IsNew = 0 AND Found = 0;",
     "    RAISERROR('Team name problem -- nothing was inserted.', 16, 1);",
     "    SET NOEXEC ON;",
     "END", "",
     "IF OBJECT_ID('tempdb..#g') IS NOT NULL DROP TABLE #g;",
     "CREATE TABLE #g ([Date] date, Home nvarchar(200), Visitor nvarchar(200), HS int, VS int, Src varchar(30));",
     "INSERT INTO #g VALUES",
     ",\n".join(f"  ('{d}', {q(strip(h))}, {q(strip(v))}, {hs}, {vs}, '{s}')" for d, h, v, hs, vs, s in games) + ";", "",
     "BEGIN TRAN;",
     "INSERT INTO dbo.HS_Scores ([ID], [Season], [Date], [Home], [Visitor], [Home_Score], [Visitor_Score], [Margin], [OT], [Source], [Date_Added])",
     "SELECT NEWID(), 2026, g.[Date], g.Home, g.Visitor, g.HS, g.VS, g.HS - g.VS, 0, g.Src, GETDATE()",
     "FROM #g g",
     "WHERE NOT EXISTS (SELECT 1 FROM dbo.HS_Scores s WHERE s.Season = 2026 AND s.[Date] = g.[Date]",
     "                  AND ((s.Home = g.Home AND s.Visitor = g.Visitor) OR (s.Home = g.Visitor AND s.Visitor = g.Home)));",
     "PRINT CONCAT(@@ROWCOUNT, ' games inserted.');",
     "COMMIT;", "",
     "SELECT Src, COUNT(*) AS GamesInFile FROM #g GROUP BY Src;",
     "SET NOEXEC OFF;"]
open("Import_Ontario_2026.sql", "w", encoding="utf-8-sig", newline="\r\n").write("\n".join(L) + "\n")
from collections import Counter
print(f"{len(games)} games, {len(names)} teams, {dup} duplicates dropped"); print(Counter(g[5] for g in games))
print("NEW:", [strip(n) for n in names if n.startswith(NEW)])
