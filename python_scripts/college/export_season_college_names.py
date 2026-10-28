"""
export_season_college_names.py -- read-only. Lists every team that has games in College_Scores for the
given seasons, with its College_Team_Names row (Kind, State, HS_Team_Name link). Used to match newspaper
names to the exact Team_Name each season's games are stored under (Wolfe/Access names change by era,
and the 2026-10 collision splits renamed some).

Usage:  python export_season_college_names.py 1907 1908 1909 1950 1952 1971
Output: newspaper_split/college_names_by_season.csv
"""
import csv, os, sys
import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "newspaper_split", "college_names_by_season.csv")

seasons = [int(s) for s in sys.argv[1:]]
if not seasons:
    sys.exit("Give one or more seasons, e.g. 1908 1950 1971")
cur = pyodbc.connect(CONN).cursor()
marks = ",".join("?" * len(seasons))
rows = cur.execute(f"""
    WITH g AS (SELECT Season, Home AS Team FROM dbo.College_Scores WHERE Season IN ({marks})
               UNION ALL
               SELECT Season, Visitor FROM dbo.College_Scores WHERE Season IN ({marks}))
    SELECT g.Season, g.Team, COUNT(*) AS Games, t.Kind, t.State, t.HS_Team_Name
    FROM g LEFT JOIN dbo.College_Team_Names t ON t.Team_Name = g.Team
    GROUP BY g.Season, g.Team, t.Kind, t.State, t.HS_Team_Name
    ORDER BY g.Season, g.Team""", *seasons, *seasons).fetchall()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Season", "Team_Name", "Games", "Kind", "State", "HS_Team_Name"])
    w.writerows([list(r) for r in rows])
names = cur.execute("SELECT Team_Name, Kind, State, HS_Team_Name FROM dbo.College_Team_Names").fetchall()
with open(os.path.join(HERE, "newspaper_split", "college_team_names_current.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Team_Name", "Kind", "State", "HS_Team_Name"])
    w.writerows([list(r) for r in names])
print(f"{len(rows):,} team-seasons written to {OUT}; {len(names):,} College_Team_Names rows to college_team_names_current.csv")
