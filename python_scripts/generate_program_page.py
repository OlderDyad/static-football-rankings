# generate_program_page.py
"""
Generate program index pages for teams
Shows all seasons, championships, coaches, decade performance
"""

import pyodbc
import os
from jinja2 import Template
import logging

# --- CONFIGURATION ---
SERVER = "McKnights-PC\\SQLEXPRESS01"
DATABASE = "hs_football_database"
TEMPLATE_PATH = "templates/program_page_template.html"
OUTPUT_BASE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/pages/teams"
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_program_data(team_id):
    """Fetch all data needed for a program page"""
    
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
                    LogoURL, School_Logo_URL, Team_Slug,
                    Stadium, YearFounded
                FROM HS_Team_Names
                WHERE ID = ?
            """, team_id)
            
            row = cursor.fetchone()
            data['team_id'] = team_id
            data['team_name'] = row.Team_Name
            data['city'] = row.City
            data['state'] = row.State
            data['mascot'] = row.Mascot or 'Football'
            data['primary_color'] = row.PrimaryColor or '#003366'
            data['secondary_color'] = row.SecondaryColor or '#0066cc'
            data['logo_url'] = row.LogoURL
            data['school_logo_url'] = row.School_Logo_URL
            data['team_slug'] = row.Team_Slug
            data['stadium'] = row.Stadium
            data['year_founded'] = row.YearFounded
            
            # 2. Get all-time rank and summary stats
            cursor.execute("""
                WITH AllTimeRankings AS (
                    SELECT 
                        Team,
                        AVG(Combined_Rating) AS Avg_Rating,
                        COUNT(DISTINCT Season) AS Seasons,
                        ROW_NUMBER() OVER (ORDER BY AVG(Combined_Rating) DESC) AS Rank
                    FROM Rankings_Combined
                    GROUP BY Team
                    HAVING COUNT(DISTINCT Season) >= 25
                )
                SELECT 
                    Rank,
                    CAST(Avg_Rating AS DECIMAL(10,3)) AS Avg_Rating,
                    Seasons
                FROM AllTimeRankings
                WHERE Team = ?
            """, data['team_name'])
            
            rank_row = cursor.fetchone()
            if rank_row:
                data['all_time_rank'] = rank_row.Rank
                data['avg_rating'] = rank_row.Avg_Rating
                data['total_seasons'] = rank_row.Seasons
            else:
                data['all_time_rank'] = 'N/A'
                data['avg_rating'] = 0
                data['total_seasons'] = 0
            
            # 3. Get season range
            cursor.execute("""
                SELECT 
                    MIN(Season) AS First_Season,
                    MAX(Season) AS Last_Season
                FROM Rankings_Combined
                WHERE Team = ?
            """, data['team_name'])
            
            range_row = cursor.fetchone()
            data['first_season'] = range_row.First_Season if range_row else 'N/A'
            data['last_season'] = range_row.Last_Season if range_row else 'N/A'
            
            # 4. Count national championships
            cursor.execute("""
                SELECT COUNT(*) AS NC_Count
                FROM Media_National_Champions
                WHERE Team_ID = ?
            """, team_id)
            
            nc_row = cursor.fetchone()
            data['national_championships'] = nc_row.NC_Count if nc_row else 0
            
            # 5. Get all seasons with ratings (for seasons table)
            # Pre-calculate records to avoid slow subqueries
            cursor.execute("""
                WITH SeasonRecords AS (
                    SELECT 
                        Season,
                        SUM(CASE 
                            WHEN (Home = ? AND Home_Score > Visitor_Score)
                              OR (Visitor = ? AND Visitor_Score > Home_Score) 
                            THEN 1 ELSE 0 
                        END) AS Wins,
                        SUM(CASE 
                            WHEN (Home = ? AND Home_Score < Visitor_Score)
                              OR (Visitor = ? AND Visitor_Score < Home_Score) 
                            THEN 1 ELSE 0 
                        END) AS Losses,
                        SUM(CASE 
                            WHEN (Home = ? OR Visitor = ?)
                             AND Home_Score = Visitor_Score
                            THEN 1 ELSE 0 
                        END) AS Ties
                    FROM HS_Scores
                    WHERE Home = ? OR Visitor = ?
                    GROUP BY Season
                )
                SELECT 
                    r.Season,
                    CAST(r.Combined_Rating AS DECIMAL(10,3)) AS Rating,
                    ISNULL(rec.Wins, 0) AS Wins,
                    ISNULL(rec.Losses, 0) AS Losses,
                    ISNULL(rec.Ties, 0) AS Ties,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM Media_National_Champions 
                        WHERE Team_ID = ? AND Season = r.Season
                    ) THEN 1 ELSE 0 END AS Is_National_Champion,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM Team_Season_Pages 
                        WHERE Team_ID = ? AND Season = r.Season AND Page_Status = 'Published'
                    ) THEN 1 ELSE 0 END AS Has_Page
                FROM Rankings_Combined r
                LEFT JOIN SeasonRecords rec ON r.Season = rec.Season
                WHERE r.Team = ?
                ORDER BY r.Season DESC
            """, data['team_name'], data['team_name'], data['team_name'], 
                 data['team_name'], data['team_name'], data['team_name'],
                 data['team_name'], data['team_name'], team_id, team_id, data['team_name'])
            
            data['seasons'] = []
            for row in cursor.fetchall():
                wins = row.Wins
                losses = row.Losses
                ties = row.Ties
                
                if ties > 0:
                    record = f"{wins}-{losses}-{ties}"
                else:
                    record = f"{wins}-{losses}"
                
                # Rating class for color coding
                rating = row.Rating
                if rating >= 70:
                    rating_class = 'rating-excellent'
                elif rating >= 50:
                    rating_class = 'rating-good'
                else:
                    rating_class = 'rating-average'
                
                data['seasons'].append({
                    'year': row.Season,
                    'record': record,
                    'rating': f"{rating:.1f}",
                    'rating_class': rating_class,
                    'rank': 'N/A',  # Could calculate if needed
                    'is_national_champion': bool(row.Is_National_Champion),
                    'has_page': bool(row.Has_Page)
                })
            
            # 6. Get championships (detailed)
            cursor.execute("""
                SELECT 
                    m.Season,
                    m.Wins,
                    m.Losses,
                    m.Ties,
                    c.Full_Name AS Coach,
                    m.Source_Full,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM Team_Season_Pages 
                        WHERE Team_ID = ? AND Season = m.Season AND Page_Status = 'Published'
                    ) THEN 1 ELSE 0 END AS Has_Season_Page
                FROM Media_National_Champions m
                LEFT JOIN HS_Coaches c ON m.Coach_ID = c.Coach_ID
                WHERE m.Team_ID = ?
                ORDER BY m.Season DESC
            """, team_id, team_id)
            
            data['championships'] = []
            for row in cursor.fetchall():
                wins = row.Wins or 0
                losses = row.Losses or 0
                ties = row.Ties or 0
                
                if ties > 0:
                    record = f"{wins}-{losses}-{ties}"
                else:
                    record = f"{wins}-{losses}"
                
                data['championships'].append({
                    'season': row.Season,
                    'record': record,
                    'coach': row.Coach,
                    'source': row.Source_Full or 'Various Sources',
                    'has_season_page': bool(row.Has_Season_Page)
                })
            
            # 7. Get coaches
            cursor.execute("""
                SELECT 
                    Coach_Name,
                    Start_Year,
                    End_Year,
                    Total_Wins,
                    Total_Losses,
                    Total_Ties,
                    Championships,
                    Notes
                FROM Team_Coaches
                WHERE Team_ID = ?
                ORDER BY Start_Year
            """, team_id)
            
            data['coaches'] = []
            for row in cursor.fetchall():
                record = None
                if row.Total_Wins is not None:
                    wins = row.Total_Wins
                    losses = row.Total_Losses or 0
                    ties = row.Total_Ties or 0
                    if ties > 0:
                        record = f"{wins}-{losses}-{ties}"
                    else:
                        record = f"{wins}-{losses}"
                
                data['coaches'].append({
                    'name': row.Coach_Name,
                    'start_year': row.Start_Year,
                    'end_year': row.End_Year,
                    'record': record,
                    'championships': row.Championships if row.Championships else None,
                    'notes': row.Notes
                })
            
            # 8. Get decade performance
            cursor.execute("""
                SELECT 
                    (Season / 10) * 10 AS Decade,
                    COUNT(DISTINCT Season) AS Seasons,
                    CAST(AVG(Combined_Rating) AS DECIMAL(10,3)) AS Avg_Rating,
                    CAST(MAX(Combined_Rating) AS DECIMAL(10,3)) AS Best_Rating
                FROM Rankings_Combined
                WHERE Team = ?
                GROUP BY (Season / 10) * 10
                ORDER BY Decade DESC
            """, data['team_name'])
            
            data['decades'] = []
            for row in cursor.fetchall():
                data['decades'].append({
                    'decade': row.Decade,
                    'seasons': row.Seasons,
                    'avg_rating': f"{row.Avg_Rating:.1f}",
                    'best_rating': f"{row.Best_Rating:.1f}"
                })
            
            return data
            
    except Exception as e:
        logging.error(f"Error fetching program data: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_program_page(team_id):
    """Generate HTML program page for a team"""
    
    logging.info(f"Generating program page for Team ID {team_id}")
    
    # Get data
    data = get_program_data(team_id)
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
    output_dir = os.path.join(OUTPUT_BASE, state, slug)
    output_file = os.path.join(output_dir, 'index.html')
    
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
                UPDATE HS_Team_Names
                SET Has_Program_Page = 1,
                    Program_Page_Status = 'Published',
                    Program_Page_URL = ?
                WHERE ID = ?
            """, f"/static-football-rankings/pages/teams/{state}/{slug}/index.html", team_id)
            conn.commit()
        
        return True
        
    except Exception as e:
        logging.error(f"Error writing file: {e}")
        return False


if __name__ == "__main__":
    # Example: Generate Everett program page
    team_id = 40046  # Everett (WA)
    
    success = generate_program_page(team_id)
    
    if success:
        print(f"\n✓ Program page generated successfully!")
        print(f"View at: docs/pages/teams/wa/wa-everett-everett/index.html")
    else:
        print(f"\n✗ Failed to generate program page")