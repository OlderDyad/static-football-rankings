"""
LoneStar Discovery Gap Finder & Reseeder
Identifies missing teams and adds diverse seeds for complete coverage
"""

import pyodbc
import logging
from typing import List, Tuple

# Configuration
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
DB_CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER_NAME};"
    f"DATABASE={DATABASE_NAME};"
    f"Trusted_Connection=yes;"
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Diverse seed teams covering different regions and classification levels
DIVERSE_SEEDS = [
    # Small Schools (1A-2A)
    (1649, "https://lonestarfootball.net/team.asp?T=1649", "Frost", "Small 1A"),
    (1426, "https://lonestarfootball.net/team.asp?T=1426", "Canadian", "Small 2A Panhandle"),
    (1897, "https://lonestarfootball.net/team.asp?T=1897", "Refugio", "Small 2A South"),
    
    # West Texas
    (1008, "https://lonestarfootball.net/team.asp?T=1008", "Midland Lee", "West Texas 6A"),
    (1426, "https://lonestarfootball.net/team.asp?T=1426", "Andrews", "West Texas 4A"),
    
    # Panhandle
    (1013, "https://lonestarfootball.net/team.asp?T=1013", "Amarillo", "Panhandle"),
    (1108, "https://lonestarfootball.net/team.asp?T=1108", "Pampa", "Panhandle"),
    
    # South Texas
    (1066, "https://lonestarfootball.net/team.asp?T=1066", "Brownsville Hanna", "Valley"),
    (1076, "https://lonestarfootball.net/team.asp?T=1076", "McAllen", "Valley"),
    (1846, "https://lonestarfootball.net/team.asp?T=1846", "Port Lavaca Calhoun", "Coastal"),
    
    # East Texas
    (1127, "https://lonestarfootball.net/team.asp?T=1127", "Tyler Lee", "East Texas"),
    (1258, "https://lonestarfootball.net/team.asp?T=1258", "Marshall", "East Texas"),
    (1270, "https://lonestarfootball.net/team.asp?T=1270", "Longview", "East Texas"),
    
    # Central Texas
    (1239, "https://lonestarfootball.net/team.asp?T=1239", "Temple", "Central"),
    (1246, "https://lonestarfootball.net/team.asp?T=1246", "Waco", "Central"),
    (1783, "https://lonestarfootball.net/team.asp?T=1783", "Lampasas", "Central"),
    
    # San Antonio Area
    (1029, "https://lonestarfootball.net/team.asp?T=1029", "San Antonio Roosevelt", "SA"),
    (1863, "https://lonestarfootball.net/team.asp?T=1863", "Boerne", "Hill Country"),
    
    # Houston Area (if not already covered)
    (1072, "https://lonestarfootball.net/team.asp?T=1072", "Houston Bellaire", "Houston"),
    (1802, "https://lonestarfootball.net/team.asp?T=1802", "Katy", "Houston Suburbs"),
]

def check_coverage_gaps(cursor) -> List[int]:
    """
    Analyze discovered teams to find potential gaps
    Returns list of team IDs that might be missing
    """
    
    logger.info("Analyzing team coverage...")
    
    # Get current team count
    cursor.execute("SELECT COUNT(*) FROM lonestar_teams")
    current_count = cursor.fetchone()[0]
    logger.info(f"Current teams in database: {current_count}")
    
    # Get ID range
    cursor.execute("""
        SELECT 
            MIN(team_id) as min_id, 
            MAX(team_id) as max_id,
            COUNT(*) as total_teams
        FROM lonestar_teams
    """)
    
    result = cursor.fetchone()
    min_id, max_id, total = result.min_id, result.max_id, result.total_teams
    
    logger.info(f"ID Range: {min_id} to {max_id}")
    logger.info(f"Total IDs in range: {max_id - min_id + 1}")
    logger.info(f"Coverage ratio: {total}/{max_id - min_id + 1} ({100*total/(max_id-min_id+1):.1f}%)")
    
    # Find gaps in the ID sequence
    cursor.execute("""
        WITH NumberSequence AS (
            SELECT team_id
            FROM lonestar_teams
        )
        SELECT 
            team_id + 1 as gap_start
        FROM NumberSequence
        WHERE team_id + 1 NOT IN (SELECT team_id FROM lonestar_teams)
          AND team_id < ?
        ORDER BY team_id
    """, max_id)
    
    gaps = [row.gap_start for row in cursor.fetchall()]
    
    if gaps:
        logger.info(f"Found {len(gaps)} gaps in ID sequence")
        logger.info(f"Sample gaps: {gaps[:20]}")
    
    return gaps

def add_diverse_seeds(cursor) -> int:
    """
    Add diverse seed teams to ensure full coverage
    Returns count of new seeds added
    """
    
    logger.info("Adding diverse seed teams...")
    
    seeds_added = 0
    
    for team_id, team_url, team_name, region in DIVERSE_SEEDS:
        try:
            # Check if already in database
            cursor.execute("""
                SELECT team_id 
                FROM lonestar_teams 
                WHERE team_id = ?
            """, team_id)
            
            if cursor.fetchone():
                logger.info(f"  ✓ {team_name} ({region}) - already in database")
                continue
            
            # Add new seed
            cursor.execute("""
                INSERT INTO lonestar_teams (team_id, team_name, team_url)
                VALUES (?, ?, ?)
            """, team_id, team_name, team_url)
            
            seeds_added += 1
            logger.info(f"  + Added {team_name} ({region}) as new seed")
            
        except Exception as e:
            logger.warning(f"  ✗ Error adding {team_name}: {e}")
            continue
    
    cursor.connection.commit()
    logger.info(f"Added {seeds_added} new seed teams")
    
    return seeds_added

def analyze_geographic_coverage(cursor):
    """
    Analyze if we have good geographic coverage
    """
    
    logger.info("\nGeographic Coverage Analysis:")
    logger.info("=" * 50)
    
    # Check for teams by approximate regions (based on team names)
    regions = {
        'Houston': ['Houston', 'Katy', 'Cypress', 'Klein', 'Humble', 'Kingwood', 'Atascocita'],
        'Dallas': ['Dallas', 'Irving', 'Garland', 'Plano', 'Richardson', 'Mesquite', 'McKinney'],
        'San Antonio': ['San Antonio', 'Alamo Heights', 'Boerne', 'Seguin'],
        'Austin': ['Austin', 'Round Rock', 'Cedar Park', 'Westlake', 'Lake Travis'],
        'Fort Worth': ['Fort Worth', 'Arlington', 'Mansfield', 'Burleson'],
        'Valley': ['McAllen', 'Brownsville', 'Edinburg', 'Mission', 'Pharr', 'Harlingen'],
        'West Texas': ['Midland', 'Odessa', 'Abilene', 'San Angelo', 'Lubbock'],
        'Panhandle': ['Amarillo', 'Pampa', 'Borger', 'Dumas', 'Canyon'],
        'East Texas': ['Tyler', 'Longview', 'Marshall', 'Texarkana', 'Lufkin'],
        'Coastal': ['Corpus Christi', 'Port Arthur', 'Beaumont', 'Port Lavaca', 'Victoria']
    }
    
    for region_name, keywords in regions.items():
        keyword_pattern = '|'.join(keywords)
        
        cursor.execute(f"""
            SELECT COUNT(*) as team_count
            FROM lonestar_teams
            WHERE team_name LIKE '%{keywords[0]}%'
        """ + ''.join([f" OR team_name LIKE '%{kw}%'" for kw in keywords[1:]]))
        
        count = cursor.fetchone().team_count
        logger.info(f"{region_name:15s}: {count:4d} teams")

def main():
    """Main analysis and reseeding"""
    
    connection = None
    
    try:
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()
        
        print("\n" + "="*60)
        print("  LoneStar Discovery Gap Analysis")
        print("="*60 + "\n")
        
        # Analyze current coverage
        gaps = check_coverage_gaps(cursor)
        
        # Geographic analysis
        analyze_geographic_coverage(cursor)
        
        # Add diverse seeds
        print("\n" + "="*60)
        seeds_added = add_diverse_seeds(cursor)
        
        if seeds_added > 0:
            print("\n" + "="*60)
            print(f"  Added {seeds_added} new seed teams")
            print("  Run the scraper again with Option 1 to discover")
            print("  teams connected to these new seeds")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("  All diverse seeds already in database")
            print("  Coverage appears complete!")
            print("="*60)
        
        # Final stats
        cursor.execute("SELECT COUNT(*) FROM lonestar_teams")
        final_count = cursor.fetchone()[0]
        print(f"\nTotal teams in database: {final_count}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    main()