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
    
    try:
        # First check if table exists and what columns it has
        cursor.execute("""
            SELECT TOP 10 *
            FROM scraping_batches
            ORDER BY batch_id;
        """)
        
        batches = cursor.fetchall()
        if batches:
            # Show first batch to see structure
            print(f"Found {len(batches)} batches")
            for batch in batches:
                print(f"Batch {batch.batch_id}: {batch}")
        else:
            print("No batches found")
    except Exception as e:
        print(f"Table not found or error: {e}")
    
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
    
    try:
        cursor.execute("""
            SELECT TOP 10 *
            FROM team_scraping_status
            ORDER BY team_id DESC;
        """)
        
        teams = cursor.fetchall()
        if teams:
            print("Last 10 teams scraped:")
            for team in teams[:5]:
                print(f"  {team}")
        
        # Get counts
        cursor.execute("""
            SELECT 
                COUNT(*) as Total,
                MIN(team_id) as MinID,
                MAX(team_id) as MaxID
            FROM team_scraping_status;
        """)
        
        counts = cursor.fetchone()
        print(f"\nTotal teams in tracking: {counts.Total}")
        print(f"Team ID range: {counts.MinID} - {counts.MaxID}")
        
    except Exception as e:
        print(f"Table not found or error: {e}")
    
    print()
    # What team IDs are available to scrape next?
    print("🆕 NEXT AVAILABLE RANGE:")
    print("-"*80)
    
    try:
        cursor.execute("""
            SELECT MAX(team_id) as LastTeam
            FROM team_scraping_status;
        """)
        
        last = cursor.fetchone()[0]
        if last:
            next_start = last + 1
            print(f"Last team ID in tracking: {last}")
            print(f"Suggested next range: {next_start} - {next_start + 499}")
        else:
            print("No teams tracked yet")
    except:
        print("Could not determine next range")
    
    print()print("="*80)
    
    conn.close()

if __name__ == "__main__":
    main()