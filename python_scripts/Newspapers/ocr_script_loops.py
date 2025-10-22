import re
import os
import pandas as pd
import pyodbc
import sqlalchemy
import unicodedata
from fuzzywuzzy import process, fuzz
from sqlalchemy import text
from datetime import datetime

# Database Connection
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;"
engine = sqlalchemy.create_engine(f"mssql+pyodbc://MCKNIGHTS-PC\\SQLEXPRESS01/hs_football_database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes")

# Track unrecognized teams for summary
unrecognized_teams = []

def clean_text(text):
    """Normalizes team name (removes extra spaces, special characters, normalizes Unicode)."""
    text = text.strip()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s']", "", text)  # Allow apostrophes
    text = re.sub(r"\s+", " ", text)  # Ensure single spaces
    return text.lower()

def get_newspaper_region(source_filename):
    """Dynamically determine newspaper region from the filename."""
    # Remove file extension
    base_name = os.path.splitext(source_filename)[0]
    
    # Split by underscore and replace with spaces for readability
    parts = base_name.split('_')
    
    # Try to find a date pattern to separate newspaper name from date
    date_pattern = re.search(r'(\d{4}_\d{2}_\d{2})', base_name)
    
    if date_pattern:
        # Find where the date starts
        date_start = base_name.find(date_pattern.group(1))
        if date_start > 0:
            # Extract everything before the date as the newspaper name
            newspaper_name = base_name[:date_start-1].replace('_', ' ')
            return newspaper_name
    
    # Fallback - use the first 2-3 parts of the filename as the newspaper name
    if len(parts) >= 3:
        return ' '.join(parts[:3])
    elif len(parts) >= 2:
        return ' '.join(parts[:2])
    else:
        return parts[0]

# Load Data from SQL - Only load aliases with newspaper region
try:
    alias_df = pd.read_sql(
        "SELECT Alias_Name, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Name_Alias WHERE Newspaper_Region IS NOT NULL", 
        engine
    )
    
    # Group aliases by newspaper region
    newspaper_aliases = {}
    for _, row in alias_df.iterrows():
        region = row['Newspaper_Region']
        if region not in newspaper_aliases:
            newspaper_aliases[region] = {}
        
        # Add to the region's alias dictionary (normalized)
        newspaper_aliases[region][clean_text(row['Alias_Name'])] = row['Standardized_Name']

    # Print loaded aliases for verification
    for region, aliases in newspaper_aliases.items():
        print(f"Loaded {len(aliases)} aliases for {region}")
except Exception as e:
    print(f"❌ Error loading aliases from database: {e}")
    newspaper_aliases = {}

def get_standard_team_name(newspaper_name, newspaper_region):
    """
    Attempts to match a team name from a newspaper OCR result to a standardized name.
    Only uses exact matches from the specific newspaper region's alias table.
    """
    if not newspaper_name or newspaper_name.strip() == '':
        return newspaper_name
    
    normalized_name = clean_text(newspaper_name)
    print(f"🔍 Normalized: '{newspaper_name}' → '{normalized_name}'")
    
    # Check if we have aliases for this newspaper region
    if newspaper_region not in newspaper_aliases:
        print(f"⚠️ No aliases defined for newspaper region: {newspaper_region}")
        # Add to unrecognized teams list
        unrecognized_teams.append((newspaper_name, newspaper_region))
        
        # Log the unrecognized name for this region
        try:
            with engine.connect() as connection:
                connection.execute(text("""
                    INSERT INTO dbo.HS_Team_Names_Review (Unrecognized_Name, Newspaper_Region) 
                    VALUES (:name, :region)
                """), {"name": newspaper_name, "region": newspaper_region})
        except Exception as e:
            print(f"❌ Error logging to database: {e}")
            
        return newspaper_name
    
    # Check for exact match in the newspaper's alias dictionary
    region_aliases = newspaper_aliases[newspaper_region]
    if normalized_name in region_aliases:
        return region_aliases[normalized_name]
    
    # No match found - log for review
    print(f"⚠️ Unrecognized team: {newspaper_name} - Needs manual verification for {newspaper_region}")
    unrecognized_teams.append((newspaper_name, newspaper_region))
    
    try:
        with engine.connect() as connection:
            connection.execute(text("""
                INSERT INTO dbo.HS_Team_Names_Review (Unrecognized_Name, Newspaper_Region) 
                VALUES (:name, :region)
            """), {"name": newspaper_name, "region": newspaper_region})
    except Exception as e:
        print(f"❌ Error logging to database: {e}")
        
    return newspaper_name  # Return the original name as a placeholder

def extract_date_from_filename(filename):
    """Extract date from filename in format Press_and_Sun_Bulletin_1989_09_17_42.txt"""
    match = re.search(r"(\d{4})_(\d{2})_(\d{2})", filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d"), year
        except ValueError:
            print(f"⚠️ Invalid date in filename: {filename}")
            return None, None
    return None, None

# Process OCR Results
STAGED_FOLDER = "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"

# Find OCR text files in the Staged folder
ocr_files = [f for f in os.listdir(STAGED_FOLDER) if f.endswith(".txt")]

if not ocr_files:
    print("❌ No OCR result files found in Staged folder. Exiting.")
    exit()

print(f"📂 Found {len(ocr_files)} OCR files to process")
all_cleaned_data = []

# Process each OCR file
for ocr_file in ocr_files:
    ocr_results_file = os.path.join(STAGED_FOLDER, ocr_file)
    print(f"\n📄 Processing: {ocr_file}")
    
    # Extract date from filename
    game_date, season = extract_date_from_filename(ocr_file)
    source = ocr_file.replace('_', ' ')
    newspaper_region = get_newspaper_region(ocr_file)
    
    print(f"📰 Newspaper Region: {newspaper_region}")
    
    if not game_date or not season:
        print(f"⚠️ Could not extract date from filename: {ocr_file} - Using placeholder")
        game_date = "1900-01-01"  # Placeholder date
        season = 1900  # Placeholder season
    
    print(f"📅 Extracted date: {game_date}, Season: {season}")
    
    # Read OCR results
    try:
        with open(ocr_results_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error reading OCR file: {e}")
        continue
    
    # Process each line to extract scores
    games_found = 0
    for line in lines:
        match = re.match(r"(.+?)\s+(\d+)\s*,\s*(.+?)\s+(\d+)", line.strip())
        if match:
            home_team = get_standard_team_name(match.group(1).strip(), newspaper_region)
            visitor_team = get_standard_team_name(match.group(3).strip(), newspaper_region)

            try:
                home_score = int(match.group(2))
                visitor_score = int(match.group(4))

                # Handle impossible score (1) → Forfeit case
                forfeit = False
                if home_score == 1 or visitor_score == 1:
                    forfeit = True
                    home_score, visitor_score = (1, 0) if home_score == 1 else (0, 1)

                # Add date, season, and source to each game record
                all_cleaned_data.append([
                    home_team, 
                    home_score, 
                    visitor_team, 
                    visitor_score, 
                    forfeit,
                    game_date,
                    season,
                    source,
                    newspaper_region
                ])
                games_found += 1

            except ValueError:
                print(f"⚠️ Skipping invalid score line: {line.strip()}")
    
    print(f"✅ Extracted {games_found} games from {ocr_file}")

# Save all cleaned data to CSV for review
if all_cleaned_data:
    output_csv = os.path.join(STAGED_FOLDER, "cleaned_scores.csv")
    df = pd.DataFrame(
        all_cleaned_data, 
        columns=["Home", "Home_Score", "Visitor", "Visitor_Score", "Forfeit", 
                 "Date", "Season", "Source", "Newspaper_Region"]
    )
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Process completed. {len(all_cleaned_data)} games saved to {output_csv}")
else:
    print("\n⚠️ No valid games found to process")

# Generate summary report of unrecognized teams
if unrecognized_teams:
    print("\n===== UNRECOGNIZED TEAM NAMES =====")
    
    # Create a unique list of unrecognized teams
    unique_unrecognized = list(set(unrecognized_teams))
    unique_unrecognized.sort(key=lambda x: (x[1], x[0]))  # Sort by region, then name
    
    # Display in console
    current_region = None
    for team, region in unique_unrecognized:
        if region != current_region:
            print(f"\n{region}:")
            current_region = region
        print(f"- {team}")
    
    print(f"\nFound {len(unique_unrecognized)} unique unrecognized team names across {len(ocr_files)} files")
    
    # Save to CSV for easy review
    unrecognized_csv = os.path.join(STAGED_FOLDER, "unrecognized_teams.csv")
    unrecognized_df = pd.DataFrame(unique_unrecognized, columns=["Team", "Newspaper_Region"])
    unrecognized_df.to_csv(unrecognized_csv, index=False)
    
    print(f"Unrecognized teams saved to: {unrecognized_csv}")
    
    # Also create a SQL-ready script for adding these teams
    sql_file = os.path.join(STAGED_FOLDER, "add_missing_teams.sql")
    with open(sql_file, "w") as f:
        f.write("-- Execute this script to add missing team name aliases\n")
        f.write("-- Review and update standardized names as needed before executing\n\n")
        f.write("INSERT INTO dbo.HS_Team_Name_Alias (Alias_Name, Standardized_Name, Newspaper_Region)\nVALUES\n")
        
        for i, (team, region) in enumerate(unique_unrecognized):
            comma = "," if i < len(unique_unrecognized) - 1 else ";"
            f.write(f"    ('{team}', '*** UPDATE ME ***', '{region}'){comma}\n")
    
    print(f"SQL template for adding missing teams saved to: {sql_file}")
else:
    print("\n✅ All team names were recognized successfully")










