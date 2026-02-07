"""
generate_global_data.py
========================
Generates JSON files for All-Time and Decade rankings (Teams and Programs).

FIXES APPLIED:
1. State code extracted from team name suffix (XX) instead of unreliable HS_Team_Names.State
2. Proper column mapping for margin/win_loss and offense/defense
3. FIXED: Decade programs now require 7+ seasons (70% of decade) - was incorrectly set to 1
4. ADDED: Generates all-time-programs-25.json, all-time-programs-50.json, all-time-programs-100.json
5. FIXED: Added secondaryColor field for proper accent color theming
"""

import json
import pyodbc
import os
import re
import time
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'

# Base Docs Directory (Root of data folder)
DOCS_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data"

# REPO PREFIX
REPO_PREFIX = "/static-football-rankings"

# Min seasons for programs
MIN_SEASONS_DECADE_PROGRAMS = 7    # Decade lists: 7+ seasons (70% of decade)

# All-Time Programs thresholds (generates separate files for each)
ALL_TIME_PROGRAM_THRESHOLDS = [25, 50, 100]

# ==========================================
# COLOR TRANSLATOR
# ==========================================
STANDARD_COLORS = {
    'Maroon': '#800000', 'Gold': '#FFD700', 'Navy': '#000080', 'Blue': '#0000FF',
    'Red': '#FF0000', 'Black': '#000000', 'White': '#FFFFFF', 'Green': '#008000',
    'Forest Green': '#228B22', 'Purple': '#800080', 'Orange': '#FFA500', 'Yellow': '#FFFF00',
    'Silver': '#C0C0C0', 'Grey': '#808080', 'Gray': '#808080', 'Royal Blue': '#4169E1',
    'Cardinal': '#C41E3A', 'Kelly Green': '#4CBB17', 'Old Gold': '#CFB53B',
    'Vegas Gold': '#C5B358', 'Midnight Blue': '#191970', 'Brown': '#A52A2A',
    'Columbia Blue': '#9BDDFF', 'Teal': '#008080', 'Crimson': '#DC143C',
    'Scarlet': '#FF2400', 'Hunter Green': '#355E3B', 'Burnt Orange': '#CC5500'
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_db_connection():
    conn_str = f'DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    return pyodbc.connect(conn_str)

def get_hex_color(color_input):
    if not color_input: return '#333333'
    clean_val = str(color_input).strip()
    if clean_val.startswith('#'): return clean_val
    return STANDARD_COLORS.get(clean_val.title(), '#333333')

def determine_text_color(hex_color):
    """Calculate readable text color (black or white) based on background brightness"""
    if not hex_color or not hex_color.startswith('#'): return '#FFFFFF'
    try:
        h = hex_color.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
        return '#000000' if brightness > 125 else '#FFFFFF'
    except:
        return '#FFFFFF'

def fix_image_path(path):
    if not path: return ""
    clean = str(path).replace('\\', '/').lstrip('/')
    if clean.startswith(REPO_PREFIX.strip('/')):
        if not clean.startswith('/'): return f"/{clean}"
        return clean
    return f"{REPO_PREFIX}/{clean}"

def extract_state_from_name(team_name):
    """
    Extract state code from team name suffix like "Mater Dei (CA)" -> "CA"
    This is more reliable than the HS_Team_Names.State column which is often empty.
    """
    if not team_name:
        return ""
    
    # Match pattern like "(CA)" or "(TX)" at the end of the name
    match = re.search(r'\(([A-Z]{2})\)\s*$', str(team_name))
    if match:
        return match.group(1)
    return ""

def get_stat_value(row, keys):
    """Safely extract numeric stat value from row dict."""
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            try:
                val = float(row[key_lower])
                return round(val, 3)
            except (ValueError, TypeError):
                continue
    return 0.0

def get_int_value(row, keys, default=0):
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            try:
                return int(row[key_lower])
            except (ValueError, TypeError):
                continue
    return default

def get_string_value(row, keys, default=''):
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            return str(row[key_lower])
    return default

def get_min_seasons_for_decade(decade_start):
    """
    Calculate minimum seasons required for a decade.
    For completed decades: 7 seasons (70% of 10 years)
    For current/incomplete decade: 70% of available years
    """
    current_year = datetime.now().year
    decade_end = decade_start + 9
    
    if current_year <= decade_end:
        # Incomplete decade - calculate available years
        available_years = current_year - decade_start + 1
        min_seasons = max(1, int(available_years * 0.7))
        return min_seasons
    else:
        # Completed decade - require 7 seasons
        return MIN_SEASONS_DECADE_PROGRAMS

# ==========================================
# DATA PROCESSING LOGIC
# ==========================================
def process_global_data(cursor, meta_lookup, mode, decade_start=None, min_seasons_override=None):
    """
    mode: 'all-time-teams', 'all-time-programs', 'decade-teams', 'decade-programs'
    min_seasons_override: For all-time programs, allows generating 25/50/100 variants
    """
    
    # 1. Configure Query based on mode
    if 'teams' in mode:
        sub_folder_type = "teams"
        file_name = f"teams-{decade_start}s.json" if decade_start else "all-time-teams.json"
        out_subdir = f"decades/teams" if decade_start else "all-time"

        # Teams Query: Get individual season records
        if decade_start:
            # Decade Teams
            sql_exec = """
                SELECT TOP 5000
                    R.Home AS Team,
                    R.Season,
                    CAST(
                        (R.Avg_Of_Avg_Of_Home_Modified_Score * 0.723930098938845) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * 0.766431120247001) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Log_Score * 0.790878711628496)
                    AS DECIMAL(18, 3)) AS Combined,
                    CAST(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS DECIMAL(18, 3)) AS Margin,
                    CAST(R.Max_Min_Margin AS DECIMAL(18, 3)) AS Win_Loss,
                    CAST(R.Defense AS DECIMAL(18, 3)) AS Offense,
                    CAST(R.Offense AS DECIMAL(18, 3)) AS Defense,
                    G.GamesPlayed AS Games_Played
                FROM HS_Rankings R
                INNER JOIN (
                    SELECT TeamName, Season, COUNT(*) AS GamesPlayed
                    FROM (
                        SELECT Home AS TeamName, Season FROM HS_Scores WHERE Home IS NOT NULL
                        UNION ALL
                        SELECT Visitor AS TeamName, Season FROM HS_Scores WHERE Visitor IS NOT NULL
                    ) AS AllGames
                    GROUP BY TeamName, Season
                ) G ON R.Home = G.TeamName AND R.Season = G.Season
                WHERE R.Season >= ? AND R.Season <= ?
                  AND R.Week = 52
                  AND ((R.Season < 1950 AND G.GamesPlayed >= 5) OR (R.Season >= 1950 AND G.GamesPlayed >= 8))
                ORDER BY Combined DESC
            """
            params = (decade_start, decade_start + 9)
        else:
            # All-Time Teams
            sql_exec = """
                SELECT TOP 5000
                    R.Home AS Team,
                    R.Season,
                    CAST(
                        (R.Avg_Of_Avg_Of_Home_Modified_Score * 0.723930098938845) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * 0.766431120247001) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Log_Score * 0.790878711628496)
                    AS DECIMAL(18, 3)) AS Combined,
                    CAST(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS DECIMAL(18, 3)) AS Margin,
                    CAST(R.Max_Min_Margin AS DECIMAL(18, 3)) AS Win_Loss,
                    CAST(R.Defense AS DECIMAL(18, 3)) AS Offense,
                    CAST(R.Offense AS DECIMAL(18, 3)) AS Defense,
                    G.GamesPlayed AS Games_Played
                FROM HS_Rankings R
                INNER JOIN (
                    SELECT TeamName, Season, COUNT(*) AS GamesPlayed
                    FROM (
                        SELECT Home AS TeamName, Season FROM HS_Scores WHERE Home IS NOT NULL
                        UNION ALL
                        SELECT Visitor AS TeamName, Season FROM HS_Scores WHERE Visitor IS NOT NULL
                    ) AS AllGames
                    GROUP BY TeamName, Season
                ) G ON R.Home = G.TeamName AND R.Season = G.Season
                WHERE R.Week = 52
                  AND ((R.Season < 1950 AND G.GamesPlayed >= 5) OR (R.Season >= 1950 AND G.GamesPlayed >= 8))
                ORDER BY Combined DESC
            """
            params = ()
             
    else: # Programs
        sub_folder_type = "programs"
        
        # Determine file name based on mode and min_seasons
        if decade_start:
            file_name = f"programs-{decade_start}s.json"
            out_subdir = f"decades/programs"
        elif min_seasons_override:
            file_name = f"all-time-programs-{min_seasons_override}.json"
            out_subdir = "all-time"
        else:
            file_name = "all-time-programs.json"
            out_subdir = "all-time"
        
        # Programs Query: Aggregate stats
        if decade_start:
            # Decade Programs - FIXED: Now uses dynamic min seasons calculation
            min_seasons = get_min_seasons_for_decade(decade_start)
            
            sql_exec = f"""
                SELECT TOP 5000
                    R.Home AS Program,
                    COUNT(DISTINCT R.Season) AS Seasons,
                    AVG(
                        (R.Avg_Of_Avg_Of_Home_Modified_Score * 0.723930098938845) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * 0.766431120247001) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Log_Score * 0.790878711628496)
                    ) AS Combined,
                    AVG(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss) AS Margin,
                    AVG(R.Max_Min_Margin) AS Win_Loss,
                    AVG(R.Defense) AS Offense,
                    AVG(R.Offense) AS Defense
                FROM HS_Rankings R
                INNER JOIN (
                    SELECT TeamName, Season, COUNT(*) AS GamesPlayed
                    FROM (
                        SELECT Home AS TeamName, Season FROM HS_Scores WHERE Home IS NOT NULL
                        UNION ALL
                        SELECT Visitor AS TeamName, Season FROM HS_Scores WHERE Visitor IS NOT NULL
                    ) AS AllGames
                    GROUP BY TeamName, Season
                ) G ON R.Home = G.TeamName AND R.Season = G.Season
                WHERE R.Season >= ? AND R.Season <= ?
                  AND R.Week = 52
                  AND ((R.Season < 1950 AND G.GamesPlayed >= 5) OR (R.Season >= 1950 AND G.GamesPlayed >= 8))
                GROUP BY R.Home
                HAVING COUNT(DISTINCT R.Season) >= {min_seasons}
                ORDER BY Combined DESC
            """
            params = (decade_start, decade_start + 9)

        else:
            # All-Time Programs - use override if provided, else default
            min_seasons = min_seasons_override if min_seasons_override else 25
            
            sql_exec = f"""
                SELECT TOP 5000
                    R.Home AS Program,
                    COUNT(DISTINCT R.Season) AS Seasons,
                    AVG(
                        (R.Avg_Of_Avg_Of_Home_Modified_Score * 0.723930098938845) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * 0.766431120247001) +
                        (R.Avg_Of_Avg_Of_Home_Modified_Log_Score * 0.790878711628496)
                    ) AS Combined,
                    AVG(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss) AS Margin,
                    AVG(R.Max_Min_Margin) AS Win_Loss,
                    AVG(R.Defense) AS Offense,
                    AVG(R.Offense) AS Defense
                FROM HS_Rankings R
                INNER JOIN (
                    SELECT TeamName, Season, COUNT(*) AS GamesPlayed
                    FROM (
                        SELECT Home AS TeamName, Season FROM HS_Scores WHERE Home IS NOT NULL
                        UNION ALL
                        SELECT Visitor AS TeamName, Season FROM HS_Scores WHERE Visitor IS NOT NULL
                    ) AS AllGames
                    GROUP BY TeamName, Season
                ) G ON R.Home = G.TeamName AND R.Season = G.Season
                WHERE R.Week = 52
                  AND ((R.Season < 1950 AND G.GamesPlayed >= 5) OR (R.Season >= 1950 AND G.GamesPlayed >= 8))
                GROUP BY R.Home
                HAVING COUNT(DISTINCT R.Season) >= {min_seasons}
                ORDER BY Combined DESC
            """
            params = ()

    # 2. Fetch Rankings
    try:
        cursor.execute(sql_exec, params)
        ranking_rows = cursor.fetchall()
        
        if not ranking_rows:
            return 0
        
        # Lowercase columns for safe matching
        columns = [column[0].lower() for column in cursor.description]
        rankings = [dict(zip(columns, row)) for row in ranking_rows]
        
    except Exception as e:
        print(f"   Error processing {mode} ({decade_start}): {e}")
        return 0

    # 3. Merge with Metadata
    final_items = []
    sql_name_key = 'program' if 'program' in columns else 'team'
    json_name_key = 'program' if 'program' in mode else 'team'

    for i, rank_row in enumerate(rankings):
        entity_name = get_string_value(rank_row, [sql_name_key], 'Unknown')
        
        # Extract state from team/program name - THIS IS THE KEY FIX
        state_val = extract_state_from_name(entity_name)
        
        # Match with metadata for visuals
        meta = meta_lookup.get(entity_name.lower())
        
        # Visuals from metadata - FIXED: Added secondaryColor
        mascot = meta['mascot'] if meta else ""
        bg_color = get_hex_color(meta['bg_color_raw'] if meta else "")
        secondary_color = get_hex_color(meta['secondary_color_raw'] if meta else "#FFD700")  # ADDED
        text_color = determine_text_color(bg_color)
        logo_url = fix_image_path(meta['logo'] if meta else "")
        school_logo = fix_image_path(meta['school_logo'] if meta else "")
        website = meta['website'] if meta else ""

        # --- COLUMN MAPPING LOGIC ---
        # Programs have swapped columns in SQL output (same issue as state programs)
        if 'program' in mode:
            # SWAPPED MAPPING FOR PROGRAMS
            combined_val = get_stat_value(rank_row, ['combined'])
            margin_val   = get_stat_value(rank_row, ['win_loss'])  # Win/Loss → Margin
            win_loss_val = get_stat_value(rank_row, ['margin'])    # Margin → Win/Loss
            offense_val  = get_stat_value(rank_row, ['defense'])   # Defense → Offense
            defense_val  = get_stat_value(rank_row, ['offense'])   # Offense → Defense
        else:
            # STANDARD MAPPING FOR TEAMS
            combined_val = get_stat_value(rank_row, ['combined'])
            margin_val   = get_stat_value(rank_row, ['margin'])
            win_loss_val = get_stat_value(rank_row, ['win_loss'])
            offense_val  = get_stat_value(rank_row, ['offense'])
            defense_val  = get_stat_value(rank_row, ['defense'])

        item = {
            "rank": i + 1,
            json_name_key: entity_name,
            "combined": combined_val,
            "margin": margin_val,
            "win_loss": win_loss_val,
            "offense": offense_val,
            "defense": defense_val,
            "state": state_val,
            "mascot": mascot,
            "backgroundColor": bg_color,
            "secondaryColor": secondary_color,  # ADDED
            "textColor": text_color,
            "logoURL": logo_url,
            "schoolLogoURL": school_logo,
            "website": website
        }
        
        if 'teams' in mode:
            item['season'] = get_int_value(rank_row, ['season', 'year'], 0)
            item['games_played'] = get_int_value(rank_row, ['games_played', 'gamesplayed'], 0)
        else:
            item['seasons'] = get_int_value(rank_row, ['seasons'], 0)

        final_items.append(item)

    if not final_items: 
        return 0
    
    # 4. Save
    top_item = final_items[0]
    
    # Determine year range for metadata
    if decade_start:
        if decade_start < 1900:
            year_range = "Pre-1900s"
        else:
            year_range = f"{decade_start}s"
    else:
        year_range = "All-Time"
    
    # Description
    if min_seasons_override:
        description = f"All-time top programs ({min_seasons_override}+ seasons)"
    elif decade_start:
        description = f"Top {mode.replace('-', ' ')} of the {decade_start}s"
    else:
        description = f"Top {mode.replace('-', ' ')}"
    
    json_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "type": "teams" if 'teams' in mode else "programs",
            "yearRange": year_range,
            "totalItems": len(final_items),
            "description": description
        },
        "topItem": top_item,
        "items": final_items
    }

    # Construct Output Path
    if decade_start:
        out_path = os.path.join(DOCS_ROOT, "decades", sub_folder_type)
    else:
        out_path = os.path.join(DOCS_ROOT, "all-time")

    if not os.path.exists(out_path): 
        os.makedirs(out_path)
    
    full_path = os.path.join(out_path, file_name)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)

    return len(final_items)

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    start_time = time.time()
    
    print("=" * 60)
    print("Global (All-Time & Decade) JSON Generator")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    print("✓ Database connection established")

    # 0. Pre-fetch Metadata (Colors & Images)
    print("Fetching metadata cache (Colors & Images)... ", end="", flush=True)
    meta_query = """
        SELECT Team_Name, City, Mascot, PrimaryColor, SecondaryColor, 
               LogoURL, School_Logo_URL, Website, ID, PhotoUrl, State
        FROM HS_Team_Names
    """
    cursor.execute(meta_query)
    meta_rows = cursor.fetchall()
    
    meta_lookup = {}
    for m in meta_rows:
        data_pkg = {
            "mascot": m[2] if m[2] else "",
            "bg_color_raw": m[3] if m[3] else "",
            "secondary_color_raw": m[4] if m[4] else "",  # ADDED
            "logo": m[5] if m[5] else "",
            "school_logo": m[6] if m[6] else "",
            "website": m[7] if m[7] else "",
            "helmet": m[9] if m[9] else "",
            "state": m[10] if m[10] else ""
        }
        if m[8]: meta_lookup[str(m[8])] = data_pkg
        if m[0]: meta_lookup[m[0].lower()] = data_pkg
    print(f"Done. ({len(meta_lookup)} items)")

    # 1. Generate All-Time Teams
    print("\n--- Processing All-Time Lists ---")
    t = process_global_data(cursor, meta_lookup, 'all-time-teams')
    print(f"   All-Time Teams: {t}")

    # 2. Generate All-Time Programs (25+, 50+, 100+ seasons)
    for threshold in ALL_TIME_PROGRAM_THRESHOLDS:
        p = process_global_data(cursor, meta_lookup, 'all-time-programs', min_seasons_override=threshold)
        print(f"   All-Time Programs ({threshold}+ seasons): {p}")

    # 3. Generate Decades
    print("\n--- Processing Decades ---")
    
    total_teams = 0
    total_programs = 0
    
    # Standard decades 1900-2020
    decades = list(range(1900, 2030, 10))
    
    for d in decades:
        min_seasons = get_min_seasons_for_decade(d)
        print(f"   {d}s (min {min_seasons} seasons for programs)...", end=" ", flush=True)
        t = process_global_data(cursor, meta_lookup, 'decade-teams', d)
        p = process_global_data(cursor, meta_lookup, 'decade-programs', d)
        print(f"[Teams: {t} | Programs: {p}]")
        total_teams += t
        total_programs += p

    conn.close()
    
    print("\n" + "=" * 60)
    print(f"DONE.")
    print(f"  All-Time: docs/data/all-time/")
    print(f"    - all-time-teams.json")
    for threshold in ALL_TIME_PROGRAM_THRESHOLDS:
        print(f"    - all-time-programs-{threshold}.json")
    print(f"  Decades:  docs/data/decades/teams/ and decades/programs/")
    print(f"  Total Decades: {total_teams} Teams, {total_programs} Programs")
    print(f"  Duration: {time.time()-start_time:.2f}s")
    print("=" * 60)