"""
Generate Recognition Pages for 2025 Season Champions and Record Setters
Author: David McKnight
Created: December 2024

This script:
1. Queries SQL Server for teams worthy of recognition
2. Generates individual HTML pages for each team
3. Creates an index page listing all recognized teams
4. Saves pages to /docs/recognition/2025/ directory
"""

import pyodbc
import json
import os
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configuration
SQL_SERVER = 'MCKNIGHTS-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
OUTPUT_DIR = r'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\recognition\2025'
TEMPLATE_DIR = r'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\templates'

# SQL Connection
def get_db_connection():
    """Create connection to SQL Server database"""
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SQL_SERVER};'
        f'DATABASE={DATABASE};'
        f'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

def get_recognition_list():
    """Get all teams worthy of recognition in 2025"""
    conn = get_db_connection()
    query = "EXEC Get_2025_Recognition_Report"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_team_details(team_name):
    """Get detailed information for a specific team's recognition page"""
    conn = get_db_connection()
    
    # Team info
    query_team = f"""
    SELECT 
        Team_Name,
        City,
        State,
        Mascot,
        PrimaryColor,
        SecondaryColor,
        TertiaryColor,
        LogoURL,
        School_Logo_URL,
        Website
    FROM 
        HS_Team_Names
    WHERE 
        Team_Name = '{team_name}'
    """
    
    team_info = pd.read_sql(query_team, conn)
    
    # 2025 season stats with state rank
    query_stats = f"""
    SELECT 
        r.Season,
        r.Home AS Team,
        ((r.Offense * 0.5) + (r.Defense * 0.5)) AS Combined,
        r.Offense,
        r.Defense,
        r.Avg_Of_Avg_Of_Home_Modified_Score AS Margin,
        r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS Win_Loss,
        (SELECT COUNT(*) FROM HS_Scores s 
         WHERE (s.Home = r.Home OR s.Visitor = r.Home) 
         AND s.Season = 2025 AND s.Future_Game = 0) AS Games_Played,
        (SELECT COUNT(*) + 1 
         FROM HS_Rankings r2 
         INNER JOIN HS_Team_Names t2 ON r2.Home = t2.Team_Name
         WHERE r2.Season = 2025 
         AND r2.Week = 52 
         AND t2.State = '{team_info.iloc[0]['State']}'
         AND ((r2.Offense * 0.5) + (r2.Defense * 0.5)) > ((r.Offense * 0.5) + (r.Defense * 0.5))
        ) AS State_Rank,
        (SELECT COUNT(*) FROM HS_Team_Names WHERE State = '{team_info.iloc[0]['State']}') AS State_Total_Teams
    FROM 
        HS_Rankings r
    WHERE 
        r.Home = '{team_name}'
        AND r.Season = 2025
        AND r.Week = 52
    """
    
    season_stats = pd.read_sql(query_stats, conn)
    
    # Historical performance
    query_history = f"""
    SELECT 
        r.Season,
        ((r.Offense * 0.5) + (r.Defense * 0.5)) AS Combined,
        r.Offense,
        r.Defense,
        r.Avg_Of_Avg_Of_Home_Modified_Score AS Margin
    FROM 
        HS_Rankings r
    WHERE 
        r.Home = '{team_name}'
        AND r.Week = 52
    ORDER BY 
        r.Season
    """
    
    history = pd.read_sql(query_history, conn)
    
    # 2025 game results
    query_games = f"""
    SELECT 
        Date,
        CASE 
            WHEN Home = '{team_name}' THEN Visitor
            ELSE Home
        END AS Opponent,
        CASE 
            WHEN Home = '{team_name}' THEN 'vs'
            ELSE '@'
        END AS Location_Prefix,
        CASE 
            WHEN Home = '{team_name}' THEN Home_Score
            ELSE Visitor_Score
        END AS Team_Score,
        CASE 
            WHEN Home = '{team_name}' THEN Visitor_Score
            ELSE Home_Score
        END AS Opponent_Score,
        CASE 
            WHEN Home = '{team_name}' AND Home_Score > Visitor_Score THEN 'W'
            WHEN Home = '{team_name}' AND Home_Score < Visitor_Score THEN 'L'
            WHEN Visitor = '{team_name}' AND Visitor_Score > Home_Score THEN 'W'
            WHEN Visitor = '{team_name}' AND Visitor_Score < Home_Score THEN 'L'
            ELSE 'T'
        END AS Result,
        CASE 
            WHEN Home = '{team_name}' THEN Home_Score - Visitor_Score
            ELSE Visitor_Score - Home_Score
        END AS Margin
    FROM 
        HS_Scores
    WHERE 
        Season = 2025
        AND (Home = '{team_name}' OR Visitor = '{team_name}')
        AND Future_Game = 0
    ORDER BY 
        Date
    """
    
    games = pd.read_sql(query_games, conn)
    
    conn.close()
    
    return {
        'team_info': team_info,
        'season_stats': season_stats,
        'history': history,
        'games': games
    }

def sanitize_filename(team_name):
    """Convert team name to safe filename"""
    # Remove state code in parentheses
    import re
    name_without_state = re.sub(r'\s*\([A-Z]{2}\)\s*$', '', team_name)
    
    # Replace spaces and special characters
    safe_name = name_without_state.lower()
    safe_name = safe_name.replace(' ', '-')
    safe_name = re.sub(r'[^a-z0-9\-]', '', safe_name)
    
    return safe_name

def format_color(color):
    """Ensure color is in proper hex format"""
    if not color or pd.isna(color):
        return '#333333'  # Default dark gray
    
    color = str(color).strip()
    if not color.startswith('#'):
        return f'#{color}'
    return color

def calculate_record(games_df):
    """Calculate W-L-T record from games dataframe"""
    if games_df.empty:
        return "0-0-0"
    
    wins = len(games_df[games_df['Result'] == 'W'])
    losses = len(games_df[games_df['Result'] == 'L'])
    ties = len(games_df[games_df['Result'] == 'T'])
    
    return f"{wins}-{losses}" if ties == 0 else f"{wins}-{losses}-{ties}"

def generate_team_page(team_data, recognition_type, improvement=None, previous_best_season=None):
    """Generate HTML page for a single team"""
    
    team_info = team_data['team_info'].iloc[0]
    stats = team_data['season_stats'].iloc[0]
    history = team_data['history']
    games = team_data['games']
    
    # Extract team details
    team_name = team_info['Team_Name']
    city = team_info['City']
    state = team_info['State']
    mascot = team_info['Mascot'] if not pd.isna(team_info['Mascot']) else ''
    
    # Colors
    primary_color = format_color(team_info['PrimaryColor'])
    secondary_color = format_color(team_info['SecondaryColor'])
    tertiary_color = format_color(team_info['TertiaryColor'])
    
    # Logo
    logo_url = team_info['LogoURL'] if not pd.isna(team_info['LogoURL']) else '../images/default-logo.png'
    
    # Statistics
    combined = round(float(stats['Combined']), 4)
    offense = round(float(stats['Offense']), 4)
    defense = round(float(stats['Defense']), 4)
    margin = round(float(stats['Margin']), 2)
    win_loss = round(float(stats['Win_Loss']), 4)
    games_played = int(stats['Games_Played'])
    state_rank = int(stats['State_Rank'])
    
    # Record
    record = calculate_record(games)
    
    # Filename
    filename = f"recognition-2025-{sanitize_filename(team_name)}.html"
    
    # Recognition badges HTML
    badges_html = ""
    if recognition_type in ['state_champion', 'both']:
        badges_html += '<span class="badge bg-primary me-2 fs-5">🏆 2025 State Champion</span>'
    if recognition_type in ['program_record', 'both']:
        badges_html += '<span class="badge bg-success fs-5">📈 All-Time Program Record</span>'
    
    # Achievement text
    if recognition_type == 'state_champion':
        achievement_text = f"""
        <p class="lead">
            {team_name} has been recognized as the <strong>#{state_rank} ranked team in {state}</strong> 
            for the 2025 season based on comprehensive statistical analysis.
        </p>
        <p>
            With a Combined Rating of <strong>{combined}</strong>, {team_name} demonstrated exceptional 
            performance throughout the season, finishing with a record of <strong>{record}</strong>.
        </p>
        """
    elif recognition_type == 'program_record':
        achievement_text = f"""
        <p class="lead">
            {team_name} has set an <strong>all-time program record</strong> with their 2025 season 
            performance, achieving a Combined Rating of <strong>{combined}</strong>.
        </p>
        <p>
            This surpasses the program's previous best of <strong>{round(float(improvement), 4)}</strong> 
            set in {previous_best_season}, representing an improvement of 
            <strong>{round(combined - float(improvement), 4)}</strong> points.
        </p>
        """
    else:  # both
        achievement_text = f"""
        <p class="lead fs-4">
            {team_name} achieved an extraordinary <strong>double recognition</strong> in 2025: 
            winning the {state} state championship while simultaneously setting an all-time program record.
        </p>
        <p>
            With a Combined Rating of <strong>{combined}</strong>, {team_name} ranked <strong>#{state_rank}</strong> 
            in {state} and surpassed the program's previous best of <strong>{round(float(improvement), 4)}</strong> 
            from {previous_best_season}.
        </p>
        <p class="text-success fw-bold fs-5">
            This rare achievement represents the pinnacle of high school football excellence.
        </p>
        """
    
    # Games table HTML
    games_table_html = ""
    if not games.empty:
        for _, game in games.iterrows():
            result_class = 'table-success' if game['Result'] == 'W' else 'table-danger' if game['Result'] == 'L' else 'table-warning'
            games_table_html += f"""
            <tr class="{result_class}">
                <td>{game['Date'].strftime('%m/%d/%Y')}</td>
                <td>{game['Result']}</td>
                <td>{game['Location_Prefix']} {game['Opponent']}</td>
                <td class="text-center">{int(game['Team_Score'])} - {int(game['Opponent_Score'])}</td>
                <td class="text-center">{'+' if game['Margin'] > 0 else ''}{int(game['Margin'])}</td>
            </tr>
            """
    
    # Historical chart data (JSON for Plotly)
    history_data = {
        'seasons': history['Season'].tolist(),
        'combined': [round(float(x), 4) for x in history['Combined'].tolist()],
        'offense': [round(float(x), 4) for x in history['Offense'].tolist()],
        'defense': [round(float(x), 4) for x in history['Defense'].tolist()]
    }
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{team_name} - 2025 Season Recognition | McKnight's American Football</title>
    <meta name="description" content="{team_name} {recognition_type.replace('_', ' ').title()} recognition for 2025 season">
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="../../css/styles.css">
    
    <style>
        .team-banner {{
            background: linear-gradient(135deg, {primary_color}, {secondary_color});
            color: white;
            padding: 3rem 0;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .team-logo {{
            max-width: 200px;
            height: auto;
            background: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .stat-card {{
            background: white;
            border-left: 4px solid {primary_color};
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        
        .stat-value {{
            color: {primary_color};
            font-size: 2rem;
            font-weight: bold;
        }}
        
        .achievement-summary {{
            background: #f8f9fa;
            border-left: 5px solid {primary_color};
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
        }}
        
        .recognition-badges {{
            text-align: center;
            margin: 2rem 0;
        }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="../../index.html">McKnight's American Football</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="../../index.html">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="../index.html">2025 Recognition</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    
    <!-- Team Banner -->
    <div class="team-banner">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3 text-center">
                    <img src="../../{logo_url}" alt="{team_name} Logo" class="team-logo">
                </div>
                <div class="col-md-9">
                    <h1 class="display-4">{team_name}</h1>
                    <h2 class="h3">{city}, {state}{' - ' + mascot if mascot else ''}</h2>
                    <p class="lead mb-0">2025 Season Recognition</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Recognition Badges -->
    <div class="container">
        <div class="recognition-badges">
            {badges_html}
        </div>
    </div>
    
    <!-- Achievement Summary -->
    <div class="container">
        <div class="achievement-summary">
            <h3 class="mb-3">2025 Season Achievement</h3>
            {achievement_text}
        </div>
    </div>
    
    <!-- Statistics Cards -->
    <div class="container mb-5">
        <h3 class="mb-4">Season Statistics</h3>
        <div class="row">
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">Combined Rating</div>
                    <div class="stat-value">{combined}</div>
                </div>
            </div>
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">Offensive Rating</div>
                    <div class="stat-value">{offense}</div>
                </div>
            </div>
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">Defensive Rating</div>
                    <div class="stat-value">{defense}</div>
                </div>
            </div>
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">Avg Margin</div>
                    <div class="stat-value">{'+' if margin > 0 else ''}{margin}</div>
                </div>
            </div>
        </div>
        
        <div class="row mt-3">
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">Season Record</div>
                    <div class="stat-value" style="font-size: 1.5rem;">{record}</div>
                </div>
            </div>
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">Games Played</div>
                    <div class="stat-value">{games_played}</div>
                </div>
            </div>
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">State Rank</div>
                    <div class="stat-value">#{state_rank}</div>
                </div>
            </div>
            <div class="col-md-3 col-sm-6">
                <div class="stat-card">
                    <div class="stat-label">Win/Loss Rating</div>
                    <div class="stat-value" style="font-size: 1.5rem;">{win_loss}</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Historical Performance Chart -->
    <div class="container mb-5">
        <h3 class="mb-4">Program History</h3>
        <div id="historyChart" style="width:100%; height:500px;"></div>
    </div>
    
    <!-- 2025 Game Results -->
    <div class="container mb-5">
        <h3 class="mb-4">2025 Season Results</h3>
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Date</th>
                        <th>W/L</th>
                        <th>Opponent</th>
                        <th class="text-center">Score</th>
                        <th class="text-center">Margin</th>
                    </tr>
                </thead>
                <tbody>
                    {games_table_html}
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Footer -->
    <footer class="bg-dark text-white py-4 mt-5">
        <div class="container text-center">
            <p class="mb-0">McKnight's American Football Rankings</p>
            <p class="mb-0">Preserving High School Football History Since 1869</p>
            <p class="mb-0">
                <a href="https://olderdyad.github.io/static-football-rankings/" class="text-white">
                    Visit Main Site
                </a>
            </p>
        </div>
    </footer>
    
    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.18.0.min.js"></script>
    
    <script>
        // Historical performance chart
        const historyData = {json.dumps(history_data)};
        
        const trace1 = {{
            x: historyData.seasons,
            y: historyData.combined,
            mode: 'lines+markers',
            name: 'Combined Rating',
            line: {{ color: '{primary_color}', width: 3 }},
            marker: {{ size: 8 }}
        }};
        
        const trace2 = {{
            x: historyData.seasons,
            y: historyData.offense,
            mode: 'lines',
            name: 'Offense',
            line: {{ color: '{secondary_color}', width: 2, dash: 'dash' }}
        }};
        
        const trace3 = {{
            x: historyData.seasons,
            y: historyData.defense,
            mode: 'lines',
            name: 'Defense',
            line: {{ color: '{tertiary_color}', width: 2, dash: 'dot' }}
        }};
        
        const layout = {{
            title: '{team_name} - Historical Performance',
            xaxis: {{ 
                title: 'Season',
                showgrid: true,
                gridcolor: '#e0e0e0'
            }},
            yaxis: {{ 
                title: 'Rating',
                showgrid: true,
                gridcolor: '#e0e0e0'
            }},
            hovermode: 'x unified',
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white',
            font: {{ family: 'Arial, sans-serif' }},
            showlegend: true,
            legend: {{
                x: 0,
                y: 1,
                bgcolor: 'rgba(255,255,255,0.8)',
                bordercolor: '#666',
                borderwidth: 1
            }},
            shapes: [{{
                type: 'line',
                x0: 2025,
                y0: 0,
                x1: 2025,
                y1: Math.max(...historyData.combined) * 1.1,
                line: {{
                    color: 'red',
                    width: 2,
                    dash: 'dashdot'
                }}
            }}],
            annotations: [{{
                x: 2025,
                y: Math.max(...historyData.combined) * 1.05,
                text: '2025 Season',
                showarrow: true,
                arrowhead: 2,
                arrowcolor: 'red',
                ax: 0,
                ay: -40
            }}]
        }};
        
        Plotly.newPlot('historyChart', [trace1, trace2, trace3], layout, {{responsive: true}});
    </script>
</body>
</html>
"""
    
    return filename, html_content

def generate_index_page(recognition_df):
    """Generate index page listing all recognized teams"""
    
    # Sort by combined rating
    recognition_df = recognition_df.sort_values('Combined', ascending=False)
    
    # Generate team cards HTML
    cards_html = ""
    for _, row in recognition_df.iterrows():
        filename = f"recognition-2025-{sanitize_filename(row['Team'])}.html"
        
        badges = []
        if row['Is_State_Champion']:
            badges.append('🏆 State Champion')
        if row['Is_Program_Record']:
            badges.append('📈 Program Record')
        
        badges_html = ' | '.join(badges)
        
        primary_color = format_color(row['PrimaryColor'])
        logo_url = row['LogoURL'] if not pd.isna(row['LogoURL']) else 'images/default-logo.png'
        
        cards_html += f"""
        <div class="col-md-4 mb-4">
            <div class="card h-100 team-card" style="border-top: 4px solid {primary_color};">
                <div class="card-body">
                    <div class="text-center mb-3">
                        <img src="../{logo_url}" alt="{row['Team']} Logo" 
                             style="max-width: 100px; height: auto; background: white; padding: 0.5rem; border-radius: 8px;">
                    </div>
                    <h5 class="card-title">{row['Team']}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">{row['City']}, {row['State']}</h6>
                    <p class="card-text">
                        <strong>Combined:</strong> {round(float(row['Combined']), 4)}<br>
                        <strong>Recognition:</strong> {badges_html}
                    </p>
                    <a href="{filename}" class="btn btn-primary btn-sm w-100" 
                       style="background-color: {primary_color}; border-color: {primary_color};">
                        View Recognition Page
                    </a>
                </div>
            </div>
        </div>
        """
    
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2025 Season Recognition | McKnight's American Football</title>
    <meta name="description" content="State champions and program record setters for 2025 high school football season">
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="../css/styles.css">
    
    <style>
        .hero-section {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: white;
            padding: 4rem 0;
            margin-bottom: 3rem;
        }}
        
        .team-card {{
            transition: transform 0.2s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .team-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="../index.html">McKnight's American Football</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="../index.html">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="index.html">2025 Recognition</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    
    <!-- Hero Section -->
    <div class="hero-section">
        <div class="container text-center">
            <h1 class="display-3">2025 Season Recognition</h1>
            <p class="lead">Honoring state champions and teams that set all-time program records</p>
            <p class="mb-0">Total Teams Recognized: {len(recognition_df)}</p>
        </div>
    </div>
    
    <!-- Statistics Summary -->
    <div class="container mb-5">
        <div class="row text-center">
            <div class="col-md-4">
                <div class="p-4 bg-light rounded">
                    <h2 class="display-4">{len(recognition_df[recognition_df['Is_State_Champion'] == 1])}</h2>
                    <p class="text-muted">State Champions</p>
                </div>
            </div>
            <div class="col-md-4">
                <div class="p-4 bg-light rounded">
                    <h2 class="display-4">{len(recognition_df[recognition_df['Is_Program_Record'] == 1])}</h2>
                    <p class="text-muted">Program Records Set</p>
                </div>
            </div>
            <div class="col-md-4">
                <div class="p-4 bg-light rounded">
                    <h2 class="display-4">{len(recognition_df[(recognition_df['Is_State_Champion'] == 1) & (recognition_df['Is_Program_Record'] == 1)])}</h2>
                    <p class="text-muted">Double Recognition</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Team Cards Grid -->
    <div class="container mb-5">
        <h2 class="mb-4">Recognized Teams</h2>
        <div class="row">
            {cards_html}
        </div>
    </div>
    
    <!-- Footer -->
    <footer class="bg-dark text-white py-4">
        <div class="container text-center">
            <p class="mb-0">McKnight's American Football Rankings</p>
            <p class="mb-0">Preserving High School Football History Since 1869</p>
            <p class="mb-0">
                <a href="https://olderdyad.github.io/static-football-rankings/" class="text-white">
                    Visit Main Site
                </a>
            </p>
        </div>
    </footer>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    
    return index_html

def main():
    """Main execution function"""
    print("=" * 80)
    print("2025 SEASON RECOGNITION PAGE GENERATOR")
    print("=" * 80)
    print()
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    # Get recognition list
    print("Fetching recognition list from database...")
    recognition_df = get_recognition_list()
    print(f"Found {len(recognition_df)} teams worthy of recognition")
    print()
    
    # Generate individual team pages
    print("Generating individual team pages...")
    generated_files = []
    
    for idx, row in recognition_df.iterrows():
        team_name = row['Team']
        print(f"  Processing: {team_name}")
        
        # Get detailed team data
        team_data = get_team_details(team_name)
        
        # Determine recognition type
        if row['Is_State_Champion'] and row['Is_Program_Record']:
            recognition_type = 'both'
        elif row['Is_State_Champion']:
            recognition_type = 'state_champion'
        else:
            recognition_type = 'program_record'
        
        # Get improvement data for program records
        improvement = row['Record_Margin'] if not pd.isna(row['Record_Margin']) else None
        
        # Generate page
        filename, html_content = generate_team_page(
            team_data, 
            recognition_type,
            improvement=improvement
        )
        
        # Save file
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        generated_files.append(filename)
        print(f"    ✓ Generated: {filename}")
    
    print()
    print(f"Generated {len(generated_files)} team pages")
    print()
    
    # Generate index page
    print("Generating index page...")
    index_html = generate_index_page(recognition_df)
    index_path = os.path.join(OUTPUT_DIR, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("  ✓ Generated: index.html")
    print()
    
    # Summary
    print("=" * 80)
    print("GENERATION COMPLETE")
    print("=" * 80)
    print(f"Total pages generated: {len(generated_files) + 1}")
    print(f"State Champions: {len(recognition_df[recognition_df['Is_State_Champion'] == 1])}")
    print(f"Program Records: {len(recognition_df[recognition_df['Is_Program_Record'] == 1])}")
    print(f"Double Recognition: {len(recognition_df[(recognition_df['Is_State_Champion'] == 1) & (recognition_df['Is_Program_Record'] == 1)])}")
    print()
    print(f"Files saved to: {OUTPUT_DIR}")
    print()
    print("Next steps:")
    print("1. Review generated pages")
    print("2. Commit to git: git add docs/recognition/2025/*")
    print("3. Push to GitHub: git push")
    print("4. Begin email outreach using Recognition_Tracking_2025.xlsx")
    print()

if __name__ == "__main__":
    main()
