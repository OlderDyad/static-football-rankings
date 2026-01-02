"""
ENHANCED BULK COLOR CONVERSION SCRIPT
Purpose: Convert ALL non-hex color values (including NULL strings and empty values)
Date: January 2, 2026
"""

import pyodbc
from sqlalchemy import create_engine, text
import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'

# Same COLOR_LOOKUP dictionary as before
COLOR_LOOKUP = {
    'navy': '#003087', 'navy blue': '#003087', 'navyblue': '#003087', 'dark blue': '#003087',
    'royal blue': '#0033A0', 'royalblue': '#0033A0', 'royal': '#0033A0',
    'red': '#FF0000', 'bright red': '#FF0000',
    'cardinal': '#990000', 'cardinal red': '#990000',
    'crimson': '#9E1B32', 'scarlet': '#BB0000', 'scarlet red': '#BB0000',  # Added scarlet red
    'blue': '#0033A0', 'light blue': '#ADD8E6', 'sky blue': '#87CEEB', 'powder blue': '#B0E0E6',
    'green': '#006747', 'dark green': '#006747', 'forest green': '#228B22', 'kelly green': '#4CBB17',
    'gold': '#FFD700', 'golden': '#FFD700', 'yellow': '#FFFF00', 'old gold': '#CFB53B', 'vegas gold': '#C5B358',
    'purple': '#4B0082', 'dark purple': '#4B0082', 'royal purple': '#7851A9', 'violet': '#8B00FF',
    'orange': '#FF6600', 'bright orange': '#FF6600', 'burnt orange': '#BF5700', 'texas orange': '#BF5700',
    'maroon': '#800000', 'dark maroon': '#800000', 'maroon red': '#800000',
    'brown': '#654321', 'dark brown': '#654321',
    'black': '#000000', 'white': '#FFFFFF',
    'gray': '#808080', 'grey': '#808080', 'silver': '#C0C0C0',
    'light gray': '#D3D3D3', 'light grey': '#D3D3D3',
    'dark gray': '#666666', 'dark grey': '#666666',
    'pink': '#FFC0CB', 'hot pink': '#FF69B4',
    'teal': '#008080', 'aqua': '#00FFFF', 'cyan': '#00FFFF', 'turquoise': '#40E0D0',
    'columbia blue': '#B9D9EB', 'cornell red': '#B31B1B', 'harvard crimson': '#A51C30',
    'princeton orange': '#FF8F00', 'yale blue': '#00356B',
}

def convert_color_to_hex(color_value):
    """Convert color name to hex code."""
    if not color_value or str(color_value).strip() in ['', 'NULL', 'None', 'null']:
        return None  # Will be left as NULL in database
    
    color_str = str(color_value).strip()
    
    # Already a hex code - validate and return
    if color_str.startswith('#'):
        if len(color_str) == 7:
            return color_str.upper()
        else:
            return None
    
    # Try to convert color name to hex
    color_lower = color_str.lower().strip()
    
    return COLOR_LOOKUP.get(color_lower, None)

# ==========================================
# CONNECT AND QUERY
# ==========================================
print("=" * 80)
print("ENHANCED BULK COLOR CONVERSION")
print("=" * 80)
print()

print("Connecting to SQL Server...")
connection_string = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver={DRIVER}&trusted_connection=yes"
engine = create_engine(connection_string)

print("Finding ALL teams with non-hex colors...")
print()

# MORE COMPREHENSIVE QUERY
query = text("""
    SELECT 
        ID,
        Team_Name,
        State,
        PrimaryColor,
        SecondaryColor,
        TertiaryColor
    FROM HS_Team_Names
    WHERE 
        -- PrimaryColor needs conversion
        (
            PrimaryColor IS NOT NULL 
            AND (
                PrimaryColor NOT LIKE '#%'  -- Not a hex code at all
                OR LEN(PrimaryColor) != 7    -- Not proper length
                OR PrimaryColor LIKE '%[^0-9A-Fa-f#]%'  -- Contains invalid characters
            )
        )
        OR
        -- SecondaryColor needs conversion  
        (
            SecondaryColor IS NOT NULL 
            AND (
                SecondaryColor NOT LIKE '#%'
                OR LEN(SecondaryColor) != 7
                OR SecondaryColor LIKE '%[^0-9A-Fa-f#]%'
            )
        )
        OR
        -- TertiaryColor needs conversion
        (
            TertiaryColor IS NOT NULL 
            AND (
                TertiaryColor NOT LIKE '#%'
                OR LEN(TertiaryColor) != 7
                OR TertiaryColor LIKE '%[^0-9A-Fa-f#]%'
            )
        )
    ORDER BY State, Team_Name
""")

df = pd.read_sql(query, engine)
total_teams = len(df)

print(f"Found {total_teams:,} teams with non-hex colors")
print()

if total_teams == 0:
    print("✓ All colors are already in hex format!")
    exit()

# ==========================================
# ANALYZE COLOR NAMES
# ==========================================
print("=" * 80)
print("ANALYZING COLOR NAMES IN DATABASE")
print("=" * 80)
print()

color_stats = {}
for idx, row in df.iterrows():
    for col in ['PrimaryColor', 'SecondaryColor', 'TertiaryColor']:
        val = row[col]
        if val and str(val).strip() and not str(val).startswith('#'):
            color_name = str(val).strip().lower()
            if color_name not in color_stats:
                color_stats[color_name] = 0
            color_stats[color_name] += 1

# Sort by frequency
sorted_colors = sorted(color_stats.items(), key=lambda x: x[1], reverse=True)

print("Most common color names in database:")
print()
for color_name, count in sorted_colors[:20]:
    hex_code = COLOR_LOOKUP.get(color_name, '⚠️ UNKNOWN')
    print(f"  {color_name:20} → {hex_code:10} ({count:,} teams)")

print()

if len(sorted_colors) > 20:
    print(f"  ... and {len(sorted_colors) - 20} more unique color names")
    print()

# Count unknown colors
unknown_count = sum(1 for color, _ in sorted_colors if color not in COLOR_LOOKUP)
known_count = len(sorted_colors) - unknown_count

print(f"Summary:")
print(f"  Known colors:   {known_count}")
print(f"  Unknown colors: {unknown_count}")
print()

# ==========================================
# CONFIRMATION
# ==========================================
print("=" * 80)
print()
print(f"Ready to convert colors for {total_teams:,} teams")
print()

if unknown_count > 0:
    print(f"⚠️  Warning: {unknown_count} color names are not in lookup table")
    print("   These will be set to NULL and need manual review")
    print()

response = input("Proceed? (yes/no): ").strip().lower()

if response not in ['yes', 'y']:
    print("Cancelled.")
    exit()

# ==========================================
# BULK CONVERSION
# ==========================================
print()
print("=" * 80)
print("CONVERTING...")
print("=" * 80)
print()

update_sql = text("""
    UPDATE HS_Team_Names
    SET 
        PrimaryColor = :primary,
        SecondaryColor = :secondary,
        TertiaryColor = :tertiary,
        LastUpdated = GETDATE()
    WHERE ID = :id
""")

converted = 0
errors = 0

with engine.begin() as conn:
    for idx, row in df.iterrows():
        try:
            primary_new = convert_color_to_hex(row['PrimaryColor'])
            secondary_new = convert_color_to_hex(row['SecondaryColor'])
            tertiary_new = convert_color_to_hex(row['TertiaryColor'])
            
            conn.execute(update_sql, {
                'id': row['ID'],
                'primary': primary_new,
                'secondary': secondary_new,
                'tertiary': tertiary_new
            })
            
            converted += 1
            
            if converted % 1000 == 0:
                print(f"  Processed {converted:,} / {total_teams:,} teams...")
                
        except Exception as e:
            errors += 1
            print(f"  ❌ Error on {row['Team_Name']}: {e}")

print()
print(f"✓ Converted {converted:,} teams")
if errors > 0:
    print(f"❌ Errors: {errors}")
print()

# ==========================================
# FINAL VERIFICATION
# ==========================================
print("=" * 80)
print("FINAL VERIFICATION")
print("=" * 80)
print()

verify_query = text("""
    SELECT 
        CASE 
            WHEN PrimaryColor IS NULL THEN 'NULL/Empty'
            WHEN PrimaryColor LIKE '#______' AND LEN(PrimaryColor) = 7 THEN 'Valid Hex'
            ELSE 'Invalid'
        END AS PrimaryStatus,
        COUNT(*) AS Count
    FROM HS_Team_Names
    GROUP BY CASE 
            WHEN PrimaryColor IS NULL THEN 'NULL/Empty'
            WHEN PrimaryColor LIKE '#______' AND LEN(PrimaryColor) = 7 THEN 'Valid Hex'
            ELSE 'Invalid'
        END
    ORDER BY Count DESC
""")

result = pd.read_sql(verify_query, engine)
print("PrimaryColor Status:")
print(result.to_string(index=False))
print()

print("=" * 80)
print("✓ DONE")
print("=" * 80)
print()
print("Next: Regenerate JSON and HTML files, then deploy")