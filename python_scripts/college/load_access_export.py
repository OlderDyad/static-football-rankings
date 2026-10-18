"""
load_access_export.py
=====================
Loads the CSVs exported from the college Access database (CFB 2023_09_03.accdb)
into SQL Server staging/reference tables. Safe to re-run: each table is
emptied and reloaded, so a newer Access export simply replaces the old one.

    access_export/access_scores.csv             -> dbo.College_Scores_Staging
    access_export/access_division_alignment.csv -> dbo.College_Division_Alignment
    access_export/access_coaches.csv            -> dbo.College_Coach_Tenures
    access_export/access_rankings.csv           -> dbo.College_Rankings_Access
    name_fixes/college_name_fixes.csv           -> dbo.College_Name_Fixes
    name_fixes/college_team_aliases.csv         -> dbo.College_Team_Aliases
    name_fixes/college_dup_actions.csv          -> dbo.College_Dup_Actions
    name_fixes/college_team_names.csv           -> dbo.College_Team_Names
    name_fixes/college_coach_seasons_ids.csv    -> dbo.College_Coach_Seasons (with Coach_ID)
    name_fixes/college_coaches.csv              -> dbo.College_Coaches
        (reloading renumbers Team_ID -- fine until other tables reference it)

College_Rankings_Access keeps the Access-calculated ratings as a reference
baseline, separate from College_Rankings (which the SQL rating procedure
will write), so the two can be compared.

Nothing here touches dbo.College_Scores or dbo.College_Rankings; moving
staging rows into College_Scores is a separate, reviewed step.

Usage (from this folder):
    python load_access_export.py                 # every table whose CSV exists
    python load_access_export.py scores coaches  # only these (scores, divisions, coaches, rankings, namefixes, aliases, dupactions, teamnames, coachseasons, coaches)
Each table is committed separately.
"""

import csv
import os
import sys
from datetime import datetime

import pyodbc

CONN = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)
HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "access_export")

DDL = [
    """IF OBJECT_ID('dbo.College_Scores_Staging','U') IS NULL
       CREATE TABLE dbo.College_Scores_Staging (
           Access_ID      INT          NOT NULL PRIMARY KEY,
           Game_Date      DATE         NULL,
           Season         INT          NULL,
           Visitor_Score  INT          NULL,
           Home_Score     INT          NULL,
           Margin         INT          NULL,
           Neutral        BIT          NULL,
           Line           FLOAT        NULL,
           Future_Game    BIT          NULL,
           Visitor        VARCHAR(111) NULL,
           Home           VARCHAR(111) NULL,
           Location       VARCHAR(111) NULL,
           Location2      VARCHAR(255) NULL,
           Loaded_At      DATETIME     NOT NULL DEFAULT GETDATE()
       )""",
    """IF OBJECT_ID('dbo.College_Division_Alignment','U') IS NULL
       CREATE TABLE dbo.College_Division_Alignment (
           Access_ID  INT           NOT NULL PRIMARY KEY,
           YearStart  INT           NULL,
           YearEnd    INT           NULL,
           School     VARCHAR(111)  NULL,
           Division   VARCHAR(100)  NULL
       )""",
    """IF OBJECT_ID('dbo.College_Coach_Tenures','U') IS NULL
       CREATE TABLE dbo.College_Coach_Tenures (
           Access_ID   INT           NOT NULL PRIMARY KEY,
           Year_Start  INT           NULL,
           Year_End    INT           NULL,
           Date_Start  DATE          NULL,
           Date_End    DATE          NULL,
           Years       INT           NULL,
           Games       INT           NULL,
           Wins        INT           NULL,
           Losses      INT           NULL,
           Ties        INT           NULL,
           Win_Pct     FLOAT         NULL,
           School      VARCHAR(111)  NULL,
           Coach       NVARCHAR(200) NULL
       )""",
    """IF OBJECT_ID('dbo.College_Rankings_Access','U') IS NULL
       CREATE TABLE dbo.College_Rankings_Access (
           Row_ID                                       INT IDENTITY(1,1) PRIMARY KEY,
           Season                                       INT           NULL,
           Week                                         INT           NULL,
           Home                                         NVARCHAR(120) NULL,
           Avg_Of_Avg_Of_Home_Modified_Score            FLOAT NULL,
           Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss   FLOAT NULL,
           Avg_Of_Avg_Of_Home_Modified_Log_Score        FLOAT NULL,
           Max_Min_Margin                               FLOAT NULL,
           Max_Performance                              FLOAT NULL,
           Min_Performance                              FLOAT NULL,
           Offense                                      FLOAT NULL,
           Defense                                      FLOAT NULL,
           Best_Worst_Win_Loss                          FLOAT NULL,
           Season_Home                                  NVARCHAR(142) NULL
       )""",
    """IF OBJECT_ID('dbo.College_Name_Fixes','U') IS NULL
       CREATE TABLE dbo.College_Name_Fixes (
           Access_ID     INT          NOT NULL,
           Side          VARCHAR(7)   NOT NULL,     -- Home / Visitor
           Old_Name      VARCHAR(111) NULL,
           New_Name      VARCHAR(111) NOT NULL,
           Fix_Type      VARCHAR(20)  NOT NULL,     -- whitespace_case / merge / split
           Is_Duplicate  BIT          NOT NULL,
           CONSTRAINT PK_College_Name_Fixes PRIMARY KEY (Access_ID, Side)
       )""",
    """IF OBJECT_ID('dbo.College_Team_Aliases','U') IS NULL
       CREATE TABLE dbo.College_Team_Aliases (
           Alias_Name      VARCHAR(111) NOT NULL PRIMARY KEY,
           Canonical_Name  VARCHAR(111) NOT NULL,
           Reason          VARCHAR(255) NULL,
           Date_Added      DATETIME     NOT NULL DEFAULT GETDATE()
       )""",
    """IF OBJECT_ID('dbo.College_Dup_Actions','U') IS NULL
       CREATE TABLE dbo.College_Dup_Actions (
           Access_ID       INT          NOT NULL PRIMARY KEY,
           Action          VARCHAR(20)  NOT NULL,   -- MOVE / FLAG_DISPUTED
           Kept_Access_ID  INT          NULL,
           Review_Group    VARCHAR(20)  NULL,
           Reason          VARCHAR(255) NULL
       )""",
    """IF OBJECT_ID('dbo.College_Team_Names','U') IS NULL
       CREATE TABLE dbo.College_Team_Names (
           Team_ID             INT IDENTITY(1,1) PRIMARY KEY,
           Team_Name           VARCHAR(111)  NOT NULL UNIQUE,
           Kind                VARCHAR(20)   NULL,     -- College / HS/Prep / Club / Military / JC / Academy / Freshmen
           State               VARCHAR(2)    NULL,
           State_Source        VARCHAR(50)   NULL,
           First_Season        INT           NULL,
           Last_Season         INT           NULL,
           Games               INT           NULL,
           Latest_Division     VARCHAR(100)  NULL,
           Division_History    VARCHAR(500)  NULL,
           Latitude            FLOAT         NULL,
           Longitude           FLOAT         NULL,
           HS_Team_ID          INT           NULL,     -- dbo.HS_Team_Names.ID
           HS_Team_Name        VARCHAR(111)  NULL,     -- name as used in HS_Scores (some have no HS_Team_Names row)
           HS_Link_Confidence  VARCHAR(20)   NULL,
           Date_Added          DATETIME      NOT NULL DEFAULT GETDATE()
       )""",
    """IF OBJECT_ID('dbo.College_Coach_Seasons','U') IS NULL
       CREATE TABLE dbo.College_Coach_Seasons (
           Row_ID      INT IDENTITY(1,1) PRIMARY KEY,
           Team_Name   VARCHAR(111)  NOT NULL,
           Season      INT           NOT NULL,
           Coach       NVARCHAR(200) NOT NULL,
           Role        VARCHAR(20)   NULL,      -- Head / Interim
           Source      VARCHAR(40)   NULL,      -- Access / Wikipedia history / Wikipedia current / manual
           Agreement   VARCHAR(120)  NULL,      -- agree / n/a / DISAGREE (Access: ...)
           Date_Added  DATETIME      NOT NULL DEFAULT GETDATE()
       )""",
    "IF COL_LENGTH('dbo.College_Coach_Seasons', 'Coach_ID') IS NULL ALTER TABLE dbo.College_Coach_Seasons ADD Coach_ID INT NULL",
    """IF OBJECT_ID('dbo.College_Coaches','U') IS NULL
       CREATE TABLE dbo.College_Coaches (
           Coach_ID       INT            NOT NULL PRIMARY KEY,
           Coach_Name     NVARCHAR(200)  NOT NULL,
           Name_Variants  NVARCHAR(1000) NULL,
           Teams          NVARCHAR(2000) NULL,
           First_Season   INT            NULL,
           Last_Season    INT            NULL,
           Seasons        INT            NULL
       )""",
]


def num(v, cast=int):
    v = (v or "").strip()
    if v == "":
        return None
    return cast(float(v)) if cast is int else cast(v)


def bit(v):
    v = (v or "").strip().lower()
    return None if v == "" else (1 if v in ("true", "1", "-1", "yes") else 0)


def day(v):
    v = (v or "").strip()
    if not v or v.startswith("("):
        return None
    return datetime.strptime(v[:10], "%Y-%m-%d").date()


def text(v, n):
    v = (v or "").strip()
    return v[:n] if v else None


def load(cur, table, path, convert, insert_sql):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [convert(r) for r in csv.DictReader(fh)]
    cur.execute(f"TRUNCATE TABLE dbo.{table}")
    cur.fast_executemany = True
    for i in range(0, len(rows), 20000):
        cur.executemany(insert_sql, rows[i:i + 20000])
    n = cur.execute(f"SELECT COUNT(*) FROM dbo.{table}").fetchone()[0]
    print(f"{table}: {len(rows):,} rows read, {n:,} in table")
    return len(rows) == n


def flt(v):
    return num(v, float)


TABLES = {
    "scores": (
        "College_Scores_Staging", "access_scores.csv",
        lambda r: (num(r["ID"]), day(r["Date"]), num(r["Season"]),
                   num(r["Visitor Score"]), num(r["Home Score"]), num(r["Margin"]),
                   bit(r["Nuetral"]), flt(r["Line"]), bit(r["Future Game"]),
                   text(r["Visitor"], 111), text(r["Home"], 111),
                   text(r["Location"], 111), text(r["Location2"], 255)),
        "INSERT INTO dbo.College_Scores_Staging (Access_ID, Game_Date, Season, Visitor_Score, "
        "Home_Score, Margin, Neutral, Line, Future_Game, Visitor, Home, Location, Location2) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"),
    "divisions": (
        "College_Division_Alignment", "access_division_alignment.csv",
        lambda r: (num(r["ID"]), num(r["YearStart"]), num(r["YearEnd"]),
                   text(r["School"], 111), text(r["Division"], 100)),
        "INSERT INTO dbo.College_Division_Alignment (Access_ID, YearStart, YearEnd, School, Division) "
        "VALUES (?,?,?,?,?)"),
    "coaches": (
        "College_Coach_Tenures", "access_coaches.csv",
        lambda r: (num(r["ID"]), num(r["Year_ Start"]), num(r["Year_ End"]),
                   day(r["Date Start"]), day(r["Date End"]), num(r["Years"]), num(r["Games"]),
                   num(r["Wins"]), num(r["Losses"]), num(r["Ties"]), flt(r["Percent"]),
                   text(r["School"], 111), text(r["Coach"], 200)),
        "INSERT INTO dbo.College_Coach_Tenures (Access_ID, Year_Start, Year_End, Date_Start, Date_End, "
        "Years, Games, Wins, Losses, Ties, Win_Pct, School, Coach) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"),
    "rankings": (
        "College_Rankings_Access", "access_rankings.csv",
        lambda r: (num(r["Season"]), num(r["Week"]), text(r["Home"], 120),
                   flt(r["Avg Of Avg Of Home Modified Score"]),
                   flt(r["Avg Of Avg Of Home Modified Score Win-Loss"]),
                   flt(r["Avg Of Avg Of Home Modified Log Score"]),
                   flt(r["Max - Min Margin"]), flt(r["Max Performance"]), flt(r["Min Performance"]),
                   flt(r["Offense"]), flt(r["Defense"]), flt(r["Best-Worst Win-Loss"]),
                   text(r["SeasonHome"], 142)),
        "INSERT INTO dbo.College_Rankings_Access (Season, Week, Home, "
        "Avg_Of_Avg_Of_Home_Modified_Score, Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, "
        "Avg_Of_Avg_Of_Home_Modified_Log_Score, Max_Min_Margin, Max_Performance, Min_Performance, "
        "Offense, Defense, Best_Worst_Win_Loss, Season_Home) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"),
    "namefixes": (
        "College_Name_Fixes", os.path.join("..", "name_fixes", "college_name_fixes.csv"),
        lambda r: (num(r["Access_ID"]), r["Side"], text(r["Old_Name"], 111), text(r["New_Name"], 111),
                   r["Fix_Type"], int(r["Is_Duplicate"])),
        "INSERT INTO dbo.College_Name_Fixes (Access_ID, Side, Old_Name, New_Name, Fix_Type, Is_Duplicate) "
        "VALUES (?,?,?,?,?,?)"),
    "aliases": (
        "College_Team_Aliases", os.path.join("..", "name_fixes", "college_team_aliases.csv"),
        lambda r: (text(r["Alias_Name"], 111), text(r["Canonical_Name"], 111), text(r["Reason"], 255)),
        "INSERT INTO dbo.College_Team_Aliases (Alias_Name, Canonical_Name, Reason) VALUES (?,?,?)"),
    "dupactions": (
        "College_Dup_Actions", os.path.join("..", "name_fixes", "college_dup_actions.csv"),
        lambda r: (num(r["Access_ID"]), r["Action"], num(r["Kept_Access_ID"]), r["Review_Group"],
                   text(r["Reason"], 255)),
        "INSERT INTO dbo.College_Dup_Actions (Access_ID, Action, Kept_Access_ID, Review_Group, Reason) "
        "VALUES (?,?,?,?,?)"),
    "teamnames": (
        "College_Team_Names", os.path.join("..", "name_fixes", "college_team_names.csv"),
        lambda r: (text(r["Team_Name"], 111), text(r["Kind"], 20), text(r["State"], 2), text(r["State_Source"], 50),
                   num(r["First_Season"]), num(r["Last_Season"]), num(r["Games"]),
                   text(r["Latest_Division"], 100), text(r["Division_History"], 500),
                   flt(r["Latitude"]), flt(r["Longitude"]), num(r["HS_Team_ID"]),
                   text(r["HS_Team_Name"], 111), text(r["HS_Link_Confidence"], 20)),
        "INSERT INTO dbo.College_Team_Names (Team_Name, Kind, State, State_Source, First_Season, Last_Season, "
        "Games, Latest_Division, Division_History, Latitude, Longitude, HS_Team_ID, HS_Team_Name, "
        "HS_Link_Confidence) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"),
    "coachseasons": (
        "College_Coach_Seasons", os.path.join("..", "name_fixes", "college_coach_seasons_ids.csv"),
        lambda r: (text(r["Team_Name"], 111), num(r["Season"]), text(r["Coach"], 200), text(r["Role"], 20),
                   text(r["Source"], 40), text(r["Agreement"], 120), num(r["Coach_ID"])),
        "INSERT INTO dbo.College_Coach_Seasons (Team_Name, Season, Coach, Role, Source, Agreement, Coach_ID) "
        "VALUES (?,?,?,?,?,?,?)"),
    "coaches": (
        "College_Coaches", os.path.join("..", "name_fixes", "college_coaches.csv"),
        lambda r: (num(r["Coach_ID"]), text(r["Coach_Name"], 200), text(r["Name_Variants"], 1000),
                   text(r["Teams"], 2000), num(r["First"]), num(r["Last"]), num(r["Seasons"])),
        "INSERT INTO dbo.College_Coaches (Coach_ID, Coach_Name, Name_Variants, Teams, First_Season, Last_Season, Seasons) "
        "VALUES (?,?,?,?,?,?,?)"),
}


def main():
    wanted = [a.lower() for a in sys.argv[1:]] or list(TABLES)
    bad = [w for w in wanted if w not in TABLES]
    if bad:
        print(f"Unknown table(s): {bad}. Choose from {list(TABLES)}")
        sys.exit(1)
    conn = pyodbc.connect(CONN, autocommit=False)
    cur = conn.cursor()
    failed = False
    try:
        for s in DDL:
            cur.execute(s)
        conn.commit()
        for key in wanted:
            table, fname, convert, sql = TABLES[key]
            path = os.path.join(EXPORT, fname)
            if not os.path.exists(path):
                print(f"{table}: skipped ({fname} not found)")
                continue
            try:
                if load(cur, table, path, convert, sql):
                    conn.commit()
                    print(f"  committed {table}")
                else:
                    conn.rollback()
                    failed = True
                    print(f"  row counts differ -- {table} rolled back, unchanged")
            except Exception as e:
                conn.rollback()
                failed = True
                print(f"  ERROR loading {table}, rolled back: {e}")
    finally:
        conn.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
