"""
Check LoneStar Scraping Status
Shows what's been scraped and what batches exist
"""

import pyodbc

DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=McKnights-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

def main():
    conn = pyodbc.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    
    print("="*80)
    print("LONESTAR SCRAPING STATUS")
    print("="*80)
    print()
    
    # Check scraping batches
    print("📦 SCRAPING BATCHES:")
    print("-"*80)
    cursor.execute("""
        SELECT 
            batch_id,
            start_team_id,
            end_team_id,
            teams_to_process,
            teams_processed,
            status,
            CONVERT(varchar, start_time, 120) as start_time
        FROM scraping_batches
        ORDER BY batch_id;
    """)
    
    batches = cursor.fetchall()
    for batch in batches:
        print(f"Batch {batch.batch_id}:")
        print(f"  Team Range: {batch.start_team_id} - {batch.end_team_id}")
        print(f"  Progress: {batch.teams_processed}/{batch.teams_to_process} teams")
        print(f"  Status: {batch.status}")
        print(f"  Started: {batch.start_time}")
        print()
    
    # Check staging table stats
    print("📊 STAGING TABLE (HS_Scores_LoneStar_Staging):")
    print("-"*80)
    cursor.execute("""
        SELECT 
            BatchID,
            COUNT(DISTINCT team_id) as Teams,
            COUNT(*) as Schedules,
            MIN(team_id) as MinTeamID,
            MAX(team_id) as MaxTeamID
        FROM HS_Scores_LoneStar_Staging
        GROUP BY BatchID
        ORDER BY BatchID;
    """)
    
    staging = cursor.fetchall()
    for row in staging:
        print(f"BatchID {row.BatchID}: {row.Teams} teams, {row.Schedules} schedules (IDs {row.MinTeamID}-{row.MaxTeamID})")
    print()
    
    # Check what's been exported/imported
    print("✅ IMPORTED TO HS_Scores:")
    print("-"*80)
    cursor.execute("""
        SELECT 
            BatchID,
            COUNT(*) as Games,
            MIN(Season) as FirstSeason,
            MAX(Season) as LastSeason
        FROM HS_Scores
        WHERE Source LIKE 'http://lonestarfootball.net%'
        GROUP BY BatchID
        ORDER BY BatchID;
    """)
    
    imported = cursor.fetchall()
    total_games = 0
    for row in imported:
        print(f"BatchID {row.BatchID}: {row.Games:,} games ({row.FirstSeason}-{row.LastSeason})")
        total_games += row.Games
    
    print()
    print(f"TOTAL IMPORTED: {total_games:,} games")
    print()
    
    # Check team scraping status
    print("🎯 TEAM SCRAPING PROGRESS:")
    print("-"*80)
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT team_id) as TotalTeams,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as Completed,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as InProgress,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as Pending,
            MIN(team_id) as MinID,
            MAX(team_id) as MaxID
        FROM team_scraping_status;
    """)
    
    status = cursor.fetchone()
    print(f"Total Teams Tracked: {status.TotalTeams}")
    print(f"  Completed: {status.Completed}")
    print(f"  In Progress: {status.InProgress}")
    print(f"  Pending: {status.Pending}")
    print(f"Team ID Range: {status.MinID} - {status.MaxID}")
    print()
    
    # What team IDs are available to scrape next?
    print("🆕 NEXT AVAILABLE RANGE:")
    print("-"*80)
    cursor.execute("""
        SELECT MAX(team_id) as LastScraped
        FROM team_scraping_status
        WHERE status = 'completed';
    """)
    
    last_scraped = cursor.fetchone()[0]
    if last_scraped:
        next_start = last_scraped + 1
        print(f"Last scraped team ID: {last_scraped}")
        print(f"Suggested next range: {next_start} - {next_start + 999}")
    else:
        print("No teams scraped yet")
    
    print()
    print("="*80)
    
    conn.close()

if __name__ == "__main__":
    main()