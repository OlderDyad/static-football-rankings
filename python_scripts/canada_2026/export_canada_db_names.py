"""Run on the PC (needs the database). Writes canada_db_names.csv: every team name in HS_Scores
ending in a Canadian province suffix (plus WA/MT/ND/MN/WY/ID for cross-border opponents),
with game counts and seasons, for mapping the 2026 imports."""
import csv, os, sys
import pyodbc
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
DB_CONNECTION_STRING = (f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};"
                        f"DATABASE={DATABASE_NAME};Trusted_Connection=yes;")
SQL = """
SELECT Name, COUNT(*) AS Games, MIN(Season) AS FirstSeason, MAX(Season) AS LastSeason
FROM (SELECT Home AS Name, Season FROM dbo.HS_Scores UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores) x
WHERE RIGHT(Name, 4) IN ('(BC)','(AB)','(SK)','(MB)','(ON)','(QC)','(NB)','(NS)','(PE)','(NL)')
GROUP BY Name ORDER BY RIGHT(Name, 4), Name;
"""
cn = pyodbc.connect(DB_CONNECTION_STRING)
rows = cn.cursor().execute(SQL).fetchall()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "canada_db_names.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["Name", "Games", "FirstSeason", "LastSeason"]); w.writerows([tuple(r) for r in rows])
print(f"Wrote {len(rows)} names to {out}")
