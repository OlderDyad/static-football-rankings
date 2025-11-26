import os
import shutil
import pyodbc
import re

# ==========================================
# CONFIGURATION
# ==========================================
DROP_FOLDER = r"C:\Users\demck\OneDrive\Desktop\HS_Image_Drop"

# CRITICAL UPDATE: Pointing to the 'docs' folder so the website can see it
DEST_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs"
WEB_REL_PATH = "images/Teams"

SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'

ID_COLUMN = 'ID' 

TYPE_MAP = {
    'Mascot': 'LogoURL',
    'School': 'School_Logo_URL',
    'Helmet': 'PhotoUrl'
}

# ==========================================
# MAIN SCRIPT
# ==========================================
def clean_name(text):
    """Makes text safe for folder names (No parens, no spaces)"""
    if not text: return "Unknown"
    clean = re.sub(r'[^a-zA-Z0-9]', '-', text)
    return re.sub(r'-+', '-', clean).strip('-')

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

    print(f"Found {len(files)} images. Processing by ID...")
    print("------------------------------------------------")

    for filename in files:
        try:
            # 1. Parse Filename: ID_Name_Type.png
            name_no_ext = os.path.splitext(filename)[0]
            parts = name_no_ext.split('_')

            if len(parts) < 2:
                print(f"SKIPPING: {filename} (Format must be: ID_Name_Type.png)")
                continue

            team_id = parts[0]
            img_type = parts[-1] 

            if not team_id.isdigit():
                print(f"SKIPPING: {filename} (Start of filename '{team_id}' is not a number)")
                continue

            if img_type not in TYPE_MAP:
                print(f"SKIPPING: {filename} (Unknown Type '{img_type}')")
                continue

            # 2. QUERY DB
            query = f"SELECT [State], [City], [Team_Name] FROM [HS_Team_Names] WHERE [{ID_COLUMN}] = ?"
            cursor.execute(query, (team_id,))
            row = cursor.fetchone()

            if not row:
                print(f" > ERROR: ID {team_id} not found in database.")
                continue

            # Safeguard against NULLs
            db_state = row[0] if row[0] else "Unknown"
            db_city = row[1] if row[1] else "Unknown"
            db_team = row[2] if row[2] else "Unknown"

            # 3. CONSTRUCT PATHS
            safe_city = clean_name(db_city)
            safe_team = clean_name(db_team)
            folder_name = f"{safe_city}_{safe_team}"
            
            # PHYSICAL PATH: .../docs/images/Teams/State/Folder/
            dest_dir = os.path.join(DEST_ROOT, "images", "Teams", db_state, folder_name)
            
            # WEB PATH: images/Teams/State/Folder/Filename (Database stores this)
            web_path = f"{WEB_REL_PATH}/{db_state}/{folder_name}/{filename}"

            # 4. MOVE FILE
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
                print(f"   Created Folder: {dest_dir}")

            src_file = os.path.join(DROP_FOLDER, filename)
            dest_file = os.path.join(dest_dir, filename)
            shutil.move(src_file, dest_file)

            # 5. UPDATE DB
            target_col = TYPE_MAP[img_type]
            
            update_sql = f"""
                UPDATE [HS_Team_Names] 
                SET [{target_col}] = ?, [LastUpdated] = GETDATE()
                WHERE [{ID_COLUMN}] = ?
            """
            cursor.execute(update_sql, (web_path, team_id))
            conn.commit()

            print(f"SUCCESS: {filename}")
            print(f"   -> Moved to: docs/images/Teams/{db_state}/{folder_name}")

        except Exception as e:
            print(f"ERROR processing {filename}: {e}")

    conn.close()
    print("------------------------------------------------")
    print("Ingest Complete.")

if __name__ == "__main__":
    ingest_images()