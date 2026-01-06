import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, text

# ==========================================
# CONFIGURATION
# ==========================================
SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'
JSON_KEY_FILE = 'service_account.json'
SHEET_NAME = 'HS Football Data Cleaning'
TAB_NAME = 'Missing_Data'

# ==========================================
# COLOR CONVERSION LOOKUP TABLE
# ==========================================
COLOR_LOOKUP = {
    # Navy variations
    'navy': '#003087',
    'navy blue': '#003087',
    'navyblue': '#003087',
    'dark blue': '#003087',
    
    # Royal Blue variations
    'royal blue': '#0033A0',
    'royalblue': '#0033A0',
    'royal': '#0033A0',
    
    # Red variations
    'red': '#FF0000',
    'bright red': '#FF0000',
    'cardinal': '#990000',
    'cardinal red': '#990000',
    'crimson': '#9E1B32',
    'scarlet': '#BB0000',
    
    # Blue variations
    'blue': '#0033A0',
    'light blue': '#ADD8E6',
    'sky blue': '#87CEEB',
    'powder blue': '#B0E0E6',
    
    # Green variations
    'green': '#006747',
    'dark green': '#006747',
    'forest green': '#228B22',
    'kelly green': '#4CBB17',
    
    # Gold/Yellow variations
    'gold': '#FFD700',
    'golden': '#FFD700',
    'yellow': '#FFFF00',
    'old gold': '#CFB53B',
    'vegas gold': '#C5B358',
    
    # Purple variations
    'purple': '#4B0082',
    'dark purple': '#4B0082',
    'royal purple': '#7851A9',
    'violet': '#8B00FF',
    
    # Orange variations
    'orange': '#FF6600',
    'bright orange': '#FF6600',
    'burnt orange': '#BF5700',
    'texas orange': '#BF5700',
    
    # Maroon variations
    'maroon': '#800000',
    'dark maroon': '#800000',
    'maroon red': '#800000',

    # Burgundy variations
    'burgundy': '#800020',
    'burgundy red': '#800020',
    'wine': '#722F37',
    'wine red': '#722F37',
    
    # Brown variations
    'brown': '#654321',
    'dark brown': '#654321',
    
    # Black/White/Gray
    'black': '#000000',
    'white': '#FFFFFF',
    'gray': '#808080',
    'grey': '#808080',
    'silver': '#C0C0C0',
    'light gray': '#D3D3D3',
    'light grey': '#D3D3D3',
    'dark gray': '#666666',
    'dark grey': '#666666',
    
    # Pink variations
    'pink': '#FFC0CB',
    'hot pink': '#FF69B4',
    
    # Teal variations
    'teal': '#008080',
    'aqua': '#00FFFF',
    'cyan': '#00FFFF',
    'turquoise': '#40E0D0',
    
    # Special school colors
    'columbia blue': '#B9D9EB',
    'cornell red': '#B31B1B',
    'harvard crimson': '#A51C30',
    'princeton orange': '#FF8F00',
    'yale blue': '#00356B',

    # Additional common school colors
    'columbia blue': '#B9D9EB',      # Light blue (Columbia, UNC)
    'burnt orange': '#BF5700',       # Texas Longhorns
    'carolina blue': '#7BAFD4',      # UNC
    'michigan blue': '#00274C',      # Michigan
    'tennessee orange': '#FF8200',   # Tennessee Volunteers
    'penn state blue': '#041E42',    # Penn State
    'clemson orange': '#F66733',     # Clemson Tigers
    'notre dame gold': '#C99700',    # Notre Dame
    'florida orange': '#FA4616',     # Florida Gators
    'florida blue': '#0021A5',       # Florida Gators
    'alabama crimson': '#9E1B32',    # Alabama Crimson Tide
    'georgia red': '#BA0C2F',        # Georgia Bulldogs
    'ohio state scarlet': '#BB0000', # Ohio State
    'usc cardinal': '#990000',       # USC Trojans
    'usc gold': '#FFC72C',           # USC Trojans
}

def convert_color_to_hex(color_value):
    """
    Convert a color name or existing hex code to a valid hex code.
    
    Args:
        color_value: String from spreadsheet (e.g., "Navy Blue", "#003087", "")
    
    Returns:
        Hex code string or original value if not found
    """
    if not color_value or str(color_value).strip() == '':
        return ''
    
    color_str = str(color_value).strip()
    
    # Already a hex code - validate and return
    if color_str.startswith('#'):
        # Validate format
        if len(color_str) == 7 and all(c in '0123456789ABCDEFabcdef' for c in color_str[1:]):
            return color_str.upper()
        else:
            print(f"  ⚠️  Invalid hex code: {color_str} - leaving as-is")
            return color_str
    
    # Try to convert color name to hex
    color_lower = color_str.lower().strip()
    
    if color_lower in COLOR_LOOKUP:
        converted = COLOR_LOOKUP[color_lower]
        print(f"  ✓ Converted '{color_str}' → {converted}")
        return converted
    else:
        print(f"  ⚠️  Unknown color name: '{color_str}' - leaving as-is")
        print(f"     Consider adding to COLOR_LOOKUP dictionary")
        return color_str

# ==========================================
# STEP 1: CONNECT TO GOOGLE SHEETS
# ==========================================
print("Connecting to Google Sheets...")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
client = gspread.authorize(creds)

try:
    sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)
except gspread.WorksheetNotFound:
    print(f"Error: Could not find tab '{TAB_NAME}'. Check spelling.")
    exit()

# Get all records
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ==========================================
# STEP 2: FILTER FOR "SYNC" ROWS
# ==========================================
# Normalize headers
df.columns = [c.strip() for c in df.columns]
lower_cols = [c.lower() for c in df.columns]

if 'sync' not in lower_cols:
    print("WARNING: No 'Sync' column found. Please add a column header named 'Sync'.")
    exit()

# Identify columns
id_col_name = next(c for c in df.columns if c.lower() == 'id')
sync_col_name = next(c for c in df.columns if c.lower() == 'sync')

# Filter for rows marked 'x'
rows_to_update = df[df[sync_col_name].astype(str).str.lower().isin(['x', 'yes', 'true', '1'])]

count = len(rows_to_update)
if count == 0:
    print("No rows marked for sync.")
    exit()

print(f"Found {count} rows to update.")
print("")

# ==========================================
# STEP 3: UPDATE SQL SERVER (WITH COLOR CONVERSION)
# ==========================================
print("Connecting to SQL Server...")
connection_string = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver={DRIVER}&trusted_connection=yes"
engine = create_engine(connection_string)

print("Updating database...")
print("")

with engine.begin() as conn:
    for index, row in rows_to_update.iterrows():
        
        row_id = row[id_col_name]
        team_name = row['Team_Name']
        
        print(f"Processing ID {row_id}: {team_name}")
        
        # ==========================================
        # COLOR CONVERSION LOGIC
        # ==========================================
        primary_color = convert_color_to_hex(row['PrimaryColor'])
        secondary_color = convert_color_to_hex(row['SecondaryColor'])
        tertiary_color = convert_color_to_hex(row['TertiaryColor'])
        
        # SMART LOGIC:
        # We REMOVED [Team_Name] from the SET clause below.
        # This prevents the Trigger from blocking the update, even if the name in the Sheet 
        # is slightly different from the DB.
        sql_update = text("""
                    UPDATE [dbo].[HS_Team_Names]
                    SET 
                        -- SECTION 1: USER MANAGED FIELDS (Overwrite DB)
                        [City] = :city,
                        [State] = :state,
                        [Mascot] = :mascot,
                        [PrimaryColor] = :p_color,
                        [SecondaryColor] = :s_color,
                        [TertiaryColor] = :t_color,
                        [Stadium] = :stadium,        
                        [Website] = :website,
                        [YearFounded] = :founded,
                        [Latitude] = :lat,
                        [Longitude] = :long,
                        
                        -- SECTION 2: SCRIPT MANAGED FIELDS (Preserve DB)
                        [LogoURL] = CASE WHEN :logo = '' THEN [LogoURL] ELSE :logo END,
                        [School_Logo_URL] = CASE WHEN :school_logo = '' THEN [School_Logo_URL] ELSE :school_logo END,
                        [PhotoUrl] = CASE WHEN :photo = '' THEN [PhotoUrl] ELSE :photo END,
                        [Has_Team_Page] = ISNULL([Has_Team_Page], 0),
                        [Team_Page_URL] = ISNULL([Team_Page_URL], ''),
                        
                        [LastUpdated] = GETDATE()
                    WHERE [ID] = :id
                """)

        # HELPER: Handle numbers
        def clean_num(val):
            return val if val != '' else None

        # Execute parameters (Note: 'team' is NOT passed, colors are converted)
        conn.execute(sql_update, {
            'city': row['City'],
            'state': row['State'],
            'mascot': row['Mascot'],
            'p_color': primary_color,      # ← Converted hex code
            's_color': secondary_color,    # ← Converted hex code
            't_color': tertiary_color,     # ← Converted hex code
            'stadium': row['Stadium'],
            'website': row['Website'],
            'founded': clean_num(row['YearFounded']),
            'lat': clean_num(row['Latitude']),
            'long': clean_num(row['Longitude']),
            'logo': str(row['LogoURL']),
            'school_logo': str(row['School_Logo_URL']),
            'photo': str(row['PhotoUrl']),
            'id': row_id
        })
        
        print(f"  ✓ Updated ID {row_id}")
        print("")

print("")
print("=" * 60)
print("SUCCESS: SQL Database updated with color conversion.")
print("=" * 60)
print("")
print("TIPS:")
print("1. If you see '⚠️ Unknown color name' warnings, add them to COLOR_LOOKUP")
print("2. Colors are automatically converted: 'Navy Blue' → '#003087'")
print("3. Existing hex codes are validated and preserved")
print("")
