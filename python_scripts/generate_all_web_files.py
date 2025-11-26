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
    'Columbia Blue': '#9BDDFF', 'Teal': '#008080'
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_db_connection():
    conn_str = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    return pyodbc.connect(conn_str)

def get_hex_color(color_input):
    if not color_input: return '#333333'
    clean_val = color_input.strip()
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
    return path.replace('\\', '/').lstrip('/')

# ==========================================
# CORE GENERATOR LOGIC
# ==========================================
def process_state_data(cursor, state, mode):
    """
    mode: 'teams' or 'programs'
    """
    # 1. Determine Stored Procedure & Output Folder
    if mode == 'teams':
        sp_name = "GetTeamsByState"
        sub_folder = "teams"
        file_prefix = "state-teams"
    else:
        sp_name = "GetProgramsByState"
        sub_folder = "programs"
        file_prefix = "state-programs"

    # 2. Call Stored Procedure
    try:
        # Smart Retry Logic for State Param "(CT)" vs "CT"
        # CRITICAL FIX: Programs SP requires @MinSeasons parameter
        if mode == 'programs':
            sql_exec = f"EXEC {sp_name} @State=?, @PageNumber=?, @PageSize=?, @SearchTerm=?, @MinSeasons=?"
            params_parens = (f"({state})", 1, 1000, None, 0)
            params_raw = (state, 1, 1000, None, 0)
        else:
            sql_exec = f"EXEC {sp_name} @State=?, @PageNumber=?, @PageSize=?, @SearchTerm=?"
            params_parens = (f"({state})", 1, 1000, None)
            params_raw = (state, 1, 1000, None)
        
        # Attempt 1: With Parens "(CT)"
        cursor.execute(sql_exec, params_parens)
        ranking_rows = cursor.fetchall()
        
        # Attempt 2: Raw "CT" if first attempt failed
        if not ranking_rows:
            cursor.execute(sql_exec, params_raw)
            ranking_rows = cursor.fetchall()

        if not ranking_rows:
            return 0 # No data

        columns = [column[0] for column in cursor.description]
        rankings = [dict(zip(columns, row)) for row in ranking_rows]

    except Exception as e:
        print(f"   Error calling {sp_name} for {state}: {e}")
        return 0

    # 3. Fetch Visual Metadata (Common for both)
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
            "mascot": m[2], "bg_color_raw": m[3], 
            "logo": m[5], "school_logo": m[6], 
            "website": m[7], "helmet": m[9]
        }
        if m[8]: meta_lookup[str(m[8])] = data_pkg
        meta_lookup[m[0].lower()] = data_pkg

    # 4. Merge & Build JSON
    final_items = []
    
    # Check for ID column
    id_col = next((col for col in ['ID', 'TeamID'] if col in columns), None)
    
    # Determine Name Key ('Team' or 'Program')
    name_key = 'Program' if 'Program' in columns else 'Team'

    for rank_row in rankings:
        meta = None
        entity_name = rank_row.get(name_key, 'Unknown')
        
        # Match Logic
        if id_col and str(rank_row[id_col]) in meta_lookup:
            meta = meta_lookup[str(rank_row[id_col])]
        elif entity_name.lower() in meta_lookup:
            meta = meta_lookup[entity_name.lower()]
        else:
            # Fuzzy match (strip state suffix)
            clean = entity_name.lower().replace(f"({state.lower()})", "").strip()
            if clean in meta_lookup:
                meta = meta_lookup[clean]

        # Visuals
        mascot = meta['mascot'] if meta else ""
        bg_color = get_hex_color(meta['bg_color_raw'] if meta else "")
        text_color = determine_text_color(bg_color)
        logo_url = fix_image_path(meta['logo']) if meta else ""
        school_logo = fix_image_path(meta['school_logo']) if meta else ""
        website = meta['website'] if meta else ""

        # Common Item Structure
        item = {
            "rank": rank_row.get('Rank'),
            name_key.lower(): entity_name, # 'team' or 'program'
            "combined": float(rank_row.get('Combined_Score', 0) or 0),
            "margin": float(rank_row.get('Margin', 0) or 0),
            "win_loss": float(rank_row.get('Win_Loss_Pct', 0) or 0),
            "offense": float(rank_row.get('Offense_Score', 0) or 0),
            "defense": float(rank_row.get('Defense_Score', 0) or 0),
            "state": state,
            # Visuals
            "mascot": mascot,
            "backgroundColor": bg_color,
            "textColor": text_color,
            "logoURL": logo_url,
            "schoolLogoURL": school_logo,
            "website": website
        }
        
        # Specific Fields
        if mode == 'teams':
            item['season'] = rank_row.get('Year', 'All-Time')
            item['games_played'] = rank_row.get('Games_Played', 0)
        else:
            item['seasons'] = rank_row.get('Seasons', 0)

        final_items.append(item)

    if not final_items: return 0

    # 5. Save File
    top_item = final_items[0]
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
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Fetching states...")
    cursor.execute("SELECT DISTINCT [State] FROM [HS_Team_Names] WHERE [State] IS NOT NULL AND LEN([State]) = 2 ORDER BY [State]")
    states = [row[0] for row in cursor.fetchall()]
    
    print(f"Processing {len(states)} states...")

    total_teams = 0
    total_programs = 0

    for state in states:
        print(f"Processing {state}...", end=" ", flush=True)
        t_count = process_state_data(cursor, state, 'teams')
        p_count = process_state_data(cursor, state, 'programs')
        print(f"[Teams: {t_count} | Programs: {p_count}]")
        
        total_teams += t_count
        total_programs += p_count

    conn.close()
    print(f"\nDONE. Generated {total_teams} Teams and {total_programs} Programs.")