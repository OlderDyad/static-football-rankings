# test_phase4a.py
"""
Phase 4A Validation Test Script
Tests database setup and team_links module functionality
"""

import sys
sys.path.insert(0, '.')  # Ensure we can import team_links

from team_links import get_link_generator, SlugGenerator, generate_slug_for_team
import pyodbc

# --- CONFIGURATION ---
SERVER = "McKnights-PC\\SQLEXPRESS01"
DATABASE = "hs_football_database"
# --- END CONFIGURATION ---

def test_database_setup():
    """Test that all required columns and tables exist"""
    print("="*60)
    print("TEST 1: DATABASE SCHEMA VERIFICATION")
    print("="*60)
    print()
    
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            # Check HS_Team_Names columns
            print("Checking HS_Team_Names columns...")
            required_columns = [
                'Team_Slug', 'Team_Page_URL', 'Program_Page_URL',
                'Has_Team_Page', 'Has_Program_Page', 'Team_Page_Status',
                'Team_Page_Priority', 'Team_Page_Last_Updated'
            ]
            
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'HS_Team_Names' 
                AND COLUMN_NAME IN ({})
            """.format(','.join(f"'{col}'" for col in required_columns)))
            
            found_columns = [row.COLUMN_NAME for row in cursor.fetchall()]
            
            for col in required_columns:
                status = "✓" if col in found_columns else "✗"
                print(f"  {status} {col}")
            
            print()
            
            # Check supporting tables
            print("Checking supporting tables...")
            tables = ['Team_Page_Content', 'Team_Page_Photos', 'Team_Coaches']
            
            for table in tables:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = '{table}'
                """)
                exists = cursor.fetchone()[0] > 0
                status = "✓" if exists else "✗"
                print(f"  {status} {table}")
            
            print()
            
            # Check priorities
            print("Checking priority assignments...")
            cursor.execute("""
                SELECT 
                    Team_Page_Priority,
                    COUNT(*) as Count
                FROM HS_Team_Names
                WHERE Team_Page_Priority > 0
                GROUP BY Team_Page_Priority
                ORDER BY Team_Page_Priority DESC
            """)
            
            priorities = cursor.fetchall()
            if priorities:
                for priority, count in priorities:
                    print(f"  Priority {priority}: {count} teams")
            else:
                print("  ⚠ No priorities set yet")
            
            print()
            return True
            
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False


def test_slug_generation():
    """Test slug generation functionality"""
    print("="*60)
    print("TEST 2: SLUG GENERATION")
    print("="*60)
    print()
    
    test_cases = [
        ("WA", "Everett", "Seagulls", "wa-everett-seagulls"),
        ("TX", "Allen", "Eagles", "tx-allen-eagles"),
        ("FL", "Fort Lauderdale", "St. Thomas Aquinas", "fl-fort-lauderdale-st-thomas-aquinas"),
        ("GA", "Buford", "Wolves", "ga-buford-wolves"),
        ("OK", "Bixby", "Spartans", "ok-bixby-spartans"),
    ]
    
    all_passed = True
    
    for state, city, name, expected in test_cases:
        result = SlugGenerator.create(state, city, name)
        passed = result == expected
        status = "✓" if passed else "✗"
        
        print(f"{status} {state}, {city}, {name}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        
        if not passed:
            all_passed = False
        print()
    
    # Test from team name
    print("Testing slug from full team name:")
    team_name_tests = [
        ("Everett (WA)", "wa-everett"),
        ("Allen (TX)", "tx-allen"),
        ("Buford (GA)", "ga-buford"),
    ]
    
    for team_name, expected in team_name_tests:
        result = SlugGenerator.create_from_team_name(team_name)
        passed = result == expected
        status = "✓" if passed else "✗"
        
        print(f"{status} {team_name} → {result}")
        if not passed:
            print(f"  Expected: {expected}")
            all_passed = False
    
    print()
    return all_passed


def test_link_generator():
    """Test link generation functionality"""
    print("="*60)
    print("TEST 3: LINK GENERATION")
    print("="*60)
    print()
    
    try:
        linker = get_link_generator(SERVER, DATABASE)
        
        # Test with a known team (should exist in database)
        print("Testing link generation...")
        
        # Get a sample team ID
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP 1 ID, Team_Name, Has_Team_Page, Team_Page_Status
                FROM HS_Team_Names
                WHERE Team_Page_Priority > 0
                ORDER BY Team_Page_Priority DESC
            """)
            
            row = cursor.fetchone()
            if row:
                team_id, team_name, has_page, status = row
                
                print(f"Sample Team: {team_name} (ID: {team_id})")
                print(f"Has Page: {has_page}, Status: {status}")
                print()
                
                # Test different link types
                print("Link Type: icon")
                print(f"  {linker.generate_link(team_id, team_name, 'icon')}")
                print()
                
                print("Link Type: full")
                print(f"  {linker.generate_link(team_id, team_name, 'full')}")
                print()
                
                print("Link Type: both")
                print(f"  {linker.generate_link(team_id, team_name, 'both')}")
                print()
                
                # Test cache stats
                stats = linker.get_cache_stats()
                print(f"Cache Stats: {stats['hits']} hits, {stats['misses']} misses")
                print()
                
                return True
            else:
                print("⚠ No teams with priority found")
                return False
                
    except Exception as e:
        print(f"✗ Link generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_find_everett():
    """Find Everett (WA) team ID for pilot project"""
    print("="*60)
    print("TEST 4: FIND EVERETT (WA) FOR PILOT")
    print("="*60)
    print()
    
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    ID,
                    Team_Name,
                    City,
                    State,
                    Mascot,
                    Team_Page_Priority,
                    Team_Slug
                FROM HS_Team_Names
                WHERE Team_Name LIKE '%Everett%' AND State = 'WA'
            """)
            
            rows = cursor.fetchall()
            
            if rows:
                print(f"Found {len(rows)} Everett (WA) team(s):")
                print()
                
                for row in rows:
                    print(f"ID: {row.ID}")
                    print(f"Name: {row.Team_Name}")
                    print(f"City: {row.City}, State: {row.State}")
                    print(f"Mascot: {row.Mascot}")
                    print(f"Priority: {row.Team_Page_Priority}")
                    print(f"Slug: {row.Team_Slug or 'Not generated'}")
                    print()
                
                # Check if it's a Media NC
                everett_id = rows[0].ID
                cursor.execute("""
                    SELECT Season, Wins, Losses, Ties
                    FROM Media_National_Champions
                    WHERE Team_ID = ?
                """, everett_id)
                
                nc_rows = cursor.fetchall()
                if nc_rows:
                    print("Media National Championships:")
                    for season, w, l, t in nc_rows:
                        record = f"{w}-{l}" + (f"-{t}" if t else "")
                        print(f"  {season}: {record}")
                else:
                    print("Not a Media National Champion")
                
                print()
                return True
            else:
                print("⚠ Everett (WA) not found in database")
                return False
                
    except Exception as e:
        print(f"✗ Everett search failed: {e}")
        return False


def main():
    """Run all tests"""
    print()
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "PHASE 4A VALIDATION SUITE" + " "*18 + "║")
    print("╚" + "="*58 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(("Database Schema", test_database_setup()))
    results.append(("Slug Generation", test_slug_generation()))
    results.append(("Link Generator", test_link_generator()))
    results.append(("Find Everett (WA)", test_find_everett()))
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    print()
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print()
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("✓ All tests passed! Phase 4A foundation is ready.")
        print()
        print("Next steps:")
        print("1. Generate slug for Everett: generate_slug_for_team(everett_id, SERVER, DATABASE)")
        print("2. Start building Everett team page template")
        print("3. Integrate team_links into generate_media_champions_json.py")
    else:
        print("✗ Some tests failed. Review errors above.")
    
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())