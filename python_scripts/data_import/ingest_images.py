import os
import shutil
import pyodbc
import re

# ==========================================
# CONFIGURATION
# ==========================================
DROP_FOLDER = r"C:\Users\demck\OneDrive\Desktop\HS_Image_Drop"
DEST_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
WEB_REL_PATH = "images/Teams"

SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'

TYPE_MAP = {
    'Mascot': 'LogoURL',
    'School': 'School_Logo_URL',
    'Helmet': 'PhotoUrl'
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def sanitize(text):
    """Removes non-alphanumeric chars and makes lowercase."""
    if not text: return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def find_db_match(cursor, state, city_chunk, school_chunk):
    # 1. Fetch all teams for this state
    query = "SELECT [City], [Team_Name] FROM [HS_Team_Names] WHERE [State] = ?"
    cursor.execute(query, (state,))
    rows = cursor.fetchall()

    target_city_clean = sanitize(city_chunk)
    # We construct the target including the state suffix "(CT)"
    target_team_clean = sanitize(f"{school_chunk} {state}") 

    # For Debugging: Keep track of "almost matches"
    candidates_in_city = []

    for row in rows:
        db_city = row[0]
        db_team = row[1]
        
        db_city_clean = sanitize(db_city)
        db_team_clean = sanitize(db_team)

        # Check for City Match
        if db_city_clean == target_city_clean:
            # We found the city! Add to candidate list for debugging
            candidates_in_city.append(db_team)
            
            # NOW Check for Team Match
            if db_team_clean == target_team_clean:
                return db_city, db_team, [] # Exact match found

    # If we finish the loop with no match, return the candidates we DID find
    return None, None, candidates_in_city

# ==========================================
# MAIN SCRIPT
# ==========================================
def ingest_images():
    print(f"Scanning: {DROP_FOLDER}...")
    
    try:
        conn = pyodbc.connect(f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;')
        cursor = conn.cursor()
        print("Connected to SQL Server.")
    except Exception as e:
        print(f"SQL Connection Failed: {e}")
        return

    files = [f for f in os.listdir(DROP_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not files:
        print("No images found in Drop Folder.")
        return

    print(f"Found {len(files)} images. Processing...")
    print("------------------------------------------------")

    for filename in files:
        try:
            name_no_ext = os.path.splitext(filename)[0]
            parts = name_no_ext.split('_')

            if len(parts) != 4:
                print(f"SKIPPING: {filename} (Format must be State_City_School_Type)")
                continue

            state_abr = parts[0]
            city_chunk = parts[1]
            school_chunk = parts[2]
            img_type = parts[3]

            if img_type not in TYPE_MAP:
                print(f"SKIPPING: {filename} (Unknown Type '{img_type}')")
                continue

            # 2. FIND MATCH
            real_city, real_team_name, candidates = find_db_match(cursor, state_abr, city_chunk, school_chunk)

            if not real_team_name:
                print(f" > NO MATCH for file: {school_chunk} ({state_abr})")
                
                # --- DIAGNOSTIC OUTPUT ---
                target_look = sanitize(f"{school_chunk} {state_abr}")
                print(f"   (Script looked for sanitized string: '{target_look}')")
                
                if candidates:
                    print(f"   I found the CITY '{city_chunk}', but the TEAMS in the DB are:")
                    for c in candidates:
                        print(f"     - '{c}' (Sanitized: '{sanitize(c)}')")
                else:
                    print(f"   I could not even find the city '{city_chunk}' in state '{state_abr}'.")
                print("------------------------------------------------")
                continue

            # 3. MOVE & UPDATE (Only runs if match found)
            folder_name = f"{city_chunk}_{school_chunk}"
            dest_dir = os.path.join(DEST_ROOT, "images", "Teams", state_abr, folder_name)
            web_path = f"{WEB_REL_PATH}/{state_abr}/{folder_name}/{filename}"

            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            
            src_file = os.path.join(DROP_FOLDER, filename)
            dest_file = os.path.join(dest_dir, filename)
            shutil.move(src_file, dest_file)

            target_col = TYPE_MAP[img_type]
            update_sql = f"""
                UPDATE [HS_Team_Names]
                SET [{target_col}] = ?, [LastUpdated] = GETDATE()
                WHERE [State] = ? AND [City] = ? AND [Team_Name] = ?
            """
            cursor.execute(update_sql, (web_path, state_abr, real_city, real_team_name))
            conn.commit()
            print(f"SUCCESS: {filename} -> {real_team_name}")

        except Exception as e:
            print(f"ERROR processing {filename}: {e}")

    conn.close()
    print("Ingest Complete.")

if __name__ == "__main__":
    ingest_images()