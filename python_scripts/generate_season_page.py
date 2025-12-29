# generate_season_page.py
"""
Generate individual season pages for teams
Reads from Team_Page_Content and generates HTML using Jinja2 template
"""

import pyodbc
import os
from jinja2 import Template
import logging

# --- CONFIGURATION ---
SERVER = "McKnights-PC\\SQLEXPRESS01"
DATABASE = "hs_football_database"
TEMPLATE_PATH = "../templates/season_page_template.html"
OUTPUT_BASE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/pages/teams"
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_season_data(team_id, season):
    """Fetch all data needed for a season page"""
    
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            data = {}
            
            # 1. Get team info
            cursor.execute("""
                SELECT 
                    Team_Name, City, State, Mascot,
                    PrimaryColor, SecondaryColor,
                    LogoURL, School_Logo_URL, Team_Slug
                FROM HS_Team_Names
                WHERE ID = ?
            """, team_id)
            
            row = cursor.fetchone()
            data['team_name'] = row.Team_Name
            data['city'] = row.City
            data['state'] = row.State
            data['mascot'] = row.Mascot or ''
            data['primary_color'] = row.PrimaryColor or '#003366'
            data['secondary_color'] = row.SecondaryColor or '#0066cc'
            data['logo_url'] = row.LogoURL
            data['school_logo_url'] = row.School_Logo_URL
            data['team_slug'] = row.Team_Slug
            data['season'] = season
            
            # 2. Get championship info
            cursor.execute("""
                SELECT Wins, Losses, Ties
                FROM Media_National_Champions
                WHERE Team_ID = ? AND Season = ?
            """, team_id, season)
            
            champ_row = cursor.fetchone()
            if champ_row:
                data['is_champion'] = True
                wins = champ_row.Wins or 0
                losses = champ_row.Losses or 0
                ties = champ_row.Ties or 0
                if ties > 0:
                    data['record'] = f"{wins}-{losses}-{ties}"
                else:
                    data['record'] = f"{wins}-{losses}"
            else:
                data['is_champion'] = False
                data['record'] = "N/A"
            
            # 3. Get coach
            cursor.execute("""
                SELECT Coach_Name
                FROM Team_Coaches
                WHERE Team_ID = ? 
                  AND Start_Year <= ? 
                  AND (End_Year >= ? OR End_Year IS NULL)
            """, team_id, season, season)
            
            coach_row = cursor.fetchone()
            data['coach_name'] = coach_row.Coach_Name if coach_row else 'Unknown'
            
            # 4. Get ratings
            cursor.execute("""
                SELECT 
                    CAST(Combined_Rating AS DECIMAL(10,3)) AS Combined,
                    CAST(Offense AS DECIMAL(10,3)) AS Offense,
                    CAST(Defense AS DECIMAL(10,3)) AS Defense
                FROM Rankings_Combined
                WHERE Team = ? AND Season = ?
            """, data['team_name'], season)
            
            rating_row = cursor.fetchone()
            if rating_row:
                data['ratings'] = {
                    'combined': rating_row.Combined,
                    'offense': rating_row.Offense,
                    'defense': rating_row.Defense
                }
            else:
                data['ratings'] = {
                    'combined': 'N/A',
                    'offense': 'N/A',
                    'defense': 'N/A'
                }
            
            # 5. Get narrative content
            cursor.execute("""
                SELECT Content_Title, Content_Body
                FROM Team_Page_Content
                WHERE Team_ID = ? 
                  AND Season = ? 
                  AND Content_Type IN ('narrative', 'key_stats', 'roster_highlight')
                  AND Is_Active = 1
                ORDER BY Sort_Order
            """, team_id, season)
            
            data['narratives'] = []
            for row in cursor.fetchall():
                data['narratives'].append({
                    'title': row.Content_Title,
                    'body': row.Content_Body
                })
            
            # 6. Get roster
            cursor.execute("""
                SELECT Content_Title AS Name, Content_Body AS Details
                FROM Team_Page_Content
                WHERE Team_ID = ? 
                  AND Season = ? 
                  AND Content_Type = 'roster_row'
                  AND Is_Active = 1
                ORDER BY Sort_Order
            """, team_id, season)
            
            data['roster'] = []
            for row in cursor.fetchall():
                data['roster'].append({
                    'name': row.Name,
                    'details': row.Details
                })
            
            # 7. Get game schedule
            cursor.execute("""
                SELECT 
                    Date,
                    CASE 
                        WHEN Home = ? THEN 'vs ' + Visitor
                        ELSE '@ ' + Home
                    END AS Opponent,
                    CASE 
                        WHEN Home = ? THEN CAST(Home_Score AS VARCHAR) + '-' + CAST(Visitor_Score AS VARCHAR)
                        ELSE CAST(Visitor_Score AS VARCHAR) + '-' + CAST(Home_Score AS VARCHAR)
                    END AS Score,
                    CASE 
                        WHEN (Home = ? AND Home_Score > Visitor_Score) 
                          OR (Visitor = ? AND Visitor_Score > Home_Score) THEN 'W'
                        WHEN Home_Score = Visitor_Score THEN 'T'
                        ELSE 'L'
                    END AS Result,
                    CASE 
                        WHEN Home = ? THEN 'Home'
                        ELSE 'Away'
                    END AS Location
                FROM HS_Scores
                WHERE Season = ?
                  AND (Home = ? OR Visitor = ?)
                ORDER BY Date
            """, data['team_name'], data['team_name'], data['team_name'], 
                 data['team_name'], data['team_name'], season, 
                 data['team_name'], data['team_name'])
            
            data['schedule'] = []
            for row in cursor.fetchall():
                result = row.Result
                result_class = ''
                if result == 'W':
                    result_class = 'score-win'
                elif result == 'L':
                    result_class = 'score-loss'
                else:
                    result_class = 'score-tie'
                
                data['schedule'].append({
                    'date': row.Date.strftime('%Y-%m-%d') if row.Date else 'N/A',
                    'opponent': row.Opponent,
                    'score': row.Score,
                    'result': result,
                    'result_class': result_class,
                    'location': row.Location,
                    'opponent_state': ''  # Could extract from opponent name if needed
                })
            
            return data
            
    except Exception as e:
        logging.error(f"Error fetching season data: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_season_page(team_id, season):
    """Generate HTML page for a specific season"""
    
    logging.info(f"Generating season page for Team ID {team_id}, Season {season}")
    
    # Get data
    data = get_season_data(team_id, season)
    if not data:
        logging.error("Failed to fetch data")
        return False
    
    # Load template
    try:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_str = f.read()
        
        template = Template(template_str)
    except Exception as e:
        logging.error(f"Error loading template: {e}")
        return False
    
    # Render HTML
    try:
        html = template.render(**data)
    except Exception as e:
        logging.error(f"Error rendering template: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Determine output path
    state = data['state'].lower()
    slug = data['team_slug']
    output_dir = os.path.join(OUTPUT_BASE, state, slug, 'season')
    output_file = os.path.join(output_dir, f'{season}.html')
    
    # Create directories
    os.makedirs(output_dir, exist_ok=True)
    
    # Write file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logging.info(f"✓ Generated: {output_file}")
        
        # Update database
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Team_Season_Pages
                SET Page_Status = 'Published',
                    Last_Updated = GETDATE()
                WHERE Team_ID = ? AND Season = ?
            """, team_id, season)
            conn.commit()
        
        return True
        
    except Exception as e:
        logging.error(f"Error writing file: {e}")
        return False


if __name__ == "__main__":
    # Example: Generate Everett 1920 season page
    team_id = 40046  # Everett (WA)
    season = 1920
    
    success = generate_season_page(team_id, season)
    
    if success:
        print(f"\n✓ Season page generated successfully!")
        print(f"View at: docs/pages/teams/wa/wa-everett-everett/season/1920.html")
    else:
        print(f"\n✗ Failed to generate season page")