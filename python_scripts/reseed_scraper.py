"""
Reseed Scraper - Generate seed URLs from your HS_Team_Names table
or from previously scraped data to fill gaps
"""

import pyodbc
import csv
import sys

# SQL Server connection
SERVER = "McKnights-PC\\SQLEXPRESS01"
DATABASE = "hs_football_database"

def get_canadian_teams_from_db():
    """
    Get list of Canadian teams from your HS_Team_Names table
    Returns list of team names and states
    """
    print("📊 Connecting to SQL Server...")
    
    conn_str = (
        f"Driver={{SQL Server}};"
        f"Server={SERVER};"
        f"Database={DATABASE};"
        f"Trusted_Connection=yes;"
    )
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # First, check what columns exist
        cursor.execute("""
            SELECT TOP 1 * FROM HS_Team_Names
        """)
        columns = [column[0] for column in cursor.description]
        print(f"   Available columns: {', '.join(columns)}")
        
        # Your table uses: Team_Name and State
        name_col = 'Team_Name'
        state_col = 'State'
        
        print(f"   Using columns: {name_col} (name), {state_col} (state)")
        
        # Get Canadian teams
        query = f"""
        SELECT DISTINCT 
            [{name_col}],
            [{state_col}],
            COUNT(*) as GameCount
        FROM HS_Team_Names
        WHERE [{state_col}] IN ('ON', 'QC', 'NS', 'NB', 'AB', 'BC')
        GROUP BY [{name_col}], [{state_col}]
        ORDER BY [{state_col}], [{name_col}]
        """
        
        cursor.execute(query)
        teams = cursor.fetchall()
        
        print(f"✅ Found {len(teams)} Canadian teams in database")
        
        return [(row[0], row[1], row[2]) for row in teams]
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_teams_from_scraped_csv(csv_file):
    """
    Get unique teams from previously scraped data
    """
    print(f"📁 Reading: {csv_file}")
    
    teams = set()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract host team
            if row.get('Host'):
                teams.add((row['Host'], row.get('HostState', '')))
            
            # Extract opponent team
            if row.get('Opponent'):
                teams.add((row['Opponent'], row.get('OpponentState', '')))
    
    print(f"✅ Found {len(teams)} unique teams in CSV")
    return list(teams)

def get_missing_teams(db_teams, scraped_teams):
    """
    Compare database teams vs scraped teams to find missing ones
    """
    db_set = set((name.strip().upper(), state) for name, state, _ in db_teams)
    scraped_set = set((name.strip().upper(), state) for name, state in scraped_teams)
    
    missing = db_set - scraped_set
    
    print(f"\n📉 Missing teams: {len(missing)}")
    
    return missing

def search_scorestream_for_team(team_name, state):
    """
    Generate a ScoreStream search URL for a team
    Note: This is just a helper - you'll need to manually find the actual team page
    """
    # Clean team name for URL
    clean_name = team_name.replace(' ', '+').replace(',', '')
    search_url = f"https://scorestream.com/search?q={clean_name}+{state}+football"
    return search_url

def create_seed_file(teams, filename="seed_urls.txt"):
    """
    Create a file with search URLs for manual verification
    """
    print(f"\n📝 Creating seed file: {filename}")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# ScoreStream Seed URLs\n")
        f.write("# Find the correct team page and copy its URL to seed_urls_verified.txt\n\n")
        
        for team_name, state in teams:
            search_url = search_scorestream_for_team(team_name, state)
            f.write(f"{team_name} ({state})\n")
            f.write(f"{search_url}\n\n")
    
    print(f"✅ Created: {filename}")
    print(f"   Manually verify URLs and add to seed_urls_verified.txt")

def load_verified_seeds(filename="seed_urls_verified.txt"):
    """
    Load manually verified team URLs
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            urls = []
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        urls.append(line)
            return urls
    except FileNotFoundError:
        print(f"⚠️  {filename} not found")
        return []

def generate_seeds_from_progress():
    """
    Look at scraped opponents that haven't been visited yet
    """
    print("\n🔍 Analyzing scraper progress...")
    
    try:
        # Load progress
        with open('scraper_progress.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            visited_ids = set(row['TeamID'] for row in reader)
        
        print(f"   Visited: {len(visited_ids)} teams")
        
        # Load all scraped games to find unvisited opponents
        import glob
        csv_files = glob.glob('scorestream_batch_*.csv')
        
        if not csv_files:
            print("   No batch files found")
            return []
        
        opponent_links = {}  # OpponentID -> URL
        
        for csv_file in csv_files:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    opp_id = row.get('OpponentID')
                    opp_link = row.get('OpponentLink')
                    opp_state = row.get('OpponentState')
                    
                    if opp_id and opp_link and opp_id not in visited_ids:
                        # Only add if in target regions
                        if opp_state in ['ON', 'QC', 'NS', 'NB']:
                            opponent_links[opp_id] = opp_link
        
        print(f"   Unvisited opponents: {len(opponent_links)}")
        
        return list(opponent_links.values())
        
    except FileNotFoundError:
        print("   No progress file found")
        return []

def main():
    print("="*70)
    print("🌱 SCORESTREAM SCRAPER RESEEDER")
    print("="*70)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        print("\nUsage:")
        print("  python reseed_scraper.py db          - Get teams from database")
        print("  python reseed_scraper.py csv <file>  - Get teams from CSV")
        print("  python reseed_scraper.py missing     - Find missing teams")
        print("  python reseed_scraper.py opponents   - Use unvisited opponents")
        return
    
    if command == "db":
        teams = get_canadian_teams_from_db()
        if teams:
            print("\n📋 Canadian Teams in Database:")
            for name, state, count in teams[:20]:
                print(f"   {name} ({state}) - {count} games")
            if len(teams) > 20:
                print(f"   ... and {len(teams) - 20} more")
            
            create_seed_file([(name, state) for name, state, _ in teams], "db_teams_seeds.txt")
    
    elif command == "csv":
        if len(sys.argv) < 3:
            print("❌ Please provide CSV file: python reseed_scraper.py csv <file>")
            return
        
        csv_file = sys.argv[2]
        teams = get_teams_from_scraped_csv(csv_file)
        
        print("\n📋 Teams from CSV:")
        for name, state in list(teams)[:20]:
            print(f"   {name} ({state})")
        if len(teams) > 20:
            print(f"   ... and {len(teams) - 20} more")
    
    elif command == "missing":
        print("\n1. Loading database teams...")
        db_teams = get_canadian_teams_from_db()
        
        print("\n2. Loading scraped teams...")
        import glob
        csv_files = glob.glob('scorestream_batch_*.csv')
        
        if not csv_files:
            print("❌ No scraped CSV files found")
            return
        
        all_scraped = []
        for csv_file in csv_files:
            all_scraped.extend(get_teams_from_scraped_csv(csv_file))
        
        print("\n3. Finding missing teams...")
        missing = get_missing_teams(db_teams, all_scraped)
        
        if missing:
            print(f"\n📋 Missing Teams ({len(missing)}):")
            for name, state in list(missing)[:30]:
                print(f"   {name} ({state})")
            if len(missing) > 30:
                print(f"   ... and {len(missing) - 30} more")
            
            create_seed_file(list(missing), "missing_teams_seeds.txt")
        else:
            print("✅ All database teams have been scraped!")
    
    elif command == "opponents":
        seed_urls = generate_seeds_from_progress()
        
        if seed_urls:
            print(f"\n📋 Unvisited Opponent URLs: {len(seed_urls)}")
            
            with open('opponent_seeds.txt', 'w', encoding='utf-8') as f:
                f.write("# Unvisited opponent URLs from scraped games\n\n")
                for url in seed_urls:
                    f.write(url + '\n')
            
            print(f"✅ Saved to: opponent_seeds.txt")
            print(f"\nTo use these seeds:")
            print(f"  1. Review opponent_seeds.txt")
            print(f"  2. Run scraper with: scrape_scorestream_batch(start_urls=seed_urls)")
        else:
            print("✅ No unvisited opponents found")
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()
