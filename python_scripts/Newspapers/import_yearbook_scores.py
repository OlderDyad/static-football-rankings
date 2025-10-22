import pandas as pd
from sqlalchemy import create_engine, text
import uuid

# ✅ Database Connection
engine = create_engine("mssql+pyodbc://MCKNIGHTS-PC\\SQLEXPRESS01/hs_football_database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes")

# ✅ Define File Path
file_path = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Yearbook_data\Staged_01.csv"

# ✅ Load CSV Data
print("🔄 Loading Yearbook Data...")
df = pd.read_csv(file_path)

# ✅ Drop the ID column (not needed since SQL auto-generates it)
df = df.drop(columns=["ID"], errors="ignore")

# ✅ Standardize Column Names to Match HS_Scores Table
df.columns = [
    "Date", "Season", "Visitor", "Visitor_Score", "Home", "Home_Score", "Margin",
    "Neutral", "Location", "Location2", "Line", "Future_Game", "Source",
    "Date_Added", "OT", "Forfeit"
]

# ✅ Convert Data Types
print("🔄 Converting data types...")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
df["Date_Added"] = pd.to_datetime(df["Date_Added"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

# Convert Boolean-like fields
df["Neutral"] = df["Neutral"].astype(bool).astype(int)
df["Future_Game"] = df["Future_Game"].astype(bool).astype(int)
df["Forfeit"] = df["Forfeit"].astype(bool).astype(int)

# Convert nullable integer fields
for col in ["Line", "OT", "Visitor_Score", "Home_Score", "Margin"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

# ✅ Add Unique ID (if missing)
df["ID"] = [str(uuid.uuid4()) for _ in range(len(df))]

# ✅ Insert Data into SQL Server
print("\n📥 Importing data into HS_Scores table...")
try:
    with engine.connect() as conn:
        df.to_sql("HS_Scores", conn, if_exists="append", index=False)
    print("✅ Data imported successfully!")
except Exception as e:
    print(f"❌ Error during import: {e}")

# ✅ Run Duplicate Removal Stored Procedure
print("\n🗑️ Removing duplicate games using stored procedure...")
try:
    with engine.connect() as conn:
        conn.execute(text("EXEC dbo.RemoveDuplicateGames;"))
    print("✅ Duplicate games removed successfully!")
except Exception as e:
    print(f"❌ Error removing duplicates: {e}")

print("\n✨ Import Process Complete!")
