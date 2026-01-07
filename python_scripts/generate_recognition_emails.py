# generate_recognition_emails.py
"""
Generate personalized recognition emails for 2025 season
Pulls data from SQL, validates rankings, generates email text with proper links

Author: David McKnight
Created: January 2026
"""

import pyodbc
import pandas as pd
from pathlib import Path
import json

# Configuration
SQL_SERVER = 'MCKNIGHTS-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
BASE_URL = 'https://olderdyad.github.io/static-football-rankings'

# Get database connection
def get_db_connection():
    """Create connection to SQL Server database"""
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SQL_SERVER};'
        f'DATABASE={DATABASE};'
        f'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

def get_recognition_data():
    """
    Get all teams worthy of recognition with validation
    Returns DataFrame with corrected flags
    """
    conn = get_db_connection()
    
    # Get the recognition report
    query = "EXEC Get_2025_Recognition_Report"
    df = pd.read_sql(query, conn)
    
    # VALIDATION: Verify state rankings
    # For each state, check that only the TOP team has Is_State_Champion = 1
    for state in df['State'].unique():
        state_teams = df[df['State'] == state].sort_values('Combined', ascending=False)
        
        if len(state_teams) > 0:
            # Only the first team should be #1 in state
            top_team = state_teams.iloc[0]
            
            # Fix any incorrectly flagged teams
            for idx, row in state_teams.iterrows():
                if row['Team'] != top_team['Team']:
                    # This team is NOT #1 in state, fix the flag
                    if df.at[idx, 'Is_State_Champion'] == 1:
                        print(f"⚠️  CORRECTED: {row['Team']} was incorrectly marked as #1 in {state}")
                        print(f"   Actual #1: {top_team['Team']} ({top_team['Combined']:.4f})")
                        print(f"   This team: {row['Combined']:.4f} (Rank #{state_teams.index.get_loc(idx) + 1})")
                        df.at[idx, 'Is_State_Champion'] = 0
    
    # Get national rankings from latest season
    query_national = """
    DECLARE @Coef_Avg_Modified_Score DECIMAL(18, 5),
            @Coef_Win_Loss DECIMAL(18, 5),
            @Coef_Log_Score DECIMAL(18, 5);
            
    SELECT TOP 1 
        @Coef_Avg_Modified_Score = Avg_Adjusted_Margin_Coef,
        @Coef_Win_Loss = Power_Ranking_Coef_Win_Loss,
        @Coef_Log_Score = Power_Ranking_Coef
    FROM [dbo].[Coefficients]
    ORDER BY ID DESC;
    
    SELECT 
        r.Home AS Team,
        ROW_NUMBER() OVER (
            ORDER BY (r.Avg_Of_Avg_Of_Home_Modified_Score * @Coef_Avg_Modified_Score) +
                     (r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * @Coef_Win_Loss) +
                     (r.Avg_Of_Avg_Of_Home_Modified_Log_Score * @Coef_Log_Score) DESC
        ) AS National_Rank
    FROM HS_Rankings r
    WHERE r.Season = 2025
      AND r.Week = 52
      AND r.Home NOT LIKE '%Frosh%'
      AND r.Home NOT LIKE '%frosh%'
      AND r.Home NOT LIKE '%Freshman%';
    """
    df_national = pd.read_sql(query_national, conn)
    
    # Merge national rankings
    df = df.merge(df_national, on='Team', how='left')
    
    # Get state rankings
    df['State_Rank'] = df.groupby('State')['Combined'].rank(method='min', ascending=False).astype(int)
    
    conn.close()
    
    return df

def get_team_links(team_name, state):
    """
    Generate relevant page links for a team
    """
    state_code = state
    
    links = {
        'latest_season': f'{BASE_URL}/pages/public/latest-season/index.html',
        'state_teams': f'{BASE_URL}/pages/public/states/{state_code}/teams.html',
        'state_programs': f'{BASE_URL}/pages/public/states/{state_code}/programs.html',
    }
    
    return links

def format_recognition_type(row):
    """
    Determine recognition type and appropriate language
    """
    is_state_top = row['Is_State_Champion'] == 1
    is_program_record = row['Is_Program_Record'] == 1
    
    if is_state_top and is_program_record:
        return {
            'type': 'double',
            'title': 'Double Recognition',
            'achievement': f"#1 rated team in {row['State']} AND all-time program record",
            'emphasis': 'exceptionally rare achievement - only 20 teams nationwide'
        }
    elif is_state_top:
        return {
            'type': 'state_top',
            'title': 'Top-Rated in State',
            'achievement': f"#1 rated team in {row['State']} for 2025",
            'emphasis': 'outstanding competitive excellence'
        }
    else:  # program_record only
        return {
            'type': 'program_record',
            'title': 'All-Time Program Record',
            'achievement': f"best season in program history",
            'emphasis': 'historic milestone for your program'
        }

def generate_email_text(row, recognition_type, links):
    """
    Generate complete email text with all data filled in
    """
    
    # Format statistics
    combined = f"{row['Combined']:.4f}"
    offense = f"{row['Offense']:.4f}"
    defense = f"{row['Defense']:.4f}"
    margin = f"{row['Margin']:.2f}"
    win_loss = f"{row['Win_Loss']:.4f}"
    games = int(row['Games_Played'])
    seasons = int(row['Total_Seasons'])
    national_rank = int(row['National_Rank']) if pd.notna(row['National_Rank']) else "N/A"
    state_rank = int(row['State_Rank'])
    
    # Get state full name
    state_names = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming',
        'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba', 'NB': 'New Brunswick',
        'NS': 'Nova Scotia', 'QB': 'Quebec', 'SK': 'Saskatchewan'
    }
    state_full = state_names.get(row['State'], row['State'])
    
    # Template based on recognition type
    if recognition_type['type'] == 'double':
        subject = f"Exceptional Achievement - {row['Team']} #1 in {state_full} AND All-Time Program Record"
        
        # Get previous best info if available
        prev_info = ""
        if row['Record_Margin'] and row['Record_Margin'] != 'First Record (25+ Seasons)':
            try:
                improvement = float(row['Record_Margin'])
                prev_info = f"(+{improvement:.4f} improvement over previous record)"
            except:
                prev_info = ""
        
        body = f"""Dear [Athletic Director / Coach Name],

I hope this message finds you well. I'm reaching out to congratulate {row['Team']} on what can only be described as an exceptional 2025 season - one of historic proportions.

According to McKnight's American Football Rankings, your 2025 team accomplished something extraordinarily rare: achieving BOTH the #1 rating in {state_full} AND setting an all-time program record. Out of 339 teams recognized nationwide for 2025, only 20 achieved this double recognition.

YOUR 2025 ACHIEVEMENTS:

🏆 #1 Rated Team in {state_full}
   • Combined Rating: {combined}
   • Highest among teams with 25+ year history

📈 All-Time Program Record
   • New Program Best: {combined}
   • Seasons in Database: {seasons}
   {prev_info}

NATIONAL CONTEXT:
   • National Rank: #{national_rank}
   • State Rank: #{state_rank} of teams in {state_full}
   • Double Recognition: Only 20 teams nationwide (top 5.9%)
   • Games Played: {games}

PERFORMANCE STATISTICS:
   • Offensive Rating: {offense}
   • Defensive Rating: {defense}
   • Average Margin: {margin} points per game
   • Win/Loss Rating: {win_loss}

This combination - being the best in your state while simultaneously setting your program's all-time record - represents the absolute pinnacle of high school football excellence.

EXPLORE YOUR RANKINGS:
   • Latest Season Rankings: {links['latest_season']}
   • {state_full} Team Rankings: {links['state_teams']}
   • {state_full} Program Rankings: {links['state_programs']}

These pages show your team's performance in context with detailed statistics and historical comparisons. We've seen significant community engagement when schools share these rankings with players, families, and alumni.

If you have any questions about our methodology or would like additional historical data, I'd be delighted to provide any information that might be helpful.

Congratulations again on a truly historic season!

Best regards,

David McKnight
McKnight's American Football Rankings
{BASE_URL}
"""
    
    elif recognition_type['type'] == 'state_top':
        subject = f"Congratulations - {row['Team']} Recognized as #1 Rated Team in {state_full} for 2025"
        
        body = f"""Dear [Athletic Director / Coach Name],

I hope this message finds you well. I'm reaching out to congratulate {row['Team']} on an outstanding 2025 season.

According to McKnight's American Football Rankings, your team achieved the #1 rating in {state_full} for 2025 among programs with at least 25 years of history in our database.

YOUR 2025 ACHIEVEMENT:
   • Combined Rating: {combined}
   • State Rank: #{state_rank} in {state_full}
   • National Rank: #{national_rank}
   • Games Played: {games}
   • Seasons in Database: {seasons}

PERFORMANCE STATISTICS:
   • Offensive Rating: {offense}
   • Defensive Rating: {defense}
   • Average Margin: {margin} points per game
   • Win/Loss Rating: {win_loss}

Being the top-rated team in your state is a testament to the excellence of your program, coaching staff, and the dedication of your players throughout the season.

EXPLORE YOUR RANKINGS:
   • Latest Season Rankings: {links['latest_season']}
   • {state_full} Team Rankings: {links['state_teams']}
   • {state_full} Program Rankings: {links['state_programs']}

These pages show your team's performance with detailed statistics and comparisons. Feel free to share these rankings with your players, families, alumni, and community.

If you have any questions about our methodology or would like more information about your team's historical performance, I'd be happy to discuss further.

Congratulations again on an exceptional season!

Best regards,

David McKnight
McKnight's American Football Rankings
{BASE_URL}
"""
    
    else:  # program_record
        subject = f"Congratulations - {row['Team']} Sets All-Time Program Record for 2025"
        
        # Get previous best info
        prev_info = "This is your program's first season with sufficient data in our database."
        if row['Record_Margin'] and row['Record_Margin'] != 'First Record (25+ Seasons)':
            try:
                improvement = float(row['Record_Margin'])
                prev_info = f"Previous Best: [Previous Year Season]\nImprovement: +{improvement:.4f} over previous record"
            except:
                prev_info = "[Record Margin information available in database]"
        
        body = f"""Dear [Athletic Director / Coach Name],

I hope this message finds you well. I'm reaching out to congratulate {row['Team']} on a truly historic 2025 season.

According to McKnight's American Football Rankings, your 2025 team achieved the highest Combined rating in your program's history among the {seasons} seasons we have in our database.

YOUR 2025 ACHIEVEMENT:
   • Combined Rating: {combined} - NEW PROGRAM RECORD
   • {prev_info}
   • State Rank: #{state_rank} in {state_full}
   • National Rank: #{national_rank}
   • Seasons in Database: {seasons}

PERFORMANCE STATISTICS:
   • Offensive Rating: {offense}
   • Defensive Rating: {defense}
   • Average Margin: {margin} points per game
   • Win/Loss Rating: {win_loss}
   • Games Played: {games}

Setting an all-time program record after {seasons} seasons of football is an extraordinary achievement that demonstrates exceptional coaching, player development, and program building.

EXPLORE YOUR RANKINGS:
   • Latest Season Rankings: {links['latest_season']}
   • {state_full} Team Rankings: {links['state_teams']}
   • {state_full} Program Rankings: {links['state_programs']}

These pages include historical comparisons showing how 2025 compares to your program's entire history. Please feel free to share this milestone with your players, families, alumni, and community.

If you have any questions about our methodology or would like more historical performance data, I'd be happy to discuss further.

Congratulations again on this historic season!

Best regards,

David McKnight
McKnight's American Football Rankings
{BASE_URL}
"""
    
    return {
        'subject': subject,
        'body': body,
        'team': row['Team'],
        'state': row['State'],
        'recognition_type': recognition_type['type'],
        'combined': combined,
        'national_rank': national_rank,
        'state_rank': state_rank
    }

def main():
    """Main execution"""
    print("=" * 80)
    print("2025 RECOGNITION EMAIL GENERATOR")
    print("=" * 80)
    print()
    
    # Get data with validation
    print("📊 Fetching recognition data from database...")
    df = get_recognition_data()
    print(f"✓ Found {len(df)} teams for recognition")
    print()
    
    # Summary statistics
    double_count = len(df[(df['Is_State_Champion'] == 1) & (df['Is_Program_Record'] == 1)])
    state_only_count = len(df[(df['Is_State_Champion'] == 1) & (df['Is_Program_Record'] == 0)])
    program_only_count = len(df[(df['Is_State_Champion'] == 0) & (df['Is_Program_Record'] == 1)])
    
    print("RECOGNITION SUMMARY:")
    print(f"  • Double Recognition: {double_count} teams")
    print(f"  • Top-Rated in State Only: {state_only_count} teams")
    print(f"  • Program Record Only: {program_only_count} teams")
    print(f"  • Total: {len(df)} teams")
    print()
    
    # Generate emails for each team
    print("📧 Generating personalized emails...")
    print()
    
    emails = []
    for idx, row in df.iterrows():
        recognition_type = format_recognition_type(row)
        links = get_team_links(row['Team'], row['State'])
        email_data = generate_email_text(row, recognition_type, links)
        emails.append(email_data)
        
        # Print progress
        status_icon = "🏆" if recognition_type['type'] == 'double' else ("🥇" if recognition_type['type'] == 'state_top' else "📈")
        print(f"{status_icon} {row['Team']:50s} [{recognition_type['type']:15s}] Rank: #{email_data['state_rank']} in {row['State']}, #{email_data['national_rank']} nationally")
    
    print()
    print(f"✓ Generated {len(emails)} personalized emails")
    print()
    
    # Save to file
    output_file = Path('recognition_emails_2025.json')
    with open(output_file, 'w') as f:
        json.dump(emails, f, indent=2)
    
    print(f"💾 Saved to: {output_file}")
    print()
    
    # Generate sample
    print("=" * 80)
    print("SAMPLE EMAIL (First Double Recognition Team):")
    print("=" * 80)
    double_teams = [e for e in emails if e['recognition_type'] == 'double']
    if double_teams:
        sample = double_teams[0]
        print(f"Subject: {sample['subject']}")
        print()
        print(sample['body'])
    
    print()
    print("=" * 80)
    print("✓ EMAIL GENERATION COMPLETE")
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print("1. Review recognition_emails_2025.json")
    print("2. Fill in [Athletic Director / Coach Name] placeholders")
    print("3. Add contact email addresses")
    print("4. Send emails in priority order (double → state → program)")
    print("5. Track sent emails in Excel Recognition_Tracking_2025.xlsx")

if __name__ == "__main__":
    main()