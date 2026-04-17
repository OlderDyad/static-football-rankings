# step 1 - pull and plot DLS streak performance
import pyodbc
import json
import os

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

SQL_RATINGS = """
SELECT Home, Season, [Avg_Of_Avg_Of_Home_Modified_Score] AS Margin_Rating
INTO #Ratings
FROM HS_Rankings
WHERE Week = 52
"""

SQL_DLS_GAMES = """
SELECT
    s.Date,
    s.Season,
    s.Home,
    s.Visitor,
    s.Home_Score,
    s.Visitor_Score,
    CASE WHEN s.Home LIKE '%Concord De La Salle (CA)%' THEN s.Margin ELSE -s.Margin END AS DLS_Margin,
    CASE WHEN s.Home LIKE 'Concord De La Salle (CA)%' THEN s.Visitor ELSE s.Home END AS Opponent,
    CAST(
        ((0.958 * rh.Margin_Rating + 2.791) + 
         (0.958 * rv.Margin_Rating + 2.791)) / 2.0 +
        CASE WHEN s.Home LIKE '%Concord De La Salle (CA)%' THEN s.Margin / 2.0 ELSE -s.Margin / 2.0 END
    AS DECIMAL(10,4)) AS Game_Performance,
    0.958 * rh.Margin_Rating + 2.791 AS DLS_Rating,
    0.958 * rv.Margin_Rating + 2.791 AS Opp_Rating
FROM HS_Scores s
INNER JOIN #Ratings rh ON rh.Home = s.Home AND rh.Season = s.Season
INNER JOIN #Ratings rv ON rv.Home = s.Visitor AND rv.Season = s.Season
WHERE (s.Home LIKE '%Concord De La Salle (CA)%' OR s.Visitor LIKE '%Concord De La Salle (CA)%')
AND s.Date BETWEEN '1992-09-11' AND '2004-09-04'
AND (s.Future_Game IS NULL OR s.Future_Game = 0)
AND (s.Forfeit IS NULL OR s.Forfeit = 0)
ORDER BY s.Date
"""

conn = pyodbc.connect(CONNECTION_STRING, timeout=30)
cursor = conn.cursor()

print("Building ratings temp table...")
cursor.execute("IF OBJECT_ID('tempdb..#Ratings') IS NOT NULL DROP TABLE #Ratings")
cursor.execute(SQL_RATINGS)

print("Pulling DLS streak games...")
cursor.execute(SQL_DLS_GAMES)
rows = cursor.fetchall()
cols = [c[0] for c in cursor.description]
conn.close()

games = [dict(zip(cols, r)) for r in rows]
print(f"Retrieved {len(games)} games")

# Output as JSON for inspection
for g in games:
    g['Date'] = str(g['Date'])
    g['Game_Performance'] = float(g['Game_Performance']) if g['Game_Performance'] else None
    g['DLS_Rating'] = float(g['DLS_Rating']) if g['DLS_Rating'] else None
    g['Opp_Rating'] = float(g['Opp_Rating']) if g['Opp_Rating'] else None
    g['DLS_Margin'] = int(g['DLS_Margin']) if g['DLS_Margin'] else None

# Print summary sorted by performance to spot outliers
print("\n--- Lowest 10 Game Performances ---")
sorted_games = sorted(games, key=lambda x: x['Game_Performance'] or 0)
for g in sorted_games[:10]:
    print(f"{g['Date']}  {g['Opponent']}  DLS_Margin:{g['DLS_Margin']:+d}  OppRating:{g['Opp_Rating']:.1f}  Perf:{g['Game_Performance']:.2f}")

# Add this to dls_streak_analysis.py after the lowest 10 section
games_sorted = sorted(games, key=lambda x: x['Game_Performance'] or 0)
perfs = [g['Game_Performance'] for g in games if g['Game_Performance']]
print(f"\n--- Benchmark Stats ---")
print(f"Total games: {len(perfs)}")
print(f"Min performance: {min(perfs):.2f}")
print(f"Avg performance: {sum(perfs)/len(perfs):.2f}")
print(f"Max performance: {max(perfs):.2f}")    

print("\n--- Full streak ---")
for i, g in enumerate(games, 1):
    print(f"{i:3d}  {g['Date']}  {g['Opponent'][:35]:35s}  Margin:{g['DLS_Margin']:+3d}  OppRating:{g['Opp_Rating']:6.1f}  Perf:{g['Game_Performance']:6.2f}")

# Save to JSON
with open('dls_streak_analysis.json', 'w') as f:
    json.dump(games, f, indent=2)
print("\nSaved to dls_streak_analysis.json")