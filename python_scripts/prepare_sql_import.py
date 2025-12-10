import pandas as pd
import sys
from datetime import datetime

def prepare_for_sql_import(csv_file):
    """
    Prepare scraped data for SQL Server import
    - Format dates properly
    - Create proper team names with state/province
    - Generate GameID format
    - Split into teams and games tables
    """
    print(f"🗄️  Preparing data for SQL Server import")
    print(f"📁 Input: {csv_file}")
    print("="*60)
    
    df = pd.read_csv(csv_file)
    
    # --- PREPARE TEAMS TABLE ---
    print("\n1️⃣  Creating Teams Table...")
    
    all_teams = set()
    team_data = []
    
    for _, row in df.iterrows():
        for team in [row['Host'], row['Opponent']]:
            if pd.notna(team) and team not in all_teams:
                all_teams.add(team)
                
                # Extract state/province if present
                state = ""
                team_name = team
                
                if '(' in team and ')' in team:
                    parts = team.rsplit('(', 1)
                    team_name = parts[0].strip()
                    state = parts[1].replace(')', '').strip()
                
                # Determine level
                level = "Varsity"
                if "JV" in team_name:
                    level = "JV"
                    team_name = team_name.replace(" JV", "").strip()
                elif "Freshman" in team_name:
                    level = "Freshman"
                    team_name = team_name.replace(" Freshman", "").strip()
                
                team_data.append({
                    'TeamName': team_name,
                    'State': state,
                    'Level': level,
                    'FullName': team,
                    'Source': 'ScoreStream',
                    'ScrapedDate': datetime.now().strftime('%Y-%m-%d')
                })
    
    teams_df = pd.DataFrame(team_data)
    teams_file = "sql_import_teams.csv"
    teams_df.to_csv(teams_file, index=False)
    print(f"   ✅ Teams table: {teams_file} ({len(teams_df)} teams)")
    
    # --- PREPARE GAMES TABLE ---
    print("\n2️⃣  Creating Games Table...")
    
    games_data = []
    
    for idx, row in df.iterrows():
        # Parse date - ScoreStream format varies
        game_date = row['Date']
        
        # Try to parse date
        parsed_date = None
        try:
            # Try common formats
            for fmt in ['%b %d %Y', '%m/%d/%Y', '%Y-%m-%d', "%b %d '%y"]:
                try:
                    parsed_date = datetime.strptime(game_date, fmt)
                    break
                except:
                    continue
        except:
            pass
        
        if not parsed_date:
            # Use a default for unparseable dates
            parsed_date = datetime(2025, 1, 1)
        
        # Generate GameID (format: YYYYMMDD_TeamID_vs_TeamID)
        date_str = parsed_date.strftime('%Y%m%d')
        
        # Create simplified team identifiers for GameID
        host_id = row.get('Host', 'UNK')[:10].replace(' ', '').replace(',', '')
        opp_id = row.get('Opponent', 'UNK')[:10].replace(' ', '').replace(',', '')
        
        game_id = f"{date_str}_{host_id}_vs_{opp_id}_{row['Level']}"
        
        game_data = {
            'GameID': game_id,
            'GameDate': parsed_date.strftime('%Y-%m-%d'),
            'Season': parsed_date.year,
            'Week': parsed_date.isocalendar()[1],  # ISO week number
            'Level': row['Level'],
            'HomeTeam': row['Host'],
            'AwayTeam': row['Opponent'],
            'HomeScore': int(row['Score1']) if row['Score1'] and row['Score1'] != '' else None,
            'AwayScore': int(row['Score2']) if row['Score2'] and row['Score2'] != '' else None,
            'ScoreStreamLink': row['GameLink'],
            'OpponentTeamID': row.get('OpponentID', ''),
            'Source': 'ScoreStream',
            'ScrapedDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        games_data.append(game_data)
    
    games_df = pd.DataFrame(games_data)
    games_file = "sql_import_games.csv"
    games_df.to_csv(games_file, index=False)
    print(f"   ✅ Games table: {games_file} ({len(games_df)} games)")
    
    # --- SUMMARY STATS ---
    print(f"\n📊 IMPORT READY DATA SUMMARY")
    print(f"   Teams: {len(teams_df)}")
    print(f"   Games: {len(games_df)}")
    print(f"   Season(s): {', '.join(map(str, sorted(games_df['Season'].unique())))}")
    print(f"   Levels: {', '.join(games_df['Level'].unique())}")
    
    # Games with scores
    scored_games = games_df[(games_df['HomeScore'].notna()) & (games_df['AwayScore'].notna())]
    print(f"\n   Games with scores: {len(scored_games)}/{len(games_df)} ({len(scored_games)/len(games_df)*100:.1f}%)")
    
    # --- CREATE SQL IMPORT SCRIPT ---
    print(f"\n3️⃣  Creating SQL Import Script...")
    
    sql_script = f"""-- ScoreStream Data Import Script
-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Teams: {len(teams_df)} | Games: {len(games_df)}

-- Step 1: Create temporary staging tables
IF OBJECT_ID('tempdb..#ScoreStream_Teams') IS NOT NULL DROP TABLE #ScoreStream_Teams;
IF OBJECT_ID('tempdb..#ScoreStream_Games') IS NOT NULL DROP TABLE #ScoreStream_Games;

CREATE TABLE #ScoreStream_Teams (
    TeamName NVARCHAR(200),
    State NVARCHAR(50),
    Level NVARCHAR(50),
    FullName NVARCHAR(250),
    Source NVARCHAR(50),
    ScrapedDate DATE
);

CREATE TABLE #ScoreStream_Games (
    GameID NVARCHAR(200),
    GameDate DATE,
    Season INT,
    Week INT,
    Level NVARCHAR(50),
    HomeTeam NVARCHAR(250),
    AwayTeam NVARCHAR(250),
    HomeScore INT,
    AwayScore INT,
    ScoreStreamLink NVARCHAR(500),
    OpponentTeamID NVARCHAR(50),
    Source NVARCHAR(50),
    ScrapedDate DATETIME
);

-- Step 2: Use BULK INSERT to load CSV files
-- Note: Update the file paths to match your system

BULK INSERT #ScoreStream_Teams
FROM 'C:\\path\\to\\{teams_file}'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\\n',
    TABLOCK
);

BULK INSERT #ScoreStream_Games
FROM 'C:\\path\\to\\{games_file}'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\\n',
    TABLOCK
);

-- Step 3: Verify data loaded
SELECT 'Teams loaded' AS Stage, COUNT(*) AS RecordCount FROM #ScoreStream_Teams;
SELECT 'Games loaded' AS Stage, COUNT(*) AS RecordCount FROM #ScoreStream_Games;

-- Step 4: Insert into your actual tables
-- Example - adjust table/column names to match your schema:

-- Insert teams (avoid duplicates)
INSERT INTO dbo.HS_Team_Names (TeamName, State, Level, Source, DateAdded)
SELECT DISTINCT 
    TeamName, 
    State, 
    Level, 
    Source, 
    GETDATE()
FROM #ScoreStream_Teams t
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.HS_Team_Names h 
    WHERE h.TeamName = t.TeamName AND h.State = t.State AND h.Level = t.Level
);

-- Insert games (avoid duplicates)
INSERT INTO dbo.HS_Scores (
    GameID, GameDate, Season, Week, Level,
    HomeTeam, AwayTeam, HomeScore, AwayScore,
    Source, DateAdded
)
SELECT 
    GameID, GameDate, Season, Week, Level,
    HomeTeam, AwayTeam, HomeScore, AwayScore,
    Source, GETDATE()
FROM #ScoreStream_Games g
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.HS_Scores h 
    WHERE h.GameID = g.GameID
);

-- Step 5: Summary
SELECT 'Import Complete' AS Status;
SELECT COUNT(*) AS NewTeams FROM dbo.HS_Team_Names WHERE DateAdded >= CAST(GETDATE() AS DATE);
SELECT COUNT(*) AS NewGames FROM dbo.HS_Scores WHERE DateAdded >= CAST(GETDATE() AS DATE);

-- Clean up
DROP TABLE #ScoreStream_Teams;
DROP TABLE #ScoreStream_Games;
"""
    
    sql_file = "import_scorestream_data.sql"
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(sql_script)
    
    print(f"   ✅ SQL script: {sql_file}")
    
    print(f"\n{'='*60}")
    print(f"✅ READY FOR SQL IMPORT")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"1. Review the CSV files:")
    print(f"   - {teams_file}")
    print(f"   - {games_file}")
    print(f"2. Edit {sql_file} to match your table schema")
    print(f"3. Update file paths in the SQL script")
    print(f"4. Run the SQL script in SSMS")
    
    return teams_df, games_df

def main():
    if len(sys.argv) < 2:
        print("Usage: python prepare_sql_import.py <csv_file>")
        print("\nExample: python prepare_sql_import.py cleaned_varsity.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    prepare_for_sql_import(csv_file)

if __name__ == "__main__":
    main()
