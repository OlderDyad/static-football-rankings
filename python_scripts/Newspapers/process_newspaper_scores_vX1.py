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
input_csv = os.path.join(staged_folder, "cleaned_scores.csv")
final_csv = os.path.join(staged_folder, "cleaned_scores_for_bulk_insert.csv")

# **✅ Verify Input File**
if not os.path.exists(input_csv):
    print(f"❌ Input file not found: {input_csv}")
    exit()

# **✅ Read Game Data**
print("🔄 Loading cleaned scores...")
df = pd.read_csv(input_csv)
initial_rows = len(df)
print(f"📊 Found {initial_rows} games to process")

# **✅ Create Base Metadata**
df["Neutral"] = 0  # Default: Not neutral
df["Location"] = df["Home"]  # Use home team as location
df["Location2"] = None
df["Line"] = None
df["Future_Game"] = 0
df["OT"] = 0
df["Forfeit"] = df["Forfeit"].fillna(0)
df["ID"] = [str(uuid.uuid4()).upper() for _ in range(len(df))]
df["Access_ID"] = None
df["Margin"] = df["Home_Score"] - df["Visitor_Score"]

# **✅ Get Dates from OCR Files**
ocr_files = sorted([f for f in os.listdir(staged_folder) if f.endswith(".txt")])

if not ocr_files:
    print("❌ No OCR files found to get dates from!")
    exit()

# Get the unique dates from filenames
file_dates = {}
for file_name in ocr_files:
    match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_name)
    if match:
        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        file_dates[file_name] = date_str

# Select one representative file for each date
unique_dates = {}
for file_name, date_str in file_dates.items():
    if date_str not in unique_dates:
        unique_dates[date_str] = file_name

print("\n🗓️ Found dates:")
for date_str, file_name in unique_dates.items():
    print(f"   {date_str} from {file_name}")

# **✅ Add Date and Source Information**
games_per_date = len(df) // len(unique_dates)
print(f"\n📊 Distributing {len(df)} games across {len(unique_dates)} dates")
print(f"   Approximately {games_per_date} games per date")

# Create final dataframe with distributed games
final_games = []
current_index = 0

for date_str, file_name in unique_dates.items():
    # Calculate number of games for this date
    if current_index + games_per_date > len(df):
        end_index = len(df)
    else:
        end_index = current_index + games_per_date
    
    # Get games for this date
    date_games = df.iloc[current_index:end_index].copy()
    
    # Add date and source information
    date_games["Date"] = date_str
    date_games["Season"] = int(date_str.split('-')[0])
    date_games["Source"] = file_name.replace('_', ' ').replace('.txt', '')
    date_games["Date_Added"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_games.append(date_games)
    current_index = end_index

final_df = pd.concat(final_games, ignore_index=True)

# **✅ Ensure Column Order Matches SQL Schema**
final_df = final_df[[
    "Date", "Season", "Home", "Visitor", "Neutral", 
    "Location", "Location2", "Line", "Future_Game", 
    "Source", "Date_Added", "OT", "Forfeit", "ID",
    "Visitor_Score", "Home_Score", "Margin", "Access_ID"
]]

# **✅ Save Processed CSV**
print("\n💾 Saving formatted CSV...")
final_df.to_csv(
    final_csv,
    index=False,
    header=False,
    encoding='utf-8',
    lineterminator='\r\n',
    na_rep='',  # Empty string for NULL values
    quoting=1,  # Quote all fields
    quotechar='"',
    doublequote=True
)

print(f"✅ Processed CSV saved at: {final_csv}")
print(f"   Final row count: {len(final_df)}")

# **✅ Verify Data Before Import**
print("\n🔍 Data Verification:")
print("Games per date:")
date_counts = final_df.groupby('Date').size()
for date, count in date_counts.items():
    print(f"   {date}: {count} games")
print(f"Total Games: {len(final_df)}")
print(f"Unique Sources: {final_df['Source'].nunique()}")

# **✅ Perform Database Import**
print("\n📥 Performing database insert...")
try:
    print("🔄 Creating temporary table...")
    final_df.to_sql(
        'HS_Scores_Temp',
        engine,
        if_exists='replace',
        index=False,
        method='multi',
        chunksize=100
    )
    
    with engine.connect() as conn:
        print("🔄 Inserting into HS_Scores...")
        conn.execute(text("""
            INSERT INTO dbo.HS_Scores
            SELECT * FROM dbo.HS_Scores_Temp;
            DROP TABLE dbo.HS_Scores_Temp;
        """))
        conn.commit()
    print("✅ Database insert completed successfully!")
    
    # Verify the insert
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT Date, COUNT(*) as game_count
            FROM dbo.HS_Scores 
            WHERE Source LIKE '%Buffalo News%'
            AND Date >= '1989-09-01'
            GROUP BY Date
            ORDER BY Date;
        """))
        print(f"\n📊 Database Verification - Games by Date:")
        for row in result:
            print(f"   {row[0]}: {row[1]} games")

except Exception as e:
    print(f"❌ Error during database insert: {e}")
    raise

print("\n✨ Process complete!")

