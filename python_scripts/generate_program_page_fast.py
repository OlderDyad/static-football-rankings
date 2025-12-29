# generate_everett_program_page.py
"""
Hardcoded Everett program page generator
Skips all slow queries - just gets basics
"""

import pyodbc
import os
from jinja2 import Template
import logging

# --- CONFIGURATION ---
SERVER = "McKnights-PC\\SQLEXPRESS01"
DATABASE = "hs_football_database"
TEMPLATE_PATH = "../templates/program_page_template.html"
OUTPUT_BASE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/pages/teams"
TEAM_ID = 40046
# --- END CONFIGURATION ---

logging.basicConfig(level=logging.INFO, format='%(message)s')

def get_everett_data():
    """Get Everett data with minimal queries"""
    
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        # Hardcoded data we know
        data = {
            'team_id': TEAM_ID,
            'team_name': 'Everett (WA)',
            'city': 'Everett',
            'state': 'WA',
            'mascot': 'Seagulls',
            'primary_color': '#003366',
            'secondary_color': '#0066cc',
            'logo_url': None,
            'school_logo_url': None,
            'team_slug': 'wa-everett-everett',
            'stadium': None,
            'year_founded': None,
            'all_time_rank': 1,  # We know Everett is #1
            'total_seasons': 100,  # Approximate
            'first_season': 1908,
            'last_season': 2025,
            'national_championships': 1
        }
        
        logging.info("Getting seasons list...")
        
        # Simple seasons query - NO subqueries, NO EXISTS
        cursor.execute("""
            SELECT 
                Season,
                CAST(Combined_Rating AS DECIMAL(10,3)) AS Rating,
                Games_Played
            FROM Rankings_Combined
            WHERE Team = 'Everett (WA)'
            ORDER BY Season DESC
        """)
        
        data['seasons'] = []
        for row in cursor.fetchall():
            rating = row.Rating
            if rating >= 70:
                rating_class = 'rating-excellent'
            elif rating >= 50:
                rating_class = 'rating-good'
            else:
                rating_class = 'rating-average'
            
            data['seasons'].append({
                'year': row.Season,
                'record': f"{row.Games_Played} games",
                'rating': f"{rating:.1f}",
                'rating_class': rating_class,
                'rank': '',
                'is_national_champion': (row.Season == 1920),  # Hardcode
                'has_page': (row.Season == 1920)  # Only 1920 exists
            })
        
        logging.info(f"Loaded {len(data['seasons'])} seasons")
        
        # Championship
        data['championships'] = [{
            'season': 1920,
            'record': '9-0-1',
            'coach': 'Enoch Bagshaw',
            'source': 'Various Sources',
            'has_season_page': True
        }]
        
        # Coaches
        cursor.execute("""
            SELECT Coach_Name, Start_Year, End_Year, Notes
            FROM Team_Coaches WHERE Team_ID = ?
        """, TEAM_ID)
        
        data['coaches'] = []
        for row in cursor.fetchall():
            data['coaches'].append({
                'name': row.Coach_Name,
                'start_year': row.Start_Year,
                'end_year': row.End_Year,
                'record': None,
                'championships': None,
                'notes': row.Notes
            })
        
        logging.info(f"Loaded {len(data['coaches'])} coaches")
        
        # Decades - simple aggregation
        cursor.execute("""
            SELECT 
                (Season/10)*10 AS Decade,
                COUNT(*) AS Seasons,
                CAST(AVG(Combined_Rating) AS DECIMAL(10,3)) AS Avg,
                CAST(MAX(Combined_Rating) AS DECIMAL(10,3)) AS Best
            FROM Rankings_Combined
            WHERE Team = 'Everett (WA)'
            GROUP BY (Season/10)*10
            ORDER BY Decade DESC
        """)
        
        data['decades'] = []
        for row in cursor.fetchall():
            data['decades'].append({
                'decade': row.Decade,
                'seasons': row.Seasons,
                'avg_rating': f"{row.Avg:.1f}",
                'best_rating': f"{row.Best:.1f}"
            })
        
        logging.info(f"Loaded {len(data['decades'])} decades")
        
        return data


if __name__ == "__main__":
    print("="*60)
    print("EVERETT PROGRAM PAGE GENERATOR")
    print("="*60)
    print()
    
    try:
        # Get data
        logging.info("Fetching Everett data...")
        data = get_everett_data()
        
        # Load template
        logging.info("Loading template...")
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template = Template(f.read())
        
        # Render
        logging.info("Rendering HTML...")
        html = template.render(**data)
        
        # Write file
        output_dir = os.path.join(OUTPUT_BASE, 'wa', 'wa-everett-everett')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'index.html')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print()
        print("="*60)
        print("✓ SUCCESS!")
        print("="*60)
        print(f"Generated: {output_file}")
        print()
        print("Next steps:")
        print("1. Open in browser to test")
        print("2. git add docs/pages/teams/wa/wa-everett-everett/")
        print("3. git commit and push")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()