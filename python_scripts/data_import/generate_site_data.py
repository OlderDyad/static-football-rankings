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

# Base Docs Directory
DOCS_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\states"

# REPO PREFIX (CRITICAL FIX for GitHub Pages 404s)
REPO_PREFIX = "/static-football-rankings"

# MINIMUM SEASONS FOR PROGRAMS
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
    """Safely extract numeric stat value from row."""
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
    """Safely extract integer value from row"""
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            try:
                return int(row[key_lower])
            except (ValueError, TypeError):
                continue
    return default

def get_string_value(row, keys, default=''):
    """Safely extract string value from row"""
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            return str(row[key_lower])
    return default

# ==========================================
# CORE GENERATOR LOGIC
# ==========================================
def process_state_data(cursor, state, mode):
    # 1. Determine Settings
    if mode == 'teams':
        sp_name = "GetTeamsByState"
        sub_folder = "teams"
        file_prefix = "state-teams"
        sql_exec = f"EXEC {sp_name} @State=?, @PageNumber=?, @PageSize=?, @SearchTerm=?"
        params_parens = (f"({state})", 1, 2000, None)
        params_raw = (state, 1, 2000, None)
    else:
        sp_name = "GetProgramsByState"
        sub_folder = "programs"
        file_prefix = "state-programs"
        # UPDATED: MinSeasons now uses configured value
        sql_exec = f"EXEC {sp_name} @State=?, @PageNumber=?, @PageSize=?, @SearchTerm=?, @MinSeasons=?"
        params_parens = (f"({state})", 1, 5000, None, MIN_SEASONS_PROGRAMS)
        params_raw = (state, 1, 5000, None, MIN_SEASONS_PROGRAMS)

    # 2. Call Stored Procedure
    try:
        cursor.execute(sql_exec, params_parens)
        ranking_rows = cursor.fetchall()
        
        if not ranking_rows:
            cursor.execute(sql_exec, params_raw)
            ranking_rows = cursor.fetchall()

        if not ranking_rows: return 0

        # Force lowercase columns for consistent matching
        columns = [column[0].lower() for column in cursor.description]
        rankings = [dict(zip(columns, row)) for row in ranking_rows]

    except Exception as e:
        print(f"   Error calling {sp_name} for {state}: {e}")
        return 0

    # 3. Fetch Visual Metadata
    meta_query = """
        SELECT Team_Name, City, Mascot, PrimaryColor, SecondaryColor, 
               LogoURL, School_Logo_URL, Website, ID, PhotoUrl
        FROM HS_Team_Names WHERE State = ?
    """
    cursor.execute(meta_query, (state,))
    meta_rows = cursor.fetchall()
    
    meta_lookup = {}
    for m in meta_rows:
        data_pkg = {
            "mascot": m[2] if m[2] else "",
            "bg_color_raw": m[3] if m[3] else "",
            "text_color_raw": m[4] if m[4] else "",  # ADD SECONDARY COLOR
            "logo": m[5] if m[5] else "",
            "school_logo": m[6] if m[6] else "",
            "website": m[7] if m[7] else "",
            "helmet": m[9] if m[9] else ""
        }
        if m[8]: meta_lookup[str(m[8])] = data_pkg
        if m[0]: meta_lookup[m[0].lower()] = data_pkg

    # 4. Merge & Build JSON
    final_items = []
    
    id_col = 'id' if 'id' in columns else ('teamid' if 'teamid' in columns else None)
    sql_name_key = 'program' if 'program' in columns else 'team'
    json_name_key = 'program' if mode == 'programs' else 'team'

    for rank_row in rankings:
        meta = None
        entity_name = get_string_value(rank_row, [sql_name_key], 'Unknown')
        
        # Match Logic
        if id_col and str(rank_row.get(id_col, '')) in meta_lookup:
            meta = meta_lookup[str(rank_row.get(id_col))]
        elif entity_name.lower() in meta_lookup:
            meta = meta_lookup[entity_name.lower()]
        else:
            clean = entity_name.lower().replace(f"({state.lower()})", "").strip()
            if clean in meta_lookup:
                meta = meta_lookup[clean]

        # Visuals - USE BOTH PRIMARY AND SECONDARY FROM DATABASE
        mascot = meta['mascot'] if meta else ""
        
        # Try to use actual secondary color from database first
        if meta and meta.get('text_color_raw'):
            bg_color = get_hex_color(meta['bg_color_raw'])
            text_color = get_hex_color(meta['text_color_raw'])
        else:
            # Fall back to auto-calculated text color
            bg_color = get_hex_color(meta['bg_color_raw'] if meta else "")
            text_color = determine_text_color(bg_color)
            
        logo_url = fix_image_path(meta['logo']) if meta else ""
        school_logo = fix_image_path(meta['school_logo']) if meta else ""
        website = meta['website'] if meta else ""

        # --- COLUMN MAPPING LOGIC ---
        # NOTE: Based on your observation, columns are swapped in the SP output for Programs
        # We manually swap them here to correct the JSON output
        
        if mode == 'programs':
             # SWAPPED MAPPING FOR PROGRAMS
             combined_val = get_stat_value(rank_row, ['combined', 'combined_score'])
             margin_val   = get_stat_value(rank_row, ['win_loss', 'win_loss_pct']) # Win/Loss -> Margin
             win_loss_val = get_stat_value(rank_row, ['margin'])                   # Margin -> Win/Loss
             offense_val  = get_stat_value(rank_row, ['defense', 'defense_score']) # Defense -> Offense
             defense_val  = get_stat_value(rank_row, ['offense', 'offense_score']) # Offense -> Defense
        else:
             # STANDARD MAPPING FOR TEAMS
             combined_val = get_stat_value(rank_row, ['combined', 'combined_score'])
             margin_val   = get_stat_value(rank_row, ['margin'])
             win_loss_val = get_stat_value(rank_row, ['win_loss', 'win_loss_pct'])
             offense_val  = get_stat_value(rank_row, ['offense', 'offense_score'])
             defense_val  = get_stat_value(rank_row, ['defense', 'defense_score'])

        # Build item
        item = {
            "rank": get_int_value(rank_row, ['rank']),
            json_name_key: entity_name,
            "combined": combined_val,
            "margin": margin_val,
            "win_loss": win_loss_val,
            "offense": offense_val,
            "defense": defense_val,
            "state": state,
            "mascot": mascot,
            "backgroundColor": bg_color,
            "textColor": text_color,
            "logoURL": logo_url,
            "schoolLogoURL": school_logo,
            "website": website
        }
        
        if mode == 'teams':
            item['season'] = get_int_value(rank_row, ['season', 'year'], 0)
            item['games_played'] = get_int_value(rank_row, ['games_played', 'gamesplayed'], 0)
            # TEAM PAGE LINK FIELDS
            item['hasTeamPage'] = get_int_value(rank_row, ['hasteampage'], 0) == 1
            item['teamPageUrl'] = get_string_value(rank_row, ['teampageurl'], '')
        else:
            item['seasons'] = get_int_value(rank_row, ['seasons'], 0)
            # PROGRAM PAGE LINK FIELDS
            item['hasProgramPage'] = get_int_value(rank_row, ['hasprogrampage'], 0) == 1
            item['programPageUrl'] = get_string_value(rank_row, ['programpageurl'], '')

        final_items.append(item)

    # 5. Save
    # Explicitly sort by Rank to ensure consistency
    final_items.sort(key=lambda x: x.get('rank', 9999))
    
    top_item = final_items[0]
    
    # CRITICAL FIX: Ensure top item has valid colors
    # If the top team's colors are missing/default, try to get them from database
    if top_item.get('backgroundColor') == '#333333' or not top_item.get('backgroundColor'):
        top_team_name = top_item.get(json_name_key, '')
        print(f"      ⚠️  Top team '{top_team_name}' missing colors, querying database...")
        
        try:
            # Try to find the team in HS_Team_Names by exact name match
            color_query = """
                SELECT PrimaryColor, SecondaryColor, Mascot, LogoURL, School_Logo_URL
                FROM HS_Team_Names 
                WHERE Team_Name = ? OR Team_Name LIKE ?
                ORDER BY ID DESC
            """
            cursor.execute(color_query, (top_team_name, f"%{top_team_name.split('(')[0].strip()}%"))
            color_row = cursor.fetchone()
            
            if color_row and color_row[0]:
                top_item['backgroundColor'] = get_hex_color(color_row[0])
                top_item['textColor'] = get_hex_color(color_row[1]) if color_row[1] else determine_text_color(top_item['backgroundColor'])
                if color_row[2]:
                    top_item['mascot'] = color_row[2]
                if color_row[3]:
                    top_item['logoURL'] = fix_image_path(color_row[3])
                if color_row[4]:
                    top_item['schoolLogoURL'] = fix_image_path(color_row[4])
                print(f"      ✓ Colors found: {top_item['backgroundColor']} / {top_item['textColor']}")
            else:
                print(f"      ⚠️  No colors found in database, using defaults")
        except Exception as e:
            print(f"      ⚠️  Error querying colors: {e}")
    
    json_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "type": mode,
            "yearRange": "All-Time",
            "totalItems": len(final_items),
            "description": f"Top {mode} for state: ({state})"
        },
        "topItem": top_item,
        "items": final_items
    }

    out_path = os.path.join(DOCS_ROOT, sub_folder)
    if not os.path.exists(out_path): os.makedirs(out_path)
    
    full_path = os.path.join(out_path, f"{file_prefix}-{state}.json")
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)

    return len(final_items)

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    start_time = time.time()
    
    print("=" * 60)
    print("State Teams & Programs JSON Generator (Color Fix)")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        exit(1)

    print("\nFetching states...")
    cursor.execute("""
        SELECT DISTINCT [State] 
        FROM [HS_Team_Names] 
        WHERE [State] IS NOT NULL 
          AND LEN([State]) = 2 
        ORDER BY [State]
    """)
    states = [row[0] for row in cursor.fetchall()]
    
    print(f"Found {len(states)} states to process\n")

    total_teams = 0
    total_programs = 0
    errors = []

    for state in states:
        print(f"Processing {state}...", end=" ", flush=True)
        try:
            t = process_state_data(cursor, state, 'teams')
            p = process_state_data(cursor, state, 'programs')
            print(f"[Teams: {t} | Programs: {p}]")
            total_teams += t
            total_programs += p
        except Exception as e:
            print(f"[ERROR: {e}]")
            errors.append((state, str(e)))

    conn.close()
    
    print("\n" + "=" * 60)
    print(f"DONE. Teams: {total_teams:,}, Programs: {total_programs:,}")
    print(f"Duration: {time.time()-start_time:.2f}s")
    print(f"Output: {DOCS_ROOT}")
    print("=" * 60)