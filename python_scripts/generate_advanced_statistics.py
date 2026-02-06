"""
Generate Advanced Statistics Visualizations for McKnight's Football Rankings
Phase 1: Top 6 Charts

1. Avg Scores & Margin by Decade
2. Most Common Final Scores
3. Rating Distribution by Decade
4. Blowout vs. Close Game Trends
5. Coverage Heatmap (Season × State)
6. Avg Scores by Rating Bin

FIXES:
- Forfeit filter: (Forfeit IS NULL OR Forfeit = 0) instead of Forfeit IS NULL
- Combined Rating: Calculated on-the-fly using formula instead of column
- Most Common Scores: Fixed to show score strings properly
"""

import pyodbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime
import json
import os

# Database connection
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;"

OUTPUT_DIR = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/data/statistics"

# Combined Rating formula: 0.958 * Margin + 2.791
# Where Margin = Avg_Of_Avg_Of_Home_Modified_Score (NOT the Win_Loss version)
COMBINED_RATING_FORMULA = "(0.958 * Avg_Of_Avg_Of_Home_Modified_Score + 2.791)"


def get_connection():
    return pyodbc.connect(conn_str)


# =============================================================================
# CHART 1: Average Scores & Margin by Decade
# =============================================================================
def get_scores_by_decade():
    """Get average winning score, losing score, and margin by decade"""
    conn = get_connection()
    
    query = """
    SELECT 
        (Season / 10) * 10 AS Decade,
        COUNT(*) AS Games,
        AVG(CAST(CASE WHEN Home_Score >= Visitor_Score THEN Home_Score ELSE Visitor_Score END AS FLOAT)) AS Avg_Winner_Score,
        AVG(CAST(CASE WHEN Home_Score < Visitor_Score THEN Home_Score ELSE Visitor_Score END AS FLOAT)) AS Avg_Loser_Score,
        AVG(CAST(ABS(Home_Score - Visitor_Score) AS FLOAT)) AS Avg_Margin,
        AVG(CAST(Home_Score + Visitor_Score AS FLOAT)) AS Avg_Total_Points
    FROM HS_Scores
    WHERE Season >= 1900 
        AND Season <= 2025
        AND Home_Score IS NOT NULL 
        AND Visitor_Score IS NOT NULL
        AND (Forfeit IS NULL OR Forfeit = 0)
    GROUP BY (Season / 10) * 10
    ORDER BY Decade
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def create_scores_by_decade_chart(df):
    """Create grouped bar chart for scores by decade"""
    
    fig = go.Figure()
    
    # Winner score bars
    fig.add_trace(go.Bar(
        x=df['Decade'].astype(str) + 's',
        y=df['Avg_Winner_Score'],
        name='Avg Winner Score',
        marker_color='#2ECC71',
        hovertemplate='<b>%{x}</b><br>Avg Winner: %{y:.1f}<extra></extra>'
    ))
    
    # Loser score bars
    fig.add_trace(go.Bar(
        x=df['Decade'].astype(str) + 's',
        y=df['Avg_Loser_Score'],
        name='Avg Loser Score',
        marker_color='#E74C3C',
        hovertemplate='<b>%{x}</b><br>Avg Loser: %{y:.1f}<extra></extra>'
    ))
    
    # Margin line
    fig.add_trace(go.Scatter(
        x=df['Decade'].astype(str) + 's',
        y=df['Avg_Margin'],
        name='Avg Margin',
        mode='lines+markers',
        line=dict(color='#3498DB', width=3),
        marker=dict(size=10),
        yaxis='y2',
        hovertemplate='<b>%{x}</b><br>Avg Margin: %{y:.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title={'text': 'Average Scores & Margin by Decade', 'x': 0.5, 'font': {'size': 22}},
        xaxis_title='Decade',
        yaxis_title='Average Score',
        yaxis2=dict(title='Average Margin', overlaying='y', side='right', showgrid=False),
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        height=500,
        hovermode='x unified'
    )
    
    fig.update_xaxes(gridcolor='lightgray', showline=True, linecolor='black')
    fig.update_yaxes(gridcolor='lightgray', showline=True, linecolor='black')
    
    return fig


# =============================================================================
# CHART 2: Most Common Final Scores
# =============================================================================
def get_common_scores():
    """Get most common final score combinations"""
    conn = get_connection()
    
    query = """
    SELECT TOP 30
        CASE WHEN Home_Score >= Visitor_Score 
             THEN CAST(Home_Score AS VARCHAR) + '-' + CAST(Visitor_Score AS VARCHAR)
             ELSE CAST(Visitor_Score AS VARCHAR) + '-' + CAST(Home_Score AS VARCHAR)
        END AS Final_Score,
        COUNT(*) AS Occurrences
    FROM HS_Scores
    WHERE Home_Score IS NOT NULL 
        AND Visitor_Score IS NOT NULL
        AND (Forfeit IS NULL OR Forfeit = 0)
        AND Season >= 1900
    GROUP BY 
        CASE WHEN Home_Score >= Visitor_Score 
             THEN CAST(Home_Score AS VARCHAR) + '-' + CAST(Visitor_Score AS VARCHAR)
             ELSE CAST(Visitor_Score AS VARCHAR) + '-' + CAST(Home_Score AS VARCHAR)
        END
    ORDER BY COUNT(*) DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def create_common_scores_chart(df):
    """Create horizontal bar chart of most common final scores"""
    
    # Reverse for horizontal bar chart (top scores at top)
    df_plot = df.iloc[::-1].reset_index(drop=True)
    
    # CRITICAL: Convert to string and add quotes/prefix to prevent Plotly interpreting as math
    # "14-0" gets interpreted as 14 minus 0 = 14, so we need to force text
    df_plot['Final_Score_Text'] = df_plot['Final_Score'].astype(str)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_plot['Occurrences'],
        y=df_plot['Final_Score_Text'],
        orientation='h',
        marker_color='#9B59B6',
        hovertemplate='<b>%{y}</b><br>Occurrences: %{x:,}<extra></extra>'
    ))
    
    fig.update_layout(
        title={'text': 'Most Common Final Scores (All-Time)', 'x': 0.5, 'font': {'size': 22}},
        xaxis_title='Number of Games',
        yaxis_title='Final Score (Winner-Loser)',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=700,
        margin=dict(l=100),
        yaxis=dict(type='category')  # Force categorical axis
    )
    
    fig.update_xaxes(gridcolor='lightgray', showline=True, linecolor='black', tickformat=',d')
    fig.update_yaxes(showline=True, linecolor='black')
    
    return fig


# =============================================================================
# CHART 3: Rating Distribution by Decade - FIXED with calculated Combined Rating
# =============================================================================
def get_ratings_by_decade():
    """Get rating distributions by decade using calculated Combined Rating"""
    conn = get_connection()
    
    # Calculate Combined Rating on-the-fly instead of using the column
    query = f"""
    SELECT 
        (Season / 10) * 10 AS Decade,
        {COMBINED_RATING_FORMULA} AS Combined_Rating
    FROM HS_Rankings
    WHERE Season >= 1900 
        AND Season <= 2025
        AND Week = 52
        AND Avg_Of_Avg_Of_Home_Modified_Score IS NOT NULL
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def create_ratings_by_decade_chart(df):
    """Create box plot of rating distributions by decade"""
    
    df['Decade_Label'] = df['Decade'].astype(str) + 's'
    
    fig = go.Figure()
    
    decades = sorted(df['Decade'].unique())
    colors = px.colors.qualitative.Set3
    
    for i, decade in enumerate(decades):
        decade_data = df[df['Decade'] == decade]['Combined_Rating']
        fig.add_trace(go.Box(
            y=decade_data,
            name=f"{decade}s",
            marker_color=colors[i % len(colors)],
            boxpoints='outliers'
        ))
    
    fig.update_layout(
        title={'text': 'Team Rating Distribution by Decade', 'x': 0.5, 'font': {'size': 22}},
        xaxis_title='Decade',
        yaxis_title='Combined Rating',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=500,
        showlegend=False
    )
    
    fig.update_xaxes(showline=True, linecolor='black')
    fig.update_yaxes(gridcolor='lightgray', showline=True, linecolor='black')
    
    return fig


# =============================================================================
# CHART 4: Blowout vs. Close Game Trends
# =============================================================================
def get_game_competitiveness():
    """Get percentage of close vs blowout games by decade"""
    conn = get_connection()
    
    query = """
    SELECT 
        (Season / 10) * 10 AS Decade,
        COUNT(*) AS Total_Games,
        SUM(CASE WHEN ABS(Home_Score - Visitor_Score) <= 7 THEN 1 ELSE 0 END) AS Close_Games,
        SUM(CASE WHEN ABS(Home_Score - Visitor_Score) BETWEEN 8 AND 14 THEN 1 ELSE 0 END) AS Moderate_Games,
        SUM(CASE WHEN ABS(Home_Score - Visitor_Score) BETWEEN 15 AND 21 THEN 1 ELSE 0 END) AS Comfortable_Games,
        SUM(CASE WHEN ABS(Home_Score - Visitor_Score) > 21 THEN 1 ELSE 0 END) AS Blowout_Games
    FROM HS_Scores
    WHERE Season >= 1900 
        AND Season <= 2025
        AND Home_Score IS NOT NULL 
        AND Visitor_Score IS NOT NULL
        AND (Forfeit IS NULL OR Forfeit = 0)
    GROUP BY (Season / 10) * 10
    ORDER BY Decade
    """
    
    df = pd.read_sql(query, conn)
    
    # Calculate percentages
    df['Close_Pct'] = (df['Close_Games'] / df['Total_Games'] * 100).round(1)
    df['Moderate_Pct'] = (df['Moderate_Games'] / df['Total_Games'] * 100).round(1)
    df['Comfortable_Pct'] = (df['Comfortable_Games'] / df['Total_Games'] * 100).round(1)
    df['Blowout_Pct'] = (df['Blowout_Games'] / df['Total_Games'] * 100).round(1)
    
    conn.close()
    return df


def create_competitiveness_chart(df):
    """Create stacked area chart of game competitiveness"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['Decade'].astype(str) + 's',
        y=df['Close_Pct'],
        name='Close (≤7 pts)',
        mode='lines',
        stackgroup='one',
        fillcolor='rgba(46, 204, 113, 0.7)',
        line=dict(color='#2ECC71'),
        hovertemplate='<b>%{x}</b><br>Close: %{y:.1f}%<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Decade'].astype(str) + 's',
        y=df['Moderate_Pct'],
        name='Moderate (8-14 pts)',
        mode='lines',
        stackgroup='one',
        fillcolor='rgba(241, 196, 15, 0.7)',
        line=dict(color='#F1C40F'),
        hovertemplate='<b>%{x}</b><br>Moderate: %{y:.1f}%<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Decade'].astype(str) + 's',
        y=df['Comfortable_Pct'],
        name='Comfortable (15-21 pts)',
        mode='lines',
        stackgroup='one',
        fillcolor='rgba(230, 126, 34, 0.7)',
        line=dict(color='#E67E22'),
        hovertemplate='<b>%{x}</b><br>Comfortable: %{y:.1f}%<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Decade'].astype(str) + 's',
        y=df['Blowout_Pct'],
        name='Blowout (>21 pts)',
        mode='lines',
        stackgroup='one',
        fillcolor='rgba(231, 76, 60, 0.7)',
        line=dict(color='#E74C3C'),
        hovertemplate='<b>%{x}</b><br>Blowout: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title={'text': 'Game Competitiveness by Decade', 'x': 0.5, 'font': {'size': 22}},
        xaxis_title='Decade',
        yaxis_title='Percentage of Games',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        height=500,
        hovermode='x unified'
    )
    
    fig.update_xaxes(showline=True, linecolor='black')
    fig.update_yaxes(gridcolor='lightgray', showline=True, linecolor='black', range=[0, 100])
    
    return fig


# =============================================================================
# CHART 5: Coverage Heatmap (Season × State)
# =============================================================================
def get_coverage_data():
    """Get game counts by season and state"""
    conn = get_connection()
    
    query = """
    SELECT 
        Season,
        CASE 
            WHEN RIGHT(Home, 5) LIKE '%(%)' THEN SUBSTRING(RIGHT(Home, 4), 2, 2)
            WHEN RIGHT(Home, 6) = '(Ont)' THEN 'ON'
            ELSE 'Other'
        END AS State,
        COUNT(*) AS Games
    FROM HS_Scores
    WHERE Season >= 1900 
        AND Season <= 2025
        AND Home IS NOT NULL
    GROUP BY 
        Season,
        CASE 
            WHEN RIGHT(Home, 5) LIKE '%(%)' THEN SUBSTRING(RIGHT(Home, 4), 2, 2)
            WHEN RIGHT(Home, 6) = '(Ont)' THEN 'ON'
            ELSE 'Other'
        END
    HAVING CASE 
            WHEN RIGHT(Home, 5) LIKE '%(%)' THEN SUBSTRING(RIGHT(Home, 4), 2, 2)
            WHEN RIGHT(Home, 6) = '(Ont)' THEN 'ON'
            ELSE 'Other'
        END != 'Other'
    ORDER BY Season, State
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def create_coverage_heatmap(df):
    """Create heatmap showing coverage by season and state"""
    
    # Pivot the data
    pivot_df = df.pivot_table(index='State', columns='Season', values='Games', fill_value=0)
    
    # Get top 25 states by total games
    state_totals = pivot_df.sum(axis=1).sort_values(ascending=False)
    top_states = state_totals.head(25).index.tolist()
    pivot_df = pivot_df.loc[top_states]
    
    # Sample every 5th year for readability
    years = [y for y in pivot_df.columns if y % 5 == 0]
    pivot_df = pivot_df[years]
    
    fig = go.Figure(data=go.Heatmap(
        z=np.log1p(pivot_df.values),  # Log scale for better visualization
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='YlOrRd',
        hovertemplate='<b>%{y}</b> - %{x}<br>Games: %{customdata:,}<extra></extra>',
        customdata=pivot_df.values
    ))
    
    fig.update_layout(
        title={'text': 'Database Coverage by State & Season (Top 25 States)', 'x': 0.5, 'font': {'size': 22}},
        xaxis_title='Season',
        yaxis_title='State',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=700
    )
    
    return fig


# =============================================================================
# CHART 6: Average Scores by Rating Bin - FIXED with calculated Combined Rating
# =============================================================================
def get_scores_by_rating():
    """Get average scores based on team ratings"""
    conn = get_connection()
    
    # Use calculated Combined Rating with proper rating bins including negatives
    query = f"""
    WITH TeamRatings AS (
        SELECT 
            Home,
            Season,
            {COMBINED_RATING_FORMULA} AS Combined_Rating
        FROM HS_Rankings
        WHERE Week = 52
            AND Avg_Of_Avg_Of_Home_Modified_Score IS NOT NULL
    ),
    GameScores AS (
        SELECT 
            s.Season,
            s.Home,
            s.Visitor,
            s.Home_Score,
            s.Visitor_Score,
            hr.Combined_Rating AS Home_Rating
        FROM HS_Scores s
        INNER JOIN TeamRatings hr ON s.Home = hr.Home AND s.Season = hr.Season
        WHERE s.Season >= 1950
            AND s.Home_Score IS NOT NULL
            AND s.Visitor_Score IS NOT NULL
            AND (s.Forfeit IS NULL OR s.Forfeit = 0)
    )
    SELECT 
        CASE 
            WHEN Home_Rating >= 80 THEN '80+'
            WHEN Home_Rating >= 70 THEN '70-79'
            WHEN Home_Rating >= 60 THEN '60-69'
            WHEN Home_Rating >= 50 THEN '50-59'
            WHEN Home_Rating >= 40 THEN '40-49'
            WHEN Home_Rating >= 30 THEN '30-39'
            WHEN Home_Rating >= 20 THEN '20-29'
            WHEN Home_Rating >= 10 THEN '10-19'
            WHEN Home_Rating >= 0 THEN '0-9'
            WHEN Home_Rating >= -10 THEN '-10 to -1'
            WHEN Home_Rating >= -20 THEN '-20 to -11'
            WHEN Home_Rating >= -30 THEN '-30 to -21'
            ELSE 'Below -30'
        END AS Rating_Bin,
        COUNT(*) AS Games,
        AVG(CAST(Home_Score AS FLOAT)) AS Avg_Points_For,
        AVG(CAST(Visitor_Score AS FLOAT)) AS Avg_Points_Against,
        AVG(CAST(Home_Score - Visitor_Score AS FLOAT)) AS Avg_Margin
    FROM GameScores
    GROUP BY 
        CASE 
            WHEN Home_Rating >= 80 THEN '80+'
            WHEN Home_Rating >= 70 THEN '70-79'
            WHEN Home_Rating >= 60 THEN '60-69'
            WHEN Home_Rating >= 50 THEN '50-59'
            WHEN Home_Rating >= 40 THEN '40-49'
            WHEN Home_Rating >= 30 THEN '30-39'
            WHEN Home_Rating >= 20 THEN '20-29'
            WHEN Home_Rating >= 10 THEN '10-19'
            WHEN Home_Rating >= 0 THEN '0-9'
            WHEN Home_Rating >= -10 THEN '-10 to -1'
            WHEN Home_Rating >= -20 THEN '-20 to -11'
            WHEN Home_Rating >= -30 THEN '-30 to -21'
            ELSE 'Below -30'
        END
    ORDER BY Rating_Bin DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Debug output
    print(f"   Rating bins found: {df['Rating_Bin'].tolist()}")
    print(f"   Game counts: {df['Games'].tolist()}")
    
    return df


def create_scores_by_rating_chart(df):
    """Create grouped bar chart of scores by rating bin"""
    
    # Define proper order (highest to lowest)
    order = ['80+', '70-79', '60-69', '50-59', '40-49', '30-39', '20-29', '10-19', '0-9', 
             '-10 to -1', '-20 to -11', '-30 to -21', 'Below -30']
    
    # Filter to only bins that exist in data
    existing_order = [b for b in order if b in df['Rating_Bin'].values]
    
    df['Rating_Bin'] = pd.Categorical(df['Rating_Bin'], categories=existing_order, ordered=True)
    df = df.sort_values('Rating_Bin')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['Rating_Bin'],
        y=df['Avg_Points_For'],
        name='Avg Points Scored',
        marker_color='#2ECC71',
        hovertemplate='<b>Rating %{x}</b><br>Avg Scored: %{y:.1f}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        x=df['Rating_Bin'],
        y=df['Avg_Points_Against'],
        name='Avg Points Allowed',
        marker_color='#E74C3C',
        hovertemplate='<b>Rating %{x}</b><br>Avg Allowed: %{y:.1f}<extra></extra>'
    ))
    
    # Add margin line
    fig.add_trace(go.Scatter(
        x=df['Rating_Bin'],
        y=df['Avg_Margin'],
        name='Avg Margin',
        mode='lines+markers',
        line=dict(color='#3498DB', width=3),
        marker=dict(size=10),
        yaxis='y2',
        hovertemplate='<b>Rating %{x}</b><br>Avg Margin: %{y:+.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title={'text': 'Average Scores by Team Rating', 'x': 0.5, 'font': {'size': 22}},
        xaxis_title='Team Rating Bin',
        yaxis_title='Average Points',
        yaxis2=dict(title='Average Margin', overlaying='y', side='right', showgrid=False),
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        height=500,
        hovermode='x unified'
    )
    
    fig.update_xaxes(showline=True, linecolor='black')
    fig.update_yaxes(gridcolor='lightgray', showline=True, linecolor='black')
    
    return fig


# =============================================================================
# MAIN
# =============================================================================
def save_chart(fig, filename):
    """Save chart to HTML file"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    fig.write_html(filepath, include_plotlyjs='cdn', config={'displayModeBar': True, 'displaylogo': False})
    print(f"   ✅ Saved: {filename}")


def main():
    print("🏈 Generating Advanced Statistics Visualizations")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Chart 1: Scores by Decade
    print("\n📊 Chart 1: Average Scores & Margin by Decade...")
    df1 = get_scores_by_decade()
    fig1 = create_scores_by_decade_chart(df1)
    save_chart(fig1, 'scores_by_decade.html')
    
    # Chart 2: Common Final Scores
    print("\n📊 Chart 2: Most Common Final Scores...")
    df2 = get_common_scores()
    print(f"   Top 5 scores: {df2.head()['Final_Score'].tolist()}")
    fig2 = create_common_scores_chart(df2)
    save_chart(fig2, 'common_scores.html')
    
    # Chart 3: Rating Distribution by Decade
    print("\n📊 Chart 3: Rating Distribution by Decade...")
    df3 = get_ratings_by_decade()
    print(f"   Decades found: {sorted(df3['Decade'].unique())}")
    fig3 = create_ratings_by_decade_chart(df3)
    save_chart(fig3, 'rating_distribution.html')
    
    # Chart 4: Game Competitiveness
    print("\n📊 Chart 4: Blowout vs Close Game Trends...")
    df4 = get_game_competitiveness()
    fig4 = create_competitiveness_chart(df4)
    save_chart(fig4, 'game_competitiveness.html')
    
    # Chart 5: Coverage Heatmap
    print("\n📊 Chart 5: Coverage Heatmap...")
    df5 = get_coverage_data()
    fig5 = create_coverage_heatmap(df5)
    save_chart(fig5, 'coverage_heatmap.html')
    
    # Chart 6: Scores by Rating
    print("\n📊 Chart 6: Average Scores by Rating Bin...")
    df6 = get_scores_by_rating()
    if len(df6) > 0:
        fig6 = create_scores_by_rating_chart(df6)
        save_chart(fig6, 'scores_by_rating.html')
    else:
        print("   ⚠️ No rating data available")
    
    print("\n" + "=" * 60)
    print("✅ Advanced Statistics Generation Complete!")
    print(f"   Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()