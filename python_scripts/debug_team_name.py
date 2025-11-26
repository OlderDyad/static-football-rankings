import pyodbc
import os

# ==========================================
# CONFIGURATION
# ==========================================
SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'

# The root folder where your website lives locally
WEB_ROOT = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings"

def check_team_data():
    conn = pyodbc.connect(f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;')
    cursor = conn.cursor()

    target_city = 'New Britain'
    print(f"\n--- DIAGNOSTIC REPORT FOR CITY: '{target_city}' ---")
    
    # Fetch ALL visual data columns including COLORS
    query = """
    SELECT ID, Team_Name, City, State, Mascot, 
           LogoURL, School_Logo_URL, PhotoUrl,
           PrimaryColor, SecondaryColor, TertiaryColor
    FROM HS_Team_Names 
    WHERE City = ?
    """
    cursor.execute(query, (target_city,))
    rows = cursor.fetchall()

    if not rows:
        print(f"❌ No rows found for City = '{target_city}'")
        conn.close()
        return

    for row in rows:
        print(f"\n[ ID: {row.ID} ] ------------------------------------------")
        print(f"1. TEAM IDENTITY")
        print(f"   - Name in DB:   '{row.Team_Name}'")
        print(f"   - City:         '{row.City}'")
        print(f"   - State:        '{row.State}'")
        print(f"   - Mascot Name:  '{row.Mascot}'  <-- {('MISSING' if not row.Mascot else 'OK')}")

        print(f"\n2. SCHOOL COLORS (Banner Styling)")
        # Check Primary Color (Critical for Banner Background)
        p_status = "✅ OK" if row.PrimaryColor else "❌ MISSING (Banner will default to Dark Grey)"
        print(f"   - Primary:      '{row.PrimaryColor}'  <-- {p_status}")
        print(f"   - Secondary:    '{row.SecondaryColor}'")
        print(f"   - Tertiary:     '{row.TertiaryColor}'")

        print(f"\n3. IMAGE FILE VALIDATION")
        
        # tuple of (Label, DB_Value)
        images_to_check = [
            ("Logo URL", row.LogoURL),
            ("School Logo", row.School_Logo_URL),
            ("Helmet Photo", row.PhotoUrl)
        ]

        for label, db_path in images_to_check:
            if not db_path:
                print(f"   - {label}: [NULL] in Database")
                continue
            
            # Construct full local path
            # DB path is usually "images/Teams/..." (forward slashes)
            # We need to convert to Windows backslashes for checking
            local_path_part = db_path.replace('/', '\\')
            full_local_path = os.path.join(WEB_ROOT, local_path_part)
            
            exists = os.path.exists(full_local_path)
            status = "✅ FOUND" if exists else "❌ FILE MISSING"
            
            print(f"   - {label}:")
            print(f"       DB Value:   {db_path}")
            print(f"       Local Path: {full_local_path}")
            print(f"       Status:     {status}")

    conn.close()
    print("\n----------------------------------------------------")

if __name__ == "__main__":
    check_team_data()