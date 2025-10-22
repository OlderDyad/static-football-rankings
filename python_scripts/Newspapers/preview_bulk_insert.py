import pandas as pd
import os
import re
from datetime import datetime

# Define path
staged_folder = r"H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
cleaned_csv = os.path.join(staged_folder, "cleaned_scores.csv")

# Read the CSV
print("📊 Reading cleaned scores CSV...")
df = pd.read_csv(cleaned_csv)

# Get unique dates from OCR files
ocr_files = [f for f in os.listdir(staged_folder) if f.endswith(".txt")]
unique_dates = set()

for f in ocr_files:
    match = re.search(r"(\d{4})_(\d{2})_(\d{2})", f)
    if match:
        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        unique_dates.add(date_str)

print(f"\n📑 Found {len(df)} total games")
print("\n🗓️ Dates from OCR files:")
for date in sorted(unique_dates):
    print(f"   {date}")

# Display sample of games
print("\n🔍 Sample of first 10 games:")
for idx, row in df.head(10).iterrows():
    print(f"\nGame {idx + 1}:")
    print(f"   {row['Home']} {row['Home_Score']} vs {row['Visitor']} {row['Visitor_Score']}")
    if 'Forfeit' in df.columns:
        print(f"   Forfeit: {row['Forfeit']}")

# Basic statistics
print("\n📈 Statistics:")
print(f"Total Games: {len(df)}")
print(f"Unique Home Teams: {df['Home'].nunique()}")
print(f"Unique Visiting Teams: {df['Visitor'].nunique()}")

# Check for potential duplicates
duplicates = df.groupby(['Home', 'Visitor', 'Home_Score', 'Visitor_Score']).size().reset_index(name='count')
duplicates = duplicates[duplicates['count'] > 1]

if not duplicates.empty:
    print("\n⚠️ Potential duplicate games found:")
    print(duplicates.to_string(index=False))
else:
    print("\n✅ No duplicate games found")

# Show all available columns
print("\n📋 Available columns in CSV:")
print(df.columns.tolist())

# If Source column exists, show counts by source
if 'Source' in df.columns:
    print("\n📰 Games by Source:")
    source_counts = df['Source'].value_counts()
    for source, count in source_counts.items():
        print(f"   {source}: {count} games")