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

# Output Directory
DOCS_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data"

# REPO PREFIX (Required for GitHub Pages)
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
    conn_str = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
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
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            try:
                return float(row[key_lower])
            except: continue
    return 0.0

def get_string_value(row, keys, default=''):
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            return str(row[key_lower])
    return default

def get_int_value(row, keys, default=0):
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            try:
                return int(row[key_lower])
            except: continue
    return default

# ==========================================
# PROCESSOR
# ==========================================
def process_global_data(cursor, meta_lookup, mode, decade_start=None):
    
    # 1. Configure SP Calls
    if 'teams' in mode:
        sub_folder = "decades/teams" if decade_start else "all-time"
        file_name = f"teams-{decade_start}s.json" if decade_start else "all-time-teams.json"
        
        if decade_start:
            # Decade Teams
            sql_exec = "EXEC GetTeamsByDecade @DecadeStart=?, @PageNumber=1, @PageSize=5000, @TotalCount=NULL"
            params = (decade_start,)
        else:
            # All-Time Teams
            sql_exec = "EXEC GetAllTimeTeams"
            params = ()
             
    else: # Programs
        sub_folder = "decades/programs" if decade_start else "all-time"
        file_name = f"programs-{decade_start}s.json" if decade_start else "all-time-programs.json"
        
        if decade_start:
            # Decade Programs
            sql_exec = "EXEC GetProgramsByDecade @DecadeStart=?, @MinSeasons=?, @PageNumber=1, @PageSize=5000, @TotalCount=NULL"
            params = (decade_start, 5) # Lower threshold for single decades
        else:
            # All-Time Programs
            sql_exec = "EXEC GetAllTimePrograms @MinSeasons=?"
            params = (MIN_SEASONS_PROGRAMS,)

    # 2. Fetch Data
    try:
        cursor.execute(sql_exec, params)
        ranking_rows = cursor.fetchall()
        if not ranking_rows: return 0
        columns = [column[0].lower() for column in cursor.description]
        rankings = [dict(zip(columns, row)) for row in ranking_rows]
    except Exception as e:
        print(f"   Error processing {mode}: {e}")
        return 0

    # 3. Merge & Build
    final_items = []
    
    id_col = 'id' if 'id' in columns else ('teamid' if 'teamid' in columns else None)
    name_key = 'program' if 'program' in columns else 'team'

    for rank_row in rankings:
        entity_name = get_string_value(rank_row, [name_key], 'Unknown')
        
        # Metadata Lookup
        meta = None
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

        # Build Item
        item = {
            "rank": get_int_value(rank_row, ['rank']),
            ('program' if 'program' in mode else 'team'): entity_name,
            "combined": get_stat_value(rank_row, ['combined', 'combined_score']),
            "margin": get_stat_value(rank_row, ['margin']),
            "win_loss": get_stat_value(rank_row, ['win_loss', 'win_loss_pct']),
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
            item['games_played'] = get_int_value(rank_row, ['gamesplayed', 'games_played'], 0)
        else:
            item['seasons'] = get_int_value(rank_row, ['seasons'], 0)

        final_items.append(item)

    # 4. Save
    final_items.sort(key=lambda x: x.get('rank', 9999))
    
    json_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "type": mode.split('-')[-1],
            "yearRange": str(decade_start) + "s" if decade_start else "All-Time",
            "totalItems": len(final_items),
            "description": f"Top {mode}"
        },
        "topItem": final_items[0],
        "items": final_items
    }

    out_path = os.path.join(DOCS_ROOT, sub_folder)
    if not os.path.exists(out_path): os.makedirs(out_path)
    
    full_path = os.path.join(out_path, file_name)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)

    return len(final_items)

# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    start_time = time.time()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Pre-fetch Metadata
    print("Fetching metadata cache...", end="", flush=True)
    cursor.execute("SELECT Team_Name, City, Mascot, PrimaryColor, SecondaryColor, LogoURL, School_Logo_URL, Website, ID, PhotoUrl, State FROM HS_Team_Names")
    meta_rows = cursor.fetchall()
    meta_lookup = {}
    for m in meta_rows:
        pkg = {
            "mascot": m[2], "bg_color_raw": m[3], "logo": m[5], 
            "school_logo": m[6], "website": m[7], "helmet": m[9], "state": m[10]
        }
        if m[8]: meta_lookup[str(m[8])] = pkg
        if m[0]: meta_lookup[m[0].lower()] = pkg
    print(f" Done ({len(meta_lookup)} items).")

    # Generate All-Time
    print("\n--- All-Time Lists ---")
    t = process_global_data(cursor, meta_lookup, 'all-time-teams')
    p = process_global_data(cursor, meta_lookup, 'all-time-programs')
    print(f"   Teams: {t}, Programs: {p}")

    # Generate Decades
    print("\n--- Decades ---")
    decades = range(1900, 2030, 10)
    for d in decades:
        t = process_global_data(cursor, meta_lookup, 'decade-teams', d)
        p = process_global_data(cursor, meta_lookup, 'decade-programs', d)
        print(f"   {d}s: Teams {t} | Programs {p}")

    conn.close()
    print(f"\nDONE. Duration: {time.time()-start_time:.2f}s")