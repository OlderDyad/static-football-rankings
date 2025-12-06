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
DOCS_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\latest-season"

# REPO PREFIX
REPO_PREFIX = "/static-football-rankings"

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
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            try:
                return float(row[key_lower])
            except: continue
    return 0.0

def get_int_value(row, keys, default=0):
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            try:
                return int(row[key_lower])
            except: continue
    return default

def get_string_value(row, keys, default=''):
    for k in keys:
        key_lower = k.lower()
        if key_lower in row and row[key_lower] is not None:
            return str(row[key_lower])
    return default

def extract_state_from_name(name):
    if not name: return ""
    import re
    match = re.search(r'\(([A-Z]{2}|Ont)\)$', name.strip())
    if match: return match.group(0)
    return ""

# ==========================================
# GENERATOR LOGIC
# ==========================================
def generate_latest_season():
    start_time = time.time()
    print("=" * 60)
    print("Latest Season JSON Generator")
    print("=" * 60)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        exit(1)

    # 1. Determine Latest Season AND Week (Dynamic)
    print("Finding latest season/week...", end=" ", flush=True)
    
    # This query finds the absolute latest data point in the system
    cursor.execute("""
        SELECT TOP 1 Season, Week 
        FROM HS_Rankings 
        ORDER BY Season DESC, Week DESC
    """)
    
    row = cursor.fetchone()
    if not row:
        print("Error: No ranking data found.")
        return
        
    latest_season = row[0]
    latest_week = row[1]
    print(f"Found: {latest_season} (Week {latest_week})")

    # 2. Fetch Metadata Cache
    print("Fetching metadata cache...", end="", flush=True)
    meta_query = """
        SELECT Team_Name, City, Mascot, PrimaryColor, SecondaryColor, 
               LogoURL, School_Logo_URL, Website, ID, PhotoUrl, State
        FROM HS_Team_Names
    """
    cursor.execute(meta_query)
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

    # 3. Query Rankings (Using dynamic season & week)
    print(f"Processing rankings...", end=" ", flush=True)
    
    sql_query = """
        SELECT TOP 5000
            R.Home AS Team,
            R.Season,
            CAST(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS DECIMAL(18, 3)) AS Combined,
            CAST(R.Max_Min_Margin AS DECIMAL(18, 3)) AS Margin,
            CAST(R.Avg_Of_Avg_Of_Home_Modified_Score AS DECIMAL(18, 3)) AS Win_Loss,
            CAST(R.Offense AS DECIMAL(18, 3)) AS Offense,
            CAST(R.Defense AS DECIMAL(18, 3)) AS Defense,
            (SELECT COUNT(*) FROM HS_Scores S WHERE (S.Home = R.Home OR S.Visitor = R.Home) AND S.Season = R.Season) AS Games_Played,
            R.Home AS ID -- Temporary fallback if ID column missing in rankings, mapped later
        FROM HS_Rankings R
        WHERE R.Season = ? AND R.Week = ?
        ORDER BY Combined DESC
    """
    
    try:
        cursor.execute(sql_query, (latest_season, latest_week))
        ranking_rows = cursor.fetchall()
        
        if not ranking_rows:
            print("No data found.")
            return

        columns = [column[0].lower() for column in cursor.description]
        rankings = [dict(zip(columns, row)) for row in ranking_rows]
        print(f"Done ({len(rankings)} teams).")

    except Exception as e:
        print(f"\nError querying rankings: {e}")
        return

    # 4. Merge Data
    final_items = []
    # Determine which ID column to use for lookup
    id_col = 'id' if 'id' in columns else ('teamid' if 'teamid' in columns else None)
    
    for i, rank_row in enumerate(rankings):
        team_name = get_string_value(rank_row, ['team'], 'Unknown')
        
        # Match Metadata
        meta = None
        
        # Try ID match first (if ID column exists in rankings)
        if id_col and str(rank_row.get(id_col, '')) in meta_lookup:
            meta = meta_lookup[str(rank_row.get(id_col))]
        # Fallback to Name match
        elif team_name.lower() in meta_lookup:
            meta = meta_lookup[team_name.lower()]
        
        # Extract visuals
        mascot = meta['mascot'] if meta else ""
        bg_color = get_hex_color(meta['bg_color_raw'] if meta else "")
        text_color = determine_text_color(bg_color)
        logo_url = fix_image_path(meta['logo'] if meta else "")
        school_logo = fix_image_path(meta['school_logo'] if meta else "")
        website = meta['website'] if meta else ""
        
        # State Logic
        state_val = meta['state'] if meta else ""
        if not state_val: state_val = extract_state_from_name(team_name)

        item = {
            "rank": i + 1,
            "team": team_name,
            "season": latest_season,
            "combined": get_stat_value(rank_row, ['combined', 'combined_score']),
            "margin": get_stat_value(rank_row, ['margin']),
            "win_loss": get_stat_value(rank_row, ['win_loss']),
            "offense": get_stat_value(rank_row, ['offense']),
            "defense": get_stat_value(rank_row, ['defense']),
            "games_played": get_int_value(rank_row, ['games_played']),
            "state": state_val,
            "mascot": mascot,
            "backgroundColor": bg_color,
            "textColor": text_color,
            "logoURL": logo_url,
            "schoolLogoURL": school_logo,
            "website": website
        }
        final_items.append(item)

    # 5. Save JSON
    if not os.path.exists(DOCS_ROOT): os.makedirs(DOCS_ROOT)
    
    # Save as 'latest-season-teams.json'
    file_path = os.path.join(DOCS_ROOT, "latest-season-teams.json")
    
    json_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "type": "teams",
            "yearRange": str(latest_season),
            "totalItems": len(final_items),
            "description": f"Rankings for {latest_season} Season (Week {latest_week})"
        },
        "topItem": final_items[0] if final_items else None,
        "items": final_items
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)

    print(f"✓ Saved: {file_path}")
    print(f"Duration: {time.time()-start_time:.2f}s")

if __name__ == "__main__":
    generate_latest_season()