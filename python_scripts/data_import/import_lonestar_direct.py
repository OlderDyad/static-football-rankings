#!/usr/bin/env python3
"""
LoneStar Direct Import - Simplified Workflow
=============================================

Imports raw LoneStar data directly to SQL, bypassing Excel formula step.
SQL will handle all team name standardization via alias tables.

Input format (your current Excel):
A: team_id | B: team_name | C: season | D: WK | E: Team1 | F: SC1 | G: Team2 | H: SC2
"""

import pandas as pd
import pyodbc
from datetime import datetime, timedelta
import re

# ============================================================================
# CONFIGURATION  
# ============================================================================

EXCEL_FILE = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HSF Texas 2025_teams_1-720_v1.xlsx"
SHEET_NAME = "Lonestar"

DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=McKnights-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

STARTING_WEEK = 35  # Texas seasons start at week 35

# ============================================================================
# MAIN IMPORT
# ============================================================================

def main():
    print("="*80)
    print("LoneStar Direct Import to SQL")
    print("="*80)
    print()
    
    # Load Excel
    print(f"Loading: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
    print(f"✓ Loaded {len(df)} rows")
    print()
    
    # Connect to database
    print("Connecting to database...")
    conn = pyodbc.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    print("✓ Connected")
    print()
    
    # Get next batch ID
    cursor.execute("SELECT ISNULL(MAX(BatchID), 0) + 1 FROM HS_Scores_LoneStar_Staging")
    batch_id = cursor.fetchone()[0]
    print(f"Using Batch ID: {batch_id}")
    print()
    
    # Process each row
    print("Importing games...")
    imported = 0
    errors = 0
    
    last_season = None
    current_week = STARTING_WEEK - 1
    
    for idx, row in df.iterrows():
        try:
            team_id = int(row.iloc[0])  # A: team_id
            team_name = str(row.iloc[1])  # B: team_name
            season = int(row.iloc[2])  # C: season
            wk_str = str(row.iloc[3]) if not pd.isna(row.iloc[3]) else ''  # D: WK
            team1_raw = str(row.iloc[4])  # E: Team1
            score1 = int(row.iloc[5])  # F: SC1
            team2_raw = str(row.iloc[6])  # G: Team2
            score2 = int(row.iloc[7])  # H: SC2
            
            # Skip invalid rows
            if pd.isna(row.iloc[4]) or pd.isna(row.iloc[6]):
                continue
            
            # Calculate week number (sequential within season)
            if season != last_season:
                current_week = STARTING_WEEK
                last_season = season
            else:
                current_week += 1
            
            # Estimate date (September 1 + week offset)
            # Week 35 = early September, increment by 7 days per week
            base_date = datetime(season, 9, 1)
            estimated_date = base_date + timedelta(days=(current_week - STARTING_WEEK) * 7)
            
            # Determine home/visitor based on team_name
            # Simple rule: if our team name appears in team1, we're team1 (home)
            base_name = team_name.split('(')[0].strip()
            
            # Clean team names for comparison (remove junk prefixes/suffixes)
            team1_clean = re.sub(r'^[0-9LPTF#*@xn]+', '', team1_raw)
            team1_clean = re.sub(r'[a-z$#*@]+$', '', team1_clean).strip()
            
            team2_clean = re.sub(r'^[0-9LPTF#*@xn]+', '', team2_raw)
            team2_clean = re.sub(r'[a-z$#*@]+$', '', team2_clean).strip()
            
            # Determine home/visitor
            if base_name.lower() in team1_clean.lower():
                # We're team1 (home)
                home = f"{team_name}"
                visitor = team2_raw  # Keep raw for alias lookup
                home_score = score1
                visitor_score = score2
            else:
                # We're team2 (home)
                home = f"{team_name}"
                visitor = team1_raw  # Keep raw for alias lookup
                home_score = score2
                visitor_score = score1
            
            # Detect forfeits
            forfeit = 1 if ((home_score == 1 and visitor_score == 0) or 
                           (home_score == 0 and visitor_score == 1)) else 0
            
            # Calculate margin
            margin = home_score - visitor_score
            
            # Source
            source = f"LoneStar Team {team_id}"
            
            # Insert to staging
            sql = """
                INSERT INTO HS_Scores_LoneStar_Staging (
                    Date, Season, Home, Visitor, Neutral, Location, Location2,
                    Source, Forfeit, Visitor_Score, Home_Score, Margin, BatchID
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(sql, 
                estimated_date, season, home, visitor, 0, None, None,
                source, forfeit, visitor_score, home_score, margin, batch_id
            )
            
            imported += 1
            
            if imported % 1000 == 0:
                print(f"  Imported {imported} games...")
                conn.commit()
            
        except Exception as e:
            print(f"  ERROR on row {idx}: {e}")
            errors += 1
            if errors > 100:
                print("Too many errors, stopping")
                break
    
    # Final commit
    conn.commit()
    
    print()
    print("="*80)
    print("IMPORT COMPLETE")
    print("="*80)
    print(f"Batch ID: {batch_id}")
    print(f"Imported: {imported} games")
    print(f"Errors: {errors}")
    print()
    print("NEXT STEP:")
    print(f"Run in SQL: EXEC dbo.sp_Import_LoneStar_Batch @BatchID = {batch_id};")
    print("="*80)
    
    conn.close()

if __name__ == "__main__":
    main()