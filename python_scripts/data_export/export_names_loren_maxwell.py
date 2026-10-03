# export_names_loren_maxwell.py
# Exports HS_Team_Names to CSV for Loren Maxwell (hsfha.org) -- companion
# to export_scores_loren_maxwell.py. Same per-state subfolder convention
# under OUTPUT_BASE_DIR. Full team-metadata table (city, mascot, colors,
# stadium, coordinates, etc.) for every team whose State column matches,
# so his team can join it against the Scores export's Home_ID/Visitor_ID
# columns.

import pyodbc
import pandas as pd
import os
from datetime import datetime

SERVER   = r"McKnights-PC\SQLEXPRESS01"
DATABASE = "hs_football_database"
DRIVER   = "ODBC Driver 17 for SQL Server"

OUTPUT_BASE_DIR = r"J:\Users\demck\Google Drive\Shared_Loren_Maxwell"

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
)

SQL_STATE_NAMES = """
SELECT
     [ID]
    ,[Team_Name]
    ,[City]
    ,[State]
    ,[Mascot]
    ,[PrimaryColor]
    ,[SecondaryColor]
    ,[TertiaryColor]
    ,[Stadium]
    ,[YearFounded]
    ,[Website]
    ,[LogoURL]
    ,[School_Logo_URL]
    ,[PhotoUrl]
    ,[Latitude]
    ,[Longitude]
    ,[Has_Team_Page]
    ,[Team_Page_URL]
    ,[LastUpdated]
FROM [hs_football_database].[dbo].[HS_Team_Names]
WHERE [State] = ?
ORDER BY [Team_Name];
"""

EXPORT_JOBS = [
    {
        "label":     "OK Team Names (full)",
        "subfolder": "Oklahoma",
        "filename":  "OK-Team-Names.csv",
        "params":    ["OK"],
    },
    {
        "label":     "LA Team Names (full)",
        "subfolder": "Louisiana",
        "filename":  "LA-Team-Names.csv",
        "params":    ["LA"],
    },
]


def run_export(conn, job):
    df = pd.read_sql(SQL_STATE_NAMES, conn, params=job["params"])
    out_dir = os.path.join(OUTPUT_BASE_DIR, job.get("subfolder", ""))
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        print(f"  Created subfolder: {out_dir}")
    output_path = os.path.join(out_dir, job["filename"])
    df.to_csv(output_path, index=False)
    return df, output_path


def main():
    print("=" * 60)
    print("Loren Maxwell Team Names Export")
    print(f"Output base dir  : {OUTPUT_BASE_DIR}")
    print(f"Run time         : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not os.path.exists(OUTPUT_BASE_DIR):
        os.makedirs(OUTPUT_BASE_DIR)
        print(f"Created output directory: {OUTPUT_BASE_DIR}")

    print("\nConnecting to SQL Server...")
    try:
        conn = pyodbc.connect(CONN_STR, timeout=30)
        print("Connected.\n")
    except Exception as e:
        print(f"ERROR: Could not connect to SQL Server: {e}")
        return

    for job in EXPORT_JOBS:
        print(f"--- {job['label']} ---")
        try:
            df, output_path = run_export(conn, job)
            print(f"  Rows returned : {len(df):,}")
            missing_meta = df[['LogoURL', 'PrimaryColor', 'Website']].isna().any(axis=1).sum()
            if missing_meta:
                print(f"  Note: {missing_meta:,} team(s) missing one or more of LogoURL/PrimaryColor/Website "
                      f"(fine to share as-is -- just incomplete metadata, not a data error).")
            print(f"  Saved         : {output_path}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()

    conn.close()
    print("All exports complete. Connection closed.")


if __name__ == "__main__":
    main()
