import pandas as pd
import os
import re
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# **✅ Database Connection**
engine = create_engine("mssql+pyodbc://MCKNIGHTS-PC\\SQLEXPRESS01/hs_football_database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes")

# **✅ Define Paths**
staged_folder = r"H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
cleaned_csv = os.path.join(staged_folder, "cleaned_scores.csv")
final_csv = os.path.join(staged_folder, "cleaned_scores_for_bulk_insert.csv")

# **✅ Verify File Exists**
if not os.path.exists(cleaned_csv):
    print(f"❌ File not found: {cleaned_csv}")
    exit()

# **✅ Read & Clean Data**
print("🔄 Loading CSV file...")
df = pd.read_csv(cleaned_csv)
initial_rows = len(df)
print(f"📊 Initial row count: {initial_rows}")

# **✅ Drop Unnecessary Columns**
if 'Forfeit' in df.columns:
    df = df.drop(columns=['Forfeit'])
    print("🗑️ Removed 'Forfeit' column")

# **✅ Add Missing Columns for SQL Structure**
df["Neutral"] = 0  # Default: Not neutral
df["Location"] = None
df["Location2"] = None
df["Line"] = None
df["Future_Game"] = 0  # Default: Not a future game
df["Source"] = None
df["Date_Added"] = None
df["OT"] = 0  # Default: No overtime
df["ID"] = [str(uuid.uuid4()) for _ in range(len(df))]

# **✅ Assign Date & Source Automatically**
ocr_files = [f for f in os.listdir(staged_folder) if f.endswith(".txt")]
if ocr_files:
    file_name = ocr_files[0]
    match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_name)
    if match:
        season = int(match.group(1))
        game_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        date_added = game_date - timedelta(days=1)
        df["Season"] = season
        df["Date_Added"] = date_added.strftime("%Y-%m-%d %H:%M:%S")
        df["Source"] = file_name.replace('_', ' ')
        print(f"✅ Assigned Season: {season}, Date_Added: {date_added.strftime('%Y-%m-%d')}, Source: {file_name}")
    else:
        print(f"⚠️ Could not extract date from filename: {file_name}")
else:
    print("⚠️ No OCR source file found. Using default values.")

# **✅ Reorder Columns to Match HS_Scores Table**
df = df[["Home", "Home_Score", "Visitor", "Visitor_Score", "Neutral", "Location", "Location2", "Line", "Future_Game", "Season", "Source", "Date_Added", "OT", "ID"]]

# **✅ Save Cleaned CSV**
print("💾 Saving cleaned CSV for bulk insert...")
df.to_csv(final_csv, index=False, header=False, encoding="utf-8")
print(f"✅ Cleaned CSV saved at: {final_csv}")

print("✨ Processing complete!")


