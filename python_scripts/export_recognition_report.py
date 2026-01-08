"""
Export 2025 Recognition Report to CSV with Contact Placeholders
Runs the stored procedure and adds empty columns for contact research
"""

import pyodbc
import pandas as pd
from datetime import datetime
import os

# Configuration
SERVER = 'MCKNIGHTS-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
OUTPUT_DIR = r'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\recognition\2025'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def connect_database():
    """Connect to SQL Server database"""
    connection_string = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'Trusted_Connection=yes;'
        f'TrustServerCertificate=yes;'
    )
    return pyodbc.connect(connection_string)

def export_recognition_report():
    """Export recognition report with contact placeholder columns"""
    
    print("Connecting to database...")
    conn = connect_database()
    
    print("Running recognition report (this may take 1-2 minutes)...")
    query = "EXEC Get_2025_Recognition_Report_FAST;"
    
    # Read data into pandas DataFrame
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"Retrieved {len(df)} teams for recognition")
    
    # Add contact placeholder columns
    df['Website_Status'] = ''  # Found, Not Found, Need Research
    df['Athletic_Director'] = ''
    df['AD_Email'] = ''
    df['Head_Coach'] = ''
    df['Coach_Email'] = ''
    df['Athletic_Dept_Email'] = ''
    df['Main_Phone'] = ''
    df['Contact_Notes'] = ''
    df['Email_Sent_Date'] = ''
    df['Email_Status'] = ''  # Sent, Bounced, Opened, Replied
    df['Response_Notes'] = ''
    
    # Create summary statistics
    summary = df.groupby('Recognition_Type').size().reset_index(name='Count')
    
    print("\n=== Recognition Summary ===")
    print(summary.to_string(index=False))
    
    # Export full report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f'Recognition_Report_2025_{timestamp}.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ Full report exported to: {output_file}")
    
    # Export separate files by recognition type for focused outreach
    for rec_type in df['Recognition_Type'].unique():
        subset = df[df['Recognition_Type'] == rec_type]
        type_file = os.path.join(OUTPUT_DIR, f'Recognition_2025_{rec_type.replace(" ", "_")}_{timestamp}.csv')
        subset.to_csv(type_file, index=False, encoding='utf-8-sig')
        print(f"✅ {rec_type}: {len(subset)} teams exported to {type_file}")
    
    # Export priority list (Double Recognition + Top 100 Program Records)
    double = df[df['Recognition_Type'] == 'Double Recognition']
    top_program = df[df['Recognition_Type'] == 'Program Record'].head(100)
    priority = pd.concat([double, top_program]).sort_values('Combined_2025', ascending=False)
    
    priority_file = os.path.join(OUTPUT_DIR, f'Recognition_2025_PRIORITY_{timestamp}.csv')
    priority.to_csv(priority_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ PRIORITY LIST ({len(priority)} teams) exported to: {priority_file}")
    
    return df

def generate_email_data():
    """Generate personalized email data for mail merge"""
    
    print("\nGenerating email merge data...")
    conn = connect_database()
    df = pd.read_sql("EXEC Get_2025_Recognition_Report_FAST;", conn)
    conn.close()
    
    # Prepare email merge fields
    email_df = pd.DataFrame({
        'Team': df['Team'],
        'State': df['State'].str.replace('(', '').str.replace(')', ''),
        'Combined_2025': df['Combined_2025'].round(2),
        'National_Rank': df['National_Rank'],
        'State_Rank': df['StateRank'],
        'Previous_Best': df['Previous_Best'].round(2),
        'Improvement': df['Improvement'].round(2),
        'Games_Played': df['Games_Played'],
        'Total_Seasons': df['Total_Seasons'],
        'Recognition_Type': df['Recognition_Type'],
        'Is_State_Top': df['Is_State_Top'],
        'Is_Program_Record': df['Is_Program_Record'],
        'Website': df['TeamPageUrl'],
        # Empty fields for mail merge
        'Recipient_Name': '',
        'Recipient_Email': '',
        'Subject_Line': '',
        'Email_Body': ''
    })
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    email_file = os.path.join(OUTPUT_DIR, f'Email_Merge_Data_2025_{timestamp}.csv')
    email_df.to_csv(email_file, index=False, encoding='utf-8-sig')
    
    print(f"✅ Email merge data exported to: {email_file}")
    return email_df

if __name__ == "__main__":
    print("=" * 70)
    print("2025 RECOGNITION REPORT EXPORT")
    print("=" * 70)
    
    try:
        # Export main recognition report
        df = export_recognition_report()
        
        # Generate email merge data
        email_df = generate_email_data()
        
        print("\n" + "=" * 70)
        print("EXPORT COMPLETE!")
        print("=" * 70)
        print(f"\nTotal teams recognized: {len(df)}")
        print(f"Files saved to: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()