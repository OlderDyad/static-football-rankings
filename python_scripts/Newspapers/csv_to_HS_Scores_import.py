import pandas as pd
import os
import re
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# **✅ Database Connection**
engine = create_engine("mssql+pyodbc://MCKNIGHTS-PC\\SQLEXPRESS01/hs_football_database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes")

# **✅ Define Paths**
staged_folder = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged"
input_csv = os.path.join(staged_folder, "cleaned_scores.csv")
output_csv = os.path.join(staged_folder, "cleaned_scores_for_bulk_insert.csv")

# **✅ Extract date from OCR files**
ocr_files = [f for f in os.listdir(staged_folder) if f.endswith(".txt")]
if not ocr_files:
    print("❌ No OCR result files found in Staged folder. Exiting.")
    exit()

file_name = ocr_files[0]
match = re.search(r"(\d{4})_(\d{2})_(\d{2})_(\d+)", file_name)
if not match:
    print(f"⚠️ Could not extract date from filename: {file_name}")
    exit()

# Extract date information
game_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
date_added = game_date - timedelta(days=1)  # Date added = game date minus 1 day
season = game_date.year
source = file_name.replace('_', ' ')

print("🔄 Loading cleaned scores CSV...")
df = pd.read_csv(input_csv)
print(f"📊 Found {len(df)} games to process")

# Create expanded dataframe with all required columns
print("\n🔄 Transforming data to match HS_Scores schema...")
expanded_data = []

for _, row in df.iterrows():
    # Calculate margin (Home - Visitor)
    margin = row['Home_Score'] - row['Visitor_Score']
    
    # Generate unique ID
    game_id = str(uuid.uuid4()).upper()  # Convert to uppercase to match sample
    
    # Create game record with all required fields
    game_record = {
        'Date': game_date.strftime('%m/%d/%Y'),  # Format: MM/DD/YYYY
        'Season': season,
        'Home': row['Home'],
        'Visitor': row['Visitor'],
        'Neutral': 0,  # Default to 0
        'Location': row['Home'],  # Use home team as location
        'Location2': 'NULL',  # Use explicit NULL
        'Line': 'NULL',  # Use explicit NULL
        'Future_Game': 0,  # Default to 0
        'Source': source,
        'Date_Added': date_added.strftime('%m/%d/%y %I:%M %p'),  # Format: MM/DD/YY HH:MM AM/PM
        'OT': 'NULL',  # Use explicit NULL
        'Forfeit': 0,
        'ID': game_id,
        'Visitor_Score': row['Visitor_Score'],
        'Home_Score': row['Home_Score'],
        'Margin': margin,
        'Access_ID': 'NULL'  # Use explicit NULL
    }
    expanded_data.append(game_record)

# Create new dataframe with all required columns
print("✨ Creating final dataframe...")
final_df = pd.DataFrame(expanded_data)

# Ensure correct column order matching SQL schema
final_df = final_df[[
    'Date', 'Season', 'Home', 'Visitor', 'Neutral', 
    'Location', 'Location2', 'Line', 'Future_Game', 
    'Source', 'Date_Added', 'OT', 'Forfeit', 'ID',
    'Visitor_Score', 'Home_Score', 'Margin', 'Access_ID'
]]

# Format numeric fields
numeric_cols = ['Season', 'Neutral', 'Future_Game', 'Forfeit', 'Visitor_Score', 'Home_Score', 'Margin']
for col in numeric_cols:
    final_df[col] = pd.to_numeric(final_df[col], errors='coerce')

# Save to CSV with specific formatting for SQL Server
print("\n💾 Saving formatted CSV...")
final_df.to_csv(
    output_csv,
    index=False,
    header=False,
    encoding='utf-8',
    lineterminator='\n',
    na_rep='NULL',  # Use explicit NULL
    quoting=1,  # Quote all fields
    quotechar='"',  # Use double quotes
    doublequote=True  # Double-up quotes for escaping
)

print(f"✅ Formatted CSV saved at: {output_csv}")
print(f"   Ready for bulk insert into HS_Scores table")
print("\n📊 Summary:")
print(f"   Total games processed: {len(final_df)}")
print(f"   Columns in output: {len(final_df.columns)}")
print(f"   File size: {os.path.getsize(output_csv)} bytes")

# Print sample of the output for verification
print("\n🔍 Sample of output data (first 2 rows):")
print(final_df.head(2).to_string())

# Verify data matches expected format
print("\n🔍 Verifying format of key fields:")
sample_row = final_df.iloc[0]
print(f"Date format: {sample_row['Date']}")
print(f"Date_Added format: {sample_row['Date_Added']}")
print(f"ID format: {sample_row['ID']}")
print(f"NULL handling: Location2={sample_row['Location2']}, Line={sample_row['Line']}")



















