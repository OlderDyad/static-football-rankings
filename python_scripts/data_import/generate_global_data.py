import json
import pyodbc
import os
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

# Settings
MIN_SEASONS_PROGRAMS = 25

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

# ==========================================
# DATA PROCESSING LOGIC
# ==========================================
def process_global_data(cursor, meta_lookup, mode, decade_start=None):
    """
    mode: 'all-time-teams', 'all-time-programs', 'decade-teams', 'decade-programs'
    """
    
    # 1. Configure Query based on mode
    if 'teams' in mode:
        sub_folder_type = "teams"
        file_name = f"teams-{decade_start}s.json" if decade_start else "all-time-teams.json"
        out_subdir = f"decades/teams" if decade_start else "all-time"

        # Teams Query: Get individual season records
        if decade_start:
            # Decade Teams - UPDATED with Game Count Filter
            sql_exec = """
                SELECT TOP 5000
                    R.Home AS Team,
                    R.Season,
                    CAST(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS DECIMAL(18, 3)) AS Combined,
                    CAST(R.Max_Min_Margin AS DECIMAL(18, 3)) AS Margin,
                    CAST(R.Avg_Of_Avg_Of_Home_Modified_Score AS DECIMAL(18, 3)) AS Win_Loss,
                    CAST(R.Offense AS DECIMAL(18, 3)) AS Offense,
                    CAST(R.Defense AS DECIMAL(18, 3)) AS Defense,
                    G.GamesPlayed AS Games_Played
                FROM HS_Rankings R
                INNER JOIN (
                    SELECT Home AS TeamName, Season, COUNT(*) AS GamesPlayed
                    FROM (
                        SELECT Home, Season FROM HS_Scores WHERE Home IS NOT NULL
                        UNION ALL
                        SELECT Visitor, Season FROM HS_Scores WHERE Visitor IS NOT NULL
                    ) AS AllGames
                    GROUP BY TeamName, Season
                ) G ON R.Home = G.TeamName AND R.Season = G.Season
                WHERE R.Season >= ? AND R.Season <= ?
                  AND R.Week = 52
                  -- GAME COUNT FILTER: 5 for pre-1950, 8 for 1950+
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
                    CAST(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS DECIMAL(18, 3)) AS Combined,
                    CAST(R.Max_Min_Margin AS DECIMAL(18, 3)) AS Margin,
                    CAST(R.Avg_Of_Avg_Of_Home_Modified_Score AS DECIMAL(18, 3)) AS Win_Loss,
                    CAST(R.Offense AS DECIMAL(18, 3)) AS Offense,
                    CAST(R.Defense AS DECIMAL(18, 3)) AS Defense,
                    (SELECT COUNT(*) FROM HS_Scores S WHERE (S.Home = R.Home OR S.Visitor = R.Home) AND S.Season = R.Season) AS Games_Played
                FROM HS_Rankings R
                WHERE R.Week = 52
                ORDER BY Combined DESC
            """
            params = ()
             
    else: # Programs
        sub_folder_type = "programs"
        file_name = f"programs-{decade_start}s.json" if decade_start else "all-time-programs.json"
        out_subdir = f"decades/programs" if decade_start else "all-time"
        
        # Programs Query: Aggregate stats
        if decade_start:
            # Decade Programs - UPDATED with 10-Season Filter
            sql_exec = """
                SELECT TOP 5000
                    R.Home AS Program,
                    COUNT(DISTINCT R.Season) AS Seasons,
                    CAST(AVG(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss) AS DECIMAL(18, 3)) AS Combined,
                    CAST(AVG(R.Max_Min_Margin) AS DECIMAL(18, 3)) AS Margin,
                    CAST(AVG(R.Avg_Of_Avg_Of_Home_Modified_Score) AS DECIMAL(18, 3)) AS Win_Loss,
                    CAST(AVG(R.Offense) AS DECIMAL(18, 3)) AS Offense,
                    CAST(AVG(R.Defense) AS DECIMAL(18, 3)) AS Defense
                FROM HS_Rankings R
                WHERE R.Season >= ? AND R.Season <= ?
                  AND R.Week = 52
                GROUP BY R.Home
                HAVING COUNT(DISTINCT R.Season) >= 10
                ORDER BY Combined DESC
            """
            params = (decade_start, decade_start + 9)
        else:
            # All-Time Programs
            sql_exec = """
                SELECT TOP 5000
                    R.Home AS Program,
                    COUNT(DISTINCT R.Season) AS Seasons,
                    CAST(AVG(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss) AS DECIMAL(18, 3)) AS Combined,
                    CAST(AVG(R.Max_Min_Margin) AS DECIMAL(18, 3)) AS Margin,
                    CAST(AVG(R.Avg_Of_Avg_Of_Home_Modified_Score) AS DECIMAL(18, 3)) AS Win_Loss,
                    CAST(AVG(R.Offense) AS DECIMAL(18, 3)) AS Offense,
                    CAST(AVG(R.Defense) AS DECIMAL(18, 3)) AS Defense
                FROM HS_Rankings R
                WHERE R.Week = 52
                GROUP BY R.Home
                HAVING COUNT(DISTINCT R.Season) >= 25
                ORDER BY Combined DESC
            """
            params = ()

    # 2. Fetch Rankings
    try:
        cursor.execute(sql_exec, params)
        ranking_rows = cursor.fetchall()
        
        if not ranking_rows:
            # print(f"   No data for {mode} ({decade_start})")
            return 0
        
        # Lowercase columns for safe matching
        columns = [column[0].lower() for column in cursor.description]
        rankings = [dict(zip(columns, row)) for row in ranking_rows]
        
    except Exception as e:
        print(f"   Error processing {mode} ({decade_start}): {e}")
        return 0

    # 3. Merge with Metadata
    final_items = []
    id_col = 'id' if 'id' in columns else ('teamid' if 'teamid' in columns else None)
    sql_name_key = 'program' if 'program' in columns else 'team'
    json_name_key = 'program' if 'program' in mode else 'team'

    for i, rank_row in enumerate(rankings):
        meta = None
        entity_name = get_string_value(rank_row, [sql_name_key], 'Unknown')
        
        # Match Logic
        if id_col and str(rank_row.get(id_col, '')) in meta_lookup:
            meta = meta_lookup[str(rank_row.get(id_col))]
        elif entity_name.lower() in meta_lookup:
            meta = meta_lookup[entity_name.lower()]
        
        # Visuals
        mascot = meta['mascot'] if meta else ""
        bg_color = get_hex_color(meta['bg_color_raw'] if meta else "")
        text_color = determine_text_color(bg_color)
        logo_url = fix_image_path(meta['logo']) if meta else ""
        school_logo = fix_image_path(meta['school_logo']) if meta else ""
        website = meta['website'] if meta else ""
        state_val = meta['state'] if meta else rank_row.get('state', '')

        item = {
            "rank": i + 1, # Force sequential rank based on sort order
            json_name_key: entity_name,
            "combined": get_stat_value(rank_row, ['combined', 'combined_score']),
            "margin": get_stat_value(rank_row, ['margin']),
            "win_loss": get_stat_value(rank_row, ['win_loss', 'win_loss_pct', 'winloss']),
            "offense": get_stat_value(rank_row, ['offense']),
            "defense": get_stat_value(rank_row, ['defense']),
            "state": state_val,
            "mascot": mascot,
            "backgroundColor": bg_color,
            "textColor": text_color,
            "logoURL": logo_url,
            "schoolLogoURL": school_logo,
            "website": website
        }
        
        if 'teams' in mode:
            item['season'] = get_int_value(rank_row, ['season', 'year'], 0)
            item['games_played'] = get_int_value(rank_row, ['games_played'], 0)
        else:
            item['seasons'] = get_int_value(rank_row, ['seasons'], 0)

        final_items.append(item)

    if not final_items: return 0
    
    # 4. Save
    final_items.sort(key=lambda x: x.get('rank', 9999))
    top_item = final_items[0]
    
    json_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "type": mode.split('-')[-1], # 'teams' or 'programs'
            "yearRange": str(decade_start) + "s" if decade_start else "All-Time",
            "totalItems": len(final_items),
            "description": f"Top {mode}"
        },
        "topItem": top_item,
        "items": final_items
    }

    # Construct Output Path
    # e.g. docs/data/decades/teams/teams-1950s.json
    # or   docs/data/all-time/all-time-teams.json
    
    if decade_start:
         out_path = os.path.join(DOCS_ROOT, "decades", sub_folder_type)
    else:
         out_path = os.path.join(DOCS_ROOT, "all-time") # Simple root for all-time
         # Note: Adjust this if you have separate folders for all-time/teams and all-time/programs

    if not os.path.exists(out_path): os.makedirs(out_path)
    
    full_path = os.path.join(out_path, file_name)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)

    return len(final_items)

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    start_time = time.time()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 0. Pre-fetch Metadata (Huge optimization)
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
            "logo": m[5] if m[5] else "",
            "school_logo": m[6] if m[6] else "",
            "website": m[7] if m[7] else "",
            "helmet": m[9] if m[9] else "",
            "state": m[10] if m[10] else ""
        }
        if m[8]: meta_lookup[str(m[8])] = data_pkg
        if m[0]: meta_lookup[m[0].lower()] = data_pkg
    print(f"Done. ({len(meta_lookup)} items)")

    # 1. Generate All-Time Lists
    print("\n--- Processing All-Time Lists ---")
    t = process_global_data(cursor, meta_lookup, 'all-time-teams')
    p = process_global_data(cursor, meta_lookup, 'all-time-programs')
    print(f"   All-Time: {t} Teams, {p} Programs")

    # 2. Generate Decades
    print("\n--- Processing Decades ---")
    # Range from 1900 to 2020
    decades = range(1900, 2030, 10) 
    
    total_teams = 0
    total_programs = 0
    
    for d in decades:
        print(f"   {d}s...", end=" ", flush=True)
        t = process_global_data(cursor, meta_lookup, 'decade-teams', d)
        p = process_global_data(cursor, meta_lookup, 'decade-programs', d)
        print(f"[Teams: {t} | Programs: {p}]")
        total_teams += t
        total_programs += p

    conn.close()
    print("\n" + "=" * 60)
    print(f"DONE. Decades Total: {total_teams} Teams, {total_programs} Programs")
    print(f"Duration: {time.time()-start_time:.2f}s")
    print("=" * 60)