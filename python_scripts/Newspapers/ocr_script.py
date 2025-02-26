import re
import os
import pandas as pd
import pyodbc
import sqlalchemy
import unicodedata
from fuzzywuzzy import process, fuzz
from sqlalchemy import text

# Database Connection
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;"
engine = sqlalchemy.create_engine(f"mssql+pyodbc://MCKNIGHTS-PC\\SQLEXPRESS01/hs_football_database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes")

def clean_text(text):
    """Normalizes team name (removes extra spaces, special characters, normalizes Unicode)."""
    text = text.strip()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s']", "", text)  # Allow apostrophes
    text = re.sub(r"\s+", " ", text)  # Ensure single spaces
    return text.lower()

# Load Data from SQL
team_names_df = pd.read_sql("SELECT Team_Name FROM dbo.HS_Team_Names", engine)
alias_df = pd.read_sql("SELECT Alias_Name, Standardized_Name FROM dbo.HS_Team_Name_Alias", engine)

# Convert alias table to a dictionary (Ensure alias normalization)
alias_dict = {clean_text(alias): standard for alias, standard in zip(alias_df["Alias_Name"], alias_df["Standardized_Name"])}

def get_standard_team_name(newspaper_name):
    """Attempts to match a team name from a newspaper OCR result to a standardized name in the database."""
    
    normalized_name = clean_text(newspaper_name)
    print(f"🔍 Normalized: '{newspaper_name}' → '{normalized_name}'")  # Debugging

    # 1️⃣ Check alias table first (Case-insensitive lookup)
    if normalized_name in alias_dict:
        return alias_dict[normalized_name]

    # 2️⃣ Check for exact match in HS_Team_Names
    if normalized_name in team_names_df["Team_Name"].str.lower().values:
        return team_names_df.loc[team_names_df["Team_Name"].str.lower() == normalized_name, "Team_Name"].values[0]

    # 3️⃣ Use fuzzy matching against alias names (high confidence threshold)
    alias_match = process.extractOne(normalized_name, list(alias_dict.keys()), scorer=fuzz.token_sort_ratio)
    if alias_match and alias_match[1] > 85:
        return alias_dict[alias_match[0]]

    # 4️⃣ Use fuzzy matching against HS_Team_Names as a last resort
    team_match = process.extractOne(normalized_name, team_names_df["Team_Name"].str.lower().values, scorer=fuzz.token_sort_ratio)
    if team_match and team_match[1] > 85:
        return team_names_df.loc[team_names_df["Team_Name"].str.lower() == team_match[0], "Team_Name"].values[0]

    # 5️⃣ Log unrecognized names to review table
    with engine.connect() as connection:
        connection.execute(text("INSERT INTO dbo.HS_Team_Names_Review (Unrecognized_Name) VALUES (:name)"),
                           {"name": newspaper_name})
    
    print(f"⚠️ Unrecognized team: {newspaper_name} - Needs manual verification")
    return newspaper_name  # Return the original name as a placeholder

# Process OCR Results
STAGED_FOLDER = "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"

# Find OCR text files in the Staged folder
ocr_files = [f for f in os.listdir(STAGED_FOLDER) if f.endswith(".txt")]

if not ocr_files:
    print("❌ No OCR result files found in Staged folder. Exiting.")
    exit()

# Use the first available OCR file
ocr_results_file = os.path.join(STAGED_FOLDER, ocr_files[0])
print(f"📂 Using OCR results from: {ocr_results_file}")

# Read OCR results
cleaned_data = []
with open(ocr_results_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Process each line to extract scores
for line in lines:
    match = re.match(r"(.+?)\s+(\d+)\s*,\s*(.+?)\s+(\d+)", line.strip())  # Handle variations in spacing & missing commas
    if match:
        home_team = get_standard_team_name(match.group(1).strip())
        visitor_team = get_standard_team_name(match.group(3).strip())

        try:
            home_score = int(match.group(2))
            visitor_score = int(match.group(4))

            # Handle impossible score (1) → Forfeit case
            forfeit = False
            if home_score == 1 or visitor_score == 1:
                forfeit = True
                home_score, visitor_score = (1, 0) if home_score == 1 else (0, 1)

            cleaned_data.append([home_team, home_score, visitor_team, visitor_score, forfeit])

        except ValueError:
            print(f"⚠️ Skipping invalid score line: {line.strip()}")

# Save cleaned data to CSV for review
output_csv = os.path.join(STAGED_FOLDER, "cleaned_scores.csv")
pd.DataFrame(cleaned_data, columns=["Home", "Home_Score", "Visitor", "Visitor_Score", "Forfeit"]).to_csv(output_csv, index=False)

print(f"✅ Process completed. Cleaned data saved to {output_csv}")










