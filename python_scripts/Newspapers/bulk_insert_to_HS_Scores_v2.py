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

# **✅ Add Missing Columns for SQL Structure**
df["Neutral"] = 0  # Default: Not neutral
df["Location"] = df["Home"]  # Use home team as location
df["Location2"] = None
df["Line"] = None
df["Future_Game"] = 0  # Default: Not a future game
df["Date_Added"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current timestamp
df["OT"] = 0  # Default: No overtime
# Note: Forfeit already exists in the input
df["ID"] = [str(uuid.uuid4()).upper() for _ in range(len(df))]  # Uppercase UUID
df["Margin"] = df["Home_Score"] - df["Visitor_Score"]  # Calculate margin
df["Access_ID"] = None

# Note: We now use the Date, Season, and Source directly from the input file
# No need to extract from OCR filename

# Print sample of the data to verify
print("\n📋 Sample of data being imported:")
print(df[["Date", "Season", "Home", "Visitor", "Home_Score", "Visitor_Score", "Source"]].head(3))

# **✅ Reorder Columns to Match HS_Scores Table**
df = df[[
    "Date", "Season", "Home", "Visitor", "Neutral", 
    "Location", "Location2", "Line", "Future_Game", 
    "Source", "Date_Added", "OT", "Forfeit", "ID",
    "Visitor_Score", "Home_Score", "Margin", "Access_ID"
]]

# **✅ Save Cleaned CSV**
print("💾 Saving formatted CSV...")
df.to_csv(
    final_csv,
    index=False,
    header=False,
    encoding='utf-8',
    lineterminator='\r\n',
    na_rep='',  # Empty string for NULL values
    quoting=1,  # Quote all fields
    quotechar='"',  # Use double quotes
    doublequote=True  # Double-up quotes for escaping
)

print(f"✅ Cleaned CSV saved at: {final_csv}")
print(f"   Final row count: {len(df)}")

# **✅ Perform Database Insert**
print("\n📥 Performing database insert...")
try:
    print("🔄 Attempting pandas to_sql method...")
    df.to_sql(
        'HS_Scores_Temp',
        engine,
        if_exists='replace',
        index=False,
        method='multi',
        chunksize=100
    )
    
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO dbo.HS_Scores
            SELECT * FROM dbo.HS_Scores_Temp;
            DROP TABLE dbo.HS_Scores_Temp;
        """))
        conn.commit()
    print("✅ Insert successful!")
    
except Exception as e:
    print(f"❌ Insert Failed: {e}")
    raise

print("\n✨ Process complete!")