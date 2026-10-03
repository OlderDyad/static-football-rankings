# export_investigation_report_loren_maxwell.py
# Exports the FULL HS_Mapping_Investigations queue (open + resolved) to CSV
# for Loren Maxwell (hsfha.org) -- companion to export_scores_loren_maxwell.py
# and export_names_loren_maxwell.py. Same per-state subfolder convention.
#
# Deliberately includes BOTH open and closed investigations, not just the
# open ones: a closed "Verified-FalsePositive"/"Fixed" row is real, useful
# context (shows what's already been checked and ruled out, so his team
# doesn't waste time re-deriving something we've already resolved), and a
# still-open "New" row is exactly what's worth digging into. One export
# row per (Investigation x linked game) pair -- flat/joined, not nested --
# so it opens cleanly as a spreadsheet.

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

# One row per linked game -- if an investigation has no linked games at all
# (shouldn't normally happen, but LEFT JOIN just in case), it still appears
# once with null game columns rather than silently dropping out.
SQL_STATE_INVESTIGATIONS = """
SELECT
     i.[InvestigationID]
    ,i.[AnchorTeam]
    ,i.[State]
    ,i.[Season]
    ,i.[ConflictType]
    ,i.[Priority]
    ,i.[Status]
    ,i.[ProposedCorrection]
    ,i.[Notes]
    ,i.[FixedDate]
    ,s.[ID]             AS [ScoresID]
    ,s.[Date]
    ,s.[Home]
    ,s.[Home_Score]
    ,s.[Visitor]
    ,s.[Visitor_Score]
    ,s.[Source]
FROM [hs_football_database].[dbo].[HS_Mapping_Investigations] i
LEFT JOIN [hs_football_database].[dbo].[HS_Mapping_Investigation_Games] g
    ON g.[InvestigationID] = i.[InvestigationID]
LEFT JOIN [hs_football_database].[dbo].[HS_Scores] s
    ON s.[ID] = g.[ScoresID]
WHERE i.[State] = ?
ORDER BY i.[ConflictType], i.[Status], i.[InvestigationID], s.[Date];
"""

EXPORT_JOBS = [
    {
        "label":     "OK Investigation Queue (open + resolved)",
        "subfolder": "Oklahoma",
        "filename":  "OK-Investigation-Queue.csv",
        # HS_Mapping_Investigations.State is stored as '(OK)', not 'OK' --
        # same convention mapping_conflict_audit.py's normalize_state() handles.
        "params":    ["(OK)"],
    },
    {
        "label":     "LA Investigation Queue (open + resolved)",
        "subfolder": "Louisiana",
        "filename":  "LA-Investigation-Queue.csv",
        "params":    ["(LA)"],
    },
]


def run_export(conn, job):
    df = pd.read_sql(SQL_STATE_INVESTIGATIONS, conn, params=job["params"])
    out_dir = os.path.join(OUTPUT_BASE_DIR, job.get("subfolder", ""))
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        print(f"  Created subfolder: {out_dir}")
    output_path = os.path.join(out_dir, job["filename"])
    df.to_csv(output_path, index=False)
    return df, output_path


def main():
    print("=" * 60)
    print("Loren Maxwell Investigation Queue Export")
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
            print(f"  Rows returned      : {len(df):,}")
            inv_count = df['InvestigationID'].nunique()
            print(f"  Distinct investigations : {inv_count:,}")
            print("  By Status:")
            for status, cnt in df.drop_duplicates('InvestigationID')['Status'].value_counts().items():
                print(f"    {status}: {cnt:,}")
            print("  By ConflictType:")
            for ctype, cnt in df.drop_duplicates('InvestigationID')['ConflictType'].value_counts().items():
                print(f"    {ctype}: {cnt:,}")
            print(f"  Saved              : {output_path}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()

    conn.close()
    print("All exports complete. Connection closed.")


if __name__ == "__main__":
    main()
