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
OUTPUT_DIR = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\states\teams"

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
# MAIN LOGIC
# ==========================================
def generate_state_files():
    start_time = time.time()
    print("Starting Web File Generation...")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    conn = get_db_connection()
    cursor = conn.cursor()

    print("Fetching list of states...")
    cursor.execute("SELECT DISTINCT [State] FROM [HS_Team_Names] WHERE [State] IS NOT NULL AND LEN([State]) = 2 ORDER BY [State]")
    states = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(states)} states to process.")

    for state in states:
        # -------------------------------------------------------------
        # A. GET RANKINGS (Smart Retry Logic)
        # -------------------------------------------------------------
        ranking_rows = []
        columns = []
        
        try:
            # Attempt 1: Try with parens "(CT)" - Most likely for SP
            sql_exec = "EXEC GetTeamsByState @State=?, @PageNumber=?, @PageSize=?, @SearchTerm=?"
            params = (f"({state})", 1, 1000, None)
            cursor.execute(sql_exec, params)
            ranking_rows = cursor.fetchall()
            
            if not ranking_rows:
                # Attempt 2: Try RAW state "CT" - Fallback
                # Only run this if the first attempt returned 0 rows
                params = (state, 1, 1000, None)
                cursor.execute(sql_exec, params)
                ranking_rows = cursor.fetchall()

            if not ranking_rows:
                print(f"Skipping {state} (No data returned).")
                continue
                
            print(f"Processing {state}... ({len(ranking_rows)} teams)")
            columns = [column[0] for column in cursor.description]
            rankings = [dict(zip(columns, row)) for row in ranking_rows]

        except Exception as e:
            print(f"Error calling SP for {state}: {e}")
            continue

        # -------------------------------------------------------------
        # B. GET METADATA & BUILD LOOKUP
        # -------------------------------------------------------------
        meta_query = """
            SELECT Team_Name, City, Mascot, PrimaryColor, SecondaryColor, 
                   LogoURL, School_Logo_URL, Website, ID, PhotoUrl
            FROM HS_Team_Names 
            WHERE State = ?
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
            meta_lookup[m[0].lower()] = data_pkg # Exact name match

        # -------------------------------------------------------------
        # C. MERGE DATA
        # -------------------------------------------------------------
        final_items = []
        
        # Check for ID column in rankings
        id_col = next((col for col in ['ID', 'TeamID'] if col in columns), None)

        for rank_row in rankings:
            meta = None
            
            # 1. Try ID Match
            if id_col and str(rank_row[id_col]) in meta_lookup:
                meta = meta_lookup[str(rank_row[id_col])]
            
            # 2. Try Name Match
            if not meta:
                rank_team_lower = rank_row['Team'].lower()
                if rank_team_lower in meta_lookup:
                    meta = meta_lookup[rank_team_lower]
                else:
                    # 3. Try Fuzzy Match (Strip State Suffix)
                    # "New Britain (CT)" -> "new britain"
                    clean_name = rank_team_lower.replace(f"({state.lower()})", "").strip()
                    if clean_name in meta_lookup:
                        meta = meta_lookup[clean_name]

            # Defaults
            mascot = meta['mascot'] if meta else ""
            bg_color = get_hex_color(meta['bg_color_raw'] if meta else "")
            text_color = determine_text_color(bg_color)
            logo_url = fix_image_path(meta['logo']) if meta else ""
            school_logo = fix_image_path(meta['school_logo']) if meta else ""
            website = meta['website'] if meta else ""

            item = {
                "rank": rank_row.get('Rank'),
                "team": rank_row.get('Team'),
                "season": rank_row.get('Year', 'All-Time'),
                "combined": float(rank_row.get('Combined_Score', 0) or 0),
                "margin": float(rank_row.get('Margin', 0) or 0),
                "win_loss": float(rank_row.get('Win_Loss_Pct', 0) or 0),
                "offense": float(rank_row.get('Offense_Score', 0) or 0),
                "defense": float(rank_row.get('Defense_Score', 0) or 0),
                "games_played": rank_row.get('Games_Played', 0),
                "state": state,
                "mascot": mascot,
                "backgroundColor": bg_color,
                "textColor": text_color,
                "logoURL": logo_url,
                "schoolLogoURL": school_logo,
                "website": website
            }
            final_items.append(item)

        if not final_items: continue

        # -------------------------------------------------------------
        # D. SAVE JSON
        # -------------------------------------------------------------
        top_item = final_items[0]
        json_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "type": "teams",
                "yearRange": "All-Time",
                "totalItems": len(final_items),
                "description": f"Top teams for state: ({state})"
            },
            "topItem": top_item,
            "items": final_items
        }

        filename = f"state-teams-{state}.json"
        full_path = os.path.join(OUTPUT_DIR, filename)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)

    conn.close()
    duration = time.time() - start_time
    print(f"\nSUCCESS: Generation complete in {duration:.2f} seconds.")

if __name__ == "__main__":
    generate_state_files()