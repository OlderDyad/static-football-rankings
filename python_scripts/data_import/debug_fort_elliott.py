import pyodbc

DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=McKnights-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

# Get Fort Elliott 2003 raw schedule
conn = pyodbc.connect(DB_CONNECTION_STRING)
cursor = conn.cursor()

sql = """
    SELECT raw_schedule_text
    FROM lonestar_raw_schedules
    WHERE team_id = 1 AND season = 2003
"""

cursor.execute(sql)
result = cursor.fetchone()

if result:
    raw_text = result[0]
    print("RAW SCHEDULE TEXT:")
    print("="*80)
    print(raw_text)
    print("="*80)
    print()
    
    # Show line by line
    lines = raw_text.split('\n')
    print(f"Total lines: {len(lines)}")
    print()
    
    for i, line in enumerate(lines, 1):
        print(f"Line {i}: '{line}'")

conn.close()