# export_scores_loren_maxwell.py
# Exports HS_Scores to CSV files for Loren Maxwell (hsfha.org)
#
# Files produced:
#   FL-2026-05.csv  -- FL games added after 2025-12-31
#   LA-2026-05.csv  -- LA games added after 2025-12-31
#   LA-1975-1979.csv -- ALL LA games seasons 1975-1979 (no date filter)
#
# All files include Home_ID and Visitor_ID joined from HS_Team_Names.

import pyodbc
import pandas as pd
import os
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
SERVER   = r"McKnights-PC\SQLEXPRESS01"
DATABASE = "hs_football_database"
DRIVER   = "ODBC Driver 17 for SQL Server"

OUTPUT_DIR = r"J:\Users\demck\Google Drive\Shared_Loren_Maxwell"

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
)

# ==========================================
# SQL QUERIES
# Home_ID / Visitor_ID: LEFT JOIN to HS_Team_Names on Team_Name.
# Using LEFT JOIN so rows with unmatched names still export (ID = NULL).
# State extraction: SUBSTRING(RIGHT(RTRIM(col), 4), 2, 2)
# ==========================================

# --- Query A: State + Date_Added filter (FL-2026-05, LA-2026-05) ---
SQL_STATE_DATE = """
SELECT
     s.[ID]
    ,s.[Season]
    ,s.[Date]
    ,s.[Home]
    ,hn.[ID]  AS [Home_ID]
    ,s.[Home_Score]
    ,s.[Visitor]
    ,vn.[ID]  AS [Visitor_ID]
    ,s.[Visitor_Score]
    ,s.[Margin]
    ,s.[Neutral]
    ,s.[Location]
    ,s.[Location2]
    ,s.[Source]
    ,s.[Date_Added]
    ,s.[OT]
    ,s.[Forfeit]
FROM [hs_football_database].[dbo].[HS_Scores] s
LEFT JOIN [hs_football_database].[dbo].[HS_Team_Names] hn
    ON hn.[Team_Name] = s.[Home]
LEFT JOIN [hs_football_database].[dbo].[HS_Team_Names] vn
    ON vn.[Team_Name] = s.[Visitor]
WHERE
    s.[Date_Added] > '2025-12-31'
    AND (
        SUBSTRING(RIGHT(RTRIM(s.[Home]),    4), 2, 2) = ?
     OR SUBSTRING(RIGHT(RTRIM(s.[Visitor]), 4), 2, 2) = ?
    )
ORDER BY s.[Season], s.[Date_Added], s.[ID];
"""

# --- Query B: State + Season range filter, no date_added filter (LA-1975-1979) ---
SQL_STATE_SEASONS = """
SELECT
     s.[ID]
    ,s.[Season]
    ,s.[Date]
    ,s.[Home]
    ,hn.[ID]  AS [Home_ID]
    ,s.[Home_Score]
    ,s.[Visitor]
    ,vn.[ID]  AS [Visitor_ID]
    ,s.[Visitor_Score]
    ,s.[Margin]
    ,s.[Neutral]
    ,s.[Location]
    ,s.[Location2]
    ,s.[Source]
    ,s.[Date_Added]
    ,s.[OT]
    ,s.[Forfeit]
FROM [hs_football_database].[dbo].[HS_Scores] s
LEFT JOIN [hs_football_database].[dbo].[HS_Team_Names] hn
    ON hn.[Team_Name] = s.[Home]
LEFT JOIN [hs_football_database].[dbo].[HS_Team_Names] vn
    ON vn.[Team_Name] = s.[Visitor]
WHERE
    s.[Season] BETWEEN ? AND ?
    AND (
        SUBSTRING(RIGHT(RTRIM(s.[Home]),    4), 2, 2) = ?
     OR SUBSTRING(RIGHT(RTRIM(s.[Visitor]), 4), 2, 2) = ?
    )
ORDER BY s.[Season], s.[Date], s.[ID];
"""

# ==========================================
# EXPORT JOBS
# Each dict defines one output file.
#   query     : which SQL template to use
#   params    : positional params for that query
#   state     : label for console output
#   filename  : output CSV name
# ==========================================
EXPORT_JOBS = [
    {
        "label":    "FL 2026 additions",
        "filename": "FL-2026-05.csv",
        "query":    SQL_STATE_DATE,
        "params":   ["FL", "FL"],
    },
    {
        "label":    "LA 2026 additions",
        "filename": "LA-2026-05.csv",
        "query":    SQL_STATE_DATE,
        "params":   ["LA", "LA"],
    },
    {
        "label":    "LA 1975-1979 (all data)",
        "filename": "LA-1975-1979.csv",
        "query":    SQL_STATE_SEASONS,
        "params":   [1975, 1979, "LA", "LA"],
    },
]

# ==========================================
# MAIN
# ==========================================
def run_export(conn, job):
    """Execute one export job and write its CSV. Returns row count."""
    df = pd.read_sql(job["query"], conn, params=job["params"])
    output_path = os.path.join(OUTPUT_DIR, job["filename"])
    df.to_csv(output_path, index=False)
    return df, output_path


def main():
    print("=" * 60)
    print("Loren Maxwell Score Export")
    print(f"Output directory : {OUTPUT_DIR}")
    print(f"Run time         : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    print("\nConnecting to SQL Server...")
    try:
        conn = pyodbc.connect(CONN_STR, timeout=30)
        print("Connected.\n")
    except Exception as e:
        print(f"ERROR: Could not connect to SQL Server: {e}")
        return

    for job in EXPORT_JOBS:
        print(f"--- {job['label']} ---")
        print(f"  Running query...")

        try:
            df, output_path = run_export(conn, job)
            row_count = len(df)
            print(f"  Rows returned    : {row_count:,}")

            if row_count == 0:
                print(f"  WARNING: No rows found. CSV written with headers only.")
            else:
                # Null ID summary (helps flag unmatched team names)
                null_home    = df["Home_ID"].isna().sum()
                null_visitor = df["Visitor_ID"].isna().sum()
                if null_home or null_visitor:
                    print(f"  Home_ID nulls    : {null_home:,}  (team name not in HS_Team_Names)")
                    print(f"  Visitor_ID nulls : {null_visitor:,}  (team name not in HS_Team_Names)")

                # Per-season row counts
                season_counts = df.groupby("Season").size()
                print("  Rows by season:")
                for season, cnt in season_counts.items():
                    print(f"    {season}: {cnt:,}")

            print(f"  Saved            : {output_path}")

        except Exception as e:
            print(f"  ERROR: {e}")

        print()

    conn.close()
    print("All exports complete. Connection closed.")


if __name__ == "__main__":
    main()