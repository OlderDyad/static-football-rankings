import json
import os

# ==========================================
# CONFIGURATION
# ==========================================
# Path to your repository root
REPO_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings"

# Path to the JSON file we want to check
JSON_FILE_PATH = os.path.join(REPO_ROOT, r"docs\data\states\teams\state-teams-CT.json")

# The web prefix to strip off when looking for local files
WEB_PREFIX = "/static-football-rankings/"

# Your GitHub Pages base URL (Update if different)
LIVE_SITE_BASE = "https://olderdyad.github.io"

def check_paths():
    print(f"--- DIAGNOSTIC: Checking Image Paths for {os.path.basename(JSON_FILE_PATH)} ---")
    
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ ERROR: JSON file not found at: {JSON_FILE_PATH}")
        return

    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    top_item = data.get('topItem')
    if not top_item:
        print("❌ ERROR: No 'topItem' found in JSON.")
        return

    print(f"Top Team: {top_item.get('team')}")
    
    # Images to check
    images = {
        "Logo URL": top_item.get('logoURL'),
        "School Logo": top_item.get('schoolLogoURL')
    }

    for label, web_path in images.items():
        print(f"\nChecking {label}...")
        print(f"   Web Path:   {web_path}")

        if not web_path:
            print(f"   ❌ Status:   MISSING in JSON (Value is empty)")
            continue

        # Convert Web Path to Local Windows Path
        # 1. Remove prefix
        if web_path.startswith(WEB_PREFIX):
            relative_path = web_path[len(WEB_PREFIX):]
        else:
            relative_path = web_path.lstrip('/')
        
        # 2. Add 'docs' (because that's where your site lives)
        #    and convert forward slashes to backslashes
        local_rel_path = os.path.join("docs", relative_path.replace('/', os.sep))
        full_local_path = os.path.join(REPO_ROOT, local_rel_path)
        
        print(f"   Local Path: {full_local_path}")

        # 3. Check Existence
        if os.path.exists(full_local_path):
            print(f"   ✅ Status:   FOUND on disk.")
            
            # 4. Check Case Sensitivity (Critical for GitHub Pages)
            directory = os.path.dirname(full_local_path)
            filename = os.path.basename(full_local_path)
            actual_files = os.listdir(directory)
            
            if filename in actual_files:
                 print(f"   ✅ Casing:   MATCH (File is valid)")
                 
                 # 5. Print Live URL for testing
                 live_url = f"{LIVE_SITE_BASE}{web_path}"
                 print(f"   🌍 Test Link: {live_url}")
                 print(f"      (Click this link to see if it works on the web)")
                 
            else:
                 # Find the actual casing
                 actual_match = next((f for f in actual_files if f.lower() == filename.lower()), "Unknown")
                 print(f"   ❌ Casing:   MISMATCH!")
                 print(f"      JSON asks for: {filename}")
                 print(f"      Disk has:      {actual_match}")
                 print(f"      (This will BREAK on the website!)")
        else:
            print(f"   ❌ Status:   NOT FOUND on disk.")
            print(f"      (Did you push the 'docs/images' folder to GitHub?)")

if __name__ == "__main__":
    check_paths()