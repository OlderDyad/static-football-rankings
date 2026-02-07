"""
Generate prioritized data collection targets (FAST VERSION)
Creates target lists with performance optimization and optional queries
"""
import pyodbc
import pandas as pd
from pathlib import Path
import sys
import time

# Configuration
SERVER_INSTANCE = "MCKNIGHTS-PC\\SQLEXPRESS01"
DATABASE = "hs_football_database"
OUTPUT_DIR = Path("./targets")
QUERY_TIMEOUT = 300  # 5 minutes max per query

# Parse command line arguments
SKIP_ISLAND = False
SKIP_ELITE = False
SKIP_COVERAGE = False

for arg in sys.argv[1:]:
    if arg == "--skip-island":
        SKIP_ISLAND = True
    elif arg == "--skip-elite":
        SKIP_ELITE = True
    elif arg == "--skip-coverage":
        SKIP_COVERAGE = True
    elif arg == "--elite-only":
        SKIP_ISLAND = True
        SKIP_COVERAGE = True
    elif arg == "--coverage-only":
        SKIP_ISLAND = True
        SKIP_ELITE = True

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

print("🎯 Generating data collection targets (FAST VERSION)...")
print(f"   Server: {SERVER_INSTANCE}")
print(f"   Database: {DATABASE}")
print(f"   Output: {OUTPUT_DIR}")
print(f"   Timeout: {QUERY_TIMEOUT}s per query")
if SKIP_ISLAND:
    print("   ⏭️  Skipping: Island Programs")
if SKIP_ELITE:
    print("   ⏭️  Skipping: Elite Low-Game")
if SKIP_COVERAGE:
    print("   ⏭️  Skipping: State Coverage")
print()

# Connect to SQL Server
try:
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_INSTANCE};DATABASE={DATABASE};Trusted_Connection=yes;"
    print("🔌 Connecting to database...")
    conn = pyodbc.connect(conn_str, timeout=30)
    conn.timeout = QUERY_TIMEOUT
    print("✅ Connected!")
    print()
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

# ============================================
# TARGET TYPE 1: ISLAND PROGRAMS (OPTIMIZED)
# ============================================
if not SKIP_ISLAND:
    print("📊 Identifying island programs (multi-season volatility)...")
    print("   ⚠️  This query can be slow on large datasets")
    print("   💡 Use --skip-island to skip this, or --elite-only for quick results")
    start_time = time.time()

    # First check if convergence table exists and get row count
    check_sql = """
    SELECT COUNT(*) as row_count 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_NAME = 'HS_Rankings_Convergence_Master'
    """
    
    try:
        result = pd.read_sql(check_sql, conn)
        if result['row_count'][0] == 0:
            print("   ℹ️  HS_Rankings_Convergence_Master table not found - skipping")
        else:
            # Simplified query - just focus on teams with high volatility
            island_programs_sql = """
            WITH RunChanges AS (
                SELECT TOP 10000
                    R1.Home as Team, 
                    R1.Season, 
                    ABS(R2.Margin - R1.Margin) as Margin_Change
                FROM HS_Rankings_Convergence_Master R1
                INNER JOIN HS_Rankings_Convergence_Master R2 
                    ON R1.Home = R2.Home 
                    AND R1.Season = R2.Season 
                    AND R2.Run_Number = R1.Run_Number + 1
                WHERE R1.Season >= 2015  -- Focus on recent seasons for speed
                ORDER BY ABS(R2.Margin - R1.Margin) DESC
            ),
            TeamVolatility AS (
                SELECT 
                    RC.Team, 
                    RC.Season, 
                    AVG(RC.Margin_Change) as Avg_Volatility,
                    (SELECT COUNT(DISTINCT Date) FROM HS_Scores S 
                     WHERE (S.Home = RC.Team OR S.Visitor = RC.Team) 
                     AND S.Season = RC.Season) as Games_Played
                FROM RunChanges RC
                GROUP BY RC.Team, RC.Season
            ),
            ProgramSummary AS (
                SELECT 
                    Team as Program,
                    COUNT(*) as Volatile_Seasons,
                    AVG(Avg_Volatility) as Program_Avg_Volatility,
                    AVG(Games_Played) as Avg_Games_Per_Season,
                    MIN(Season) as First_Volatile_Season,
                    MAX(Season) as Last_Volatile_Season,
                    RIGHT(Team, 4) as State_Code
                FROM TeamVolatility
                WHERE Avg_Volatility > 10
                GROUP BY Team
                HAVING COUNT(*) >= 2
            )
            SELECT 
                Program, 
                State_Code, 
                Volatile_Seasons,
                CAST(Program_Avg_Volatility AS DECIMAL(10,2)) as Avg_Volatility,
                CAST(Avg_Games_Per_Season AS DECIMAL(10,1)) as Avg_Games,
                First_Volatile_Season, 
                Last_Volatile_Season,
                CASE 
                    WHEN Volatile_Seasons >= 5 THEN 'CRITICAL' 
                    WHEN Volatile_Seasons >= 3 THEN 'HIGH' 
                    ELSE 'MEDIUM' 
                END as Priority,
                'Island Program' as Issue_Type
            FROM ProgramSummary
            ORDER BY Volatile_Seasons DESC, Program_Avg_Volatility DESC
            """
            
            island_programs = pd.read_sql(island_programs_sql, conn)
            elapsed = time.time() - start_time
            
            if len(island_programs) > 0:
                island_programs.to_csv(OUTPUT_DIR / "island_programs.csv", index=False)
                print(f"✅ Island programs: {len(island_programs)} identified (took {elapsed:.1f}s)")
                critical = len(island_programs[island_programs['Priority'] == 'CRITICAL'])
                high = len(island_programs[island_programs['Priority'] == 'HIGH'])
                medium = len(island_programs[island_programs['Priority'] == 'MEDIUM'])
                print(f"   CRITICAL: {critical}, HIGH: {high}, MEDIUM: {medium}")
            else:
                print(f"   ℹ️  No island programs found (took {elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ⚠️  Island programs query failed after {elapsed:.1f}s: {e}")
        print(f"   💡 Try running with --skip-island flag")
    
    print()

# ============================================
# TARGET TYPE 2: ELITE LOW-GAME TEAMS (FAST)
# ============================================
if not SKIP_ELITE:
    print("📊 Identifying elite teams with too few games...")
    start_time = time.time()

    elite_lowgame_sql = """
    WITH RankedTeams AS (
        SELECT 
            Home as Team, 
            Season,
            CAST(Avg_Of_Avg_Of_Home_Modified_Score AS DECIMAL(10,2)) as Margin,
            ROW_NUMBER() OVER (PARTITION BY Season ORDER BY Avg_Of_Avg_Of_Home_Modified_Score DESC) as Season_Rank
        FROM HS_Rankings 
        WHERE Week = 52
    ),
    GameCounts AS (
        SELECT 
            RT.Team, 
            RT.Season, 
            RT.Margin, 
            RT.Season_Rank,
            COUNT(DISTINCT S.Date) as Games_Played,
            RIGHT(RT.Team, 4) as State_Code
        FROM RankedTeams RT
        LEFT JOIN HS_Scores S 
            ON (S.Home = RT.Team OR S.Visitor = RT.Team) 
            AND S.Season = RT.Season
        WHERE RT.Season_Rank <= 1000  -- Pre-filter for speed
        GROUP BY RT.Team, RT.Season, RT.Margin, RT.Season_Rank
    )
    SELECT 
        Team, 
        Season, 
        State_Code, 
        Season_Rank, 
        Margin, 
        Games_Played,
        CASE 
            WHEN Season_Rank <= 100 AND Games_Played < 8 THEN 'CRITICAL' 
            WHEN Season_Rank <= 500 AND Games_Played < 6 THEN 'HIGH' 
            WHEN Season_Rank <= 1000 AND Games_Played < 5 THEN 'MEDIUM'
            ELSE 'LOW'
        END as Priority,
        CASE
            WHEN Games_Played = 0 THEN 'No games recorded'
            WHEN Games_Played <= 3 THEN 'Very few games'
            WHEN Games_Played <= 7 THEN 'Below typical season'
            ELSE 'Review for accuracy'
        END as Issue_Type
    FROM GameCounts 
    WHERE Games_Played < 8
    ORDER BY Season_Rank, Games_Played
    """

    try:
        elite_lowgame = pd.read_sql(elite_lowgame_sql, conn)
        elapsed = time.time() - start_time
        
        if len(elite_lowgame) > 0:
            elite_lowgame.to_csv(OUTPUT_DIR / "elite_lowgame.csv", index=False)
            print(f"✅ Elite low-game teams: {len(elite_lowgame)} identified (took {elapsed:.1f}s)")
            critical = len(elite_lowgame[elite_lowgame['Priority'] == 'CRITICAL'])
            high = len(elite_lowgame[elite_lowgame['Priority'] == 'HIGH'])
            medium = len(elite_lowgame[elite_lowgame['Priority'] == 'MEDIUM'])
            print(f"   CRITICAL: {critical}, HIGH: {high}, MEDIUM: {medium}")
        else:
            print(f"   ℹ️  No elite low-game teams found (took {elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Elite low-game query failed after {elapsed:.1f}s: {e}")
    
    print()

# ============================================
# TARGET TYPE 3: STATE COVERAGE GAPS (FAST)
# ============================================
if not SKIP_COVERAGE:
    print("📊 Analyzing state coverage gaps...")
    start_time = time.time()

    state_coverage_sql = """
    WITH ModernBaseline AS (
        SELECT 
            RIGHT(Home, 4) as State_Code, 
            AVG(Game_Count) as Expected_Games_Per_Team
        FROM (
            SELECT 
                Home, 
                Season, 
                COUNT(*) as Game_Count
            FROM HS_Scores
            WHERE Season BETWEEN 2010 AND 2023  -- Recent baseline
            GROUP BY Home, Season
        ) T
        GROUP BY RIGHT(Home, 4)
    ),
    HistoricalCoverage AS (
        SELECT 
            RIGHT(S.Home, 4) as State_Code, 
            S.Season,
            COUNT(DISTINCT S.Home) as Teams,
            COUNT(*) as Total_Games,
            CAST(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT S.Home), 0) AS DECIMAL(10,2)) as Avg_Games_Per_Team
        FROM HS_Scores S
        WHERE Season BETWEEN 1960 AND 1974
        GROUP BY RIGHT(S.Home, 4), S.Season
    )
    SELECT 
        HC.State_Code, 
        HC.Season, 
        HC.Teams, 
        HC.Total_Games, 
        HC.Avg_Games_Per_Team as Actual_Avg_Games,
        CAST(MB.Expected_Games_Per_Team AS DECIMAL(10,2)) as Expected_Games_Per_Team,
        CAST((HC.Avg_Games_Per_Team / NULLIF(MB.Expected_Games_Per_Team, 0)) * 100 AS DECIMAL(5,2)) as Coverage_Pct,
        CASE
            WHEN (HC.Avg_Games_Per_Team / NULLIF(MB.Expected_Games_Per_Team, 0)) * 100 < 25 THEN 'CRITICAL'
            WHEN (HC.Avg_Games_Per_Team / NULLIF(MB.Expected_Games_Per_Team, 0)) * 100 < 50 THEN 'HIGH'
            WHEN (HC.Avg_Games_Per_Team / NULLIF(MB.Expected_Games_Per_Team, 0)) * 100 < 75 THEN 'MEDIUM'
            ELSE 'GOOD'
        END as Priority,
        CAST(MB.Expected_Games_Per_Team - HC.Avg_Games_Per_Team AS DECIMAL(10,2)) as Games_Gap
    FROM HistoricalCoverage HC
    LEFT JOIN ModernBaseline MB ON HC.State_Code = MB.State_Code
    WHERE MB.Expected_Games_Per_Team IS NOT NULL
    ORDER BY Coverage_Pct, HC.Season
    """

    try:
        state_coverage = pd.read_sql(state_coverage_sql, conn)
        elapsed = time.time() - start_time
        
        if len(state_coverage) > 0:
            state_coverage.to_csv(OUTPUT_DIR / "state_coverage.csv", index=False)
            print(f"✅ State coverage analysis: {len(state_coverage)} state-seasons analyzed (took {elapsed:.1f}s)")
            critical = len(state_coverage[state_coverage['Priority'] == 'CRITICAL'])
            high = len(state_coverage[state_coverage['Priority'] == 'HIGH'])
            medium = len(state_coverage[state_coverage['Priority'] == 'MEDIUM'])
            print(f"   CRITICAL: {critical}, HIGH: {high}, MEDIUM: {medium}")
        else:
            print(f"   ℹ️  No coverage gaps found (took {elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ State coverage query failed after {elapsed:.1f}s: {e}")
    
    print()

# Close connection
conn.close()

# ============================================
# SUMMARY
# ============================================
print("=== DATA COLLECTION TARGETS GENERATED ===")
print()
print(f"📁 Files created in {OUTPUT_DIR}:")
created_files = []
if (OUTPUT_DIR / "island_programs.csv").exists():
    print("   ✅ island_programs.csv")
    created_files.append("island_programs.csv")
if (OUTPUT_DIR / "elite_lowgame.csv").exists():
    print("   ✅ elite_lowgame.csv")
    created_files.append("elite_lowgame.csv")
if (OUTPUT_DIR / "state_coverage.csv").exists():
    print("   ✅ state_coverage.csv")
    created_files.append("state_coverage.csv")

if not created_files:
    print("   ⚠️  No files were created")
    print()
    print("💡 TIPS:")
    print("   - The island programs query is very slow on large datasets")
    print("   - Try: python generate_team_targets.py --elite-only")
    print("   - Or:  python generate_team_targets.py --skip-island")
else:
    print()
    print("🎯 Recommended workflow:")
    print("   1. Elite Low-Game    - Quick wins, single team-seasons with high impact")
    print("   2. State Coverage    - Systematic state-by-state")
    if not SKIP_ISLAND:
        print("   3. Island Programs   - Work on CRITICAL programs across all affected seasons")
    print()
    print("📊 Next step: Open the CSV files in Excel and prioritize!")

print()
print("💡 USAGE OPTIONS:")
print("   python generate_team_targets.py              # Run all queries")
print("   python generate_team_targets.py --elite-only  # Fastest - just elite low-game teams")
print("   python generate_team_targets.py --skip-island # Skip the slow convergence query")
print()
print("✅ Done!")
