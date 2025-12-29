"""
Generate database statistics visualizations for McKnight's Football Rankings
This script creates interactive charts showing:
1. Season Overview - Games played and rating statistics per season (NEW)
2. Cumulative games added to database over time
3. Annual data collection activity
"""

import pyodbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import json
import os

# Database connection
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;"

def get_games_data():
    """Extract games data from database"""
    conn = pyodbc.connect(conn_str)
    
    query = """
    SELECT 
        Season,
        CASE 
            WHEN Date_Added IS NULL THEN 2012
            ELSE YEAR(Date_Added)
        END AS Year_Added,
        COUNT(*) AS Games_Count
    FROM [hs_football_database].[dbo].[HS_Scores]
    WHERE Season IS NOT NULL
    GROUP BY 
        Season,
        CASE 
            WHEN Date_Added IS NULL THEN 2012
            ELSE YEAR(Date_Added)
        END
    ORDER BY Season, Year_Added
    """
    
    df = pd.read_sql(query, conn)
    
    summary_query = """
    SELECT 
        COUNT(*) AS Total_Games,
        MIN(Season) AS Earliest_Season,
        MAX(Season) AS Latest_Season,
        COUNT(DISTINCT Season) AS Total_Seasons,
        COUNT(DISTINCT CASE WHEN Date_Added IS NULL THEN 2012 ELSE YEAR(Date_Added) END) AS Years_Adding_Data
    FROM [hs_football_database].[dbo].[HS_Scores]
    WHERE Season IS NOT NULL
    """
    
    summary_df = pd.read_sql(summary_query, conn)
    conn.close()
    
    return df, summary_df


def get_season_overview_data():
    """Extract season-level data: total games and rating statistics"""
    conn = pyodbc.connect(conn_str)
    
    games_query = """
    SELECT 
        Season,
        COUNT(*) AS Total_Games
    FROM [hs_football_database].[dbo].[HS_Scores]
    WHERE Season IS NOT NULL
        AND Season >= 1877
    GROUP BY Season
    ORDER BY Season
    """
    
    games_df = pd.read_sql(games_query, conn)
    
    ratings_query = """
    SELECT 
        Season,
        AVG(Avg_Of_Avg_Of_Home_Modified_Score) AS Avg_Rating,
        MIN(Avg_Of_Avg_Of_Home_Modified_Score) AS Min_Rating,
        MAX(Avg_Of_Avg_Of_Home_Modified_Score) AS Max_Rating,
        COUNT(*) AS Teams_Rated
    FROM [hs_football_database].[dbo].[HS_Rankings]
    WHERE Season IS NOT NULL
        AND Season >= 1877
        AND Week = 52
    GROUP BY Season
    ORDER BY Season
    """
    
    ratings_df = pd.read_sql(ratings_query, conn)
    conn.close()
    
    merged_df = pd.merge(games_df, ratings_df, on='Season', how='outer')
    merged_df = merged_df.sort_values('Season')
    
    return merged_df


def create_season_overview_chart(df):
    """Create dual-axis chart showing games and ratings by season"""
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=df['Season'],
            y=df['Total_Games'],
            name='Total Games',
            marker_color='rgba(55, 128, 191, 0.7)',
            hovertemplate='<b>Season %{x}</b><br>Games: %{y:,.0f}<extra></extra>'
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['Season'],
            y=df['Avg_Rating'],
            name='Avg Rating',
            mode='lines',
            line=dict(color='#FF6B35', width=2),
            hovertemplate='<b>Season %{x}</b><br>Avg Rating: %{y:.2f}<extra></extra>'
        ),
        secondary_y=True
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['Season'],
            y=df['Max_Rating'],
            name='Max Rating',
            mode='lines',
            line=dict(color='#2ECC71', width=1.5, dash='dot'),
            hovertemplate='<b>Season %{x}</b><br>Max Rating: %{y:.2f}<extra></extra>'
        ),
        secondary_y=True
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['Season'],
            y=df['Min_Rating'],
            name='Min Rating',
            mode='lines',
            line=dict(color='#E74C3C', width=1.5, dash='dot'),
            hovertemplate='<b>Season %{x}</b><br>Min Rating: %{y:.2f}<extra></extra>'
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        title={'text': 'Season Overview: Games Played & Team Ratings (1877-Present)', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 22}},
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        height=550,
        barmode='overlay'
    )
    
    fig.update_xaxes(title_text='Season', gridcolor='lightgray', showline=True, linecolor='black', mirror=True, range=[1875, df['Season'].max() + 2])
    fig.update_yaxes(title_text='Total Games', title_font=dict(color='rgba(55, 128, 191, 1)'), tickfont=dict(color='rgba(55, 128, 191, 1)'), gridcolor='lightgray', tickformat=',d', secondary_y=False)
    fig.update_yaxes(title_text='Rating Value', title_font=dict(color='#FF6B35'), tickfont=dict(color='#FF6B35'), secondary_y=True)
    
    return fig


def create_cumulative_chart(df, summary_df):
    """Create cumulative stacked area chart"""
    
    pivot_df = df.pivot_table(index='Season', columns='Year_Added', values='Games_Count', fill_value=0)
    cumulative_df = pivot_df.cumsum(axis=0)
    
    fig = go.Figure()
    years = sorted(pivot_df.columns)
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    
    for idx, year in enumerate(years):
        fig.add_trace(go.Scatter(
            x=cumulative_df.index, y=cumulative_df[year], name=f'Added in {int(year)}',
            mode='lines', stackgroup='one', fillcolor=colors[idx % len(colors)],
            line=dict(width=0.5, color=colors[idx % len(colors)]),
            hovertemplate=f'<b>Season %{{x}}</b><br>Added in {int(year)}: %{{y:,.0f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title={'text': 'Cumulative Games Added to Database by Season', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 24}},
        xaxis_title='Season', yaxis_title='Cumulative Number of Games',
        hovermode='x unified', plot_bgcolor='white', paper_bgcolor='white',
        legend=dict(title='Year Added', orientation='v', yanchor='top', y=1, xanchor='left', x=1.02),
        margin=dict(r=200), height=600,
        xaxis=dict(gridcolor='lightgray', showline=True, linecolor='black', mirror=True),
        yaxis=dict(gridcolor='lightgray', showline=True, linecolor='black', mirror=True, tickformat=',d')
    )
    
    return fig


def create_annual_additions_chart(df):
    """Create bar chart showing games added each year"""
    
    annual_df = df.groupby('Year_Added')['Games_Count'].sum().reset_index()
    annual_df.columns = ['Year', 'Games_Added']
    annual_df = annual_df.sort_values('Year')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=annual_df['Year'], y=annual_df['Games_Added'], marker_color='steelblue',
                         hovertemplate='<b>%{x}</b><br>Games Added: %{y:,.0f}<extra></extra>'))
    
    fig.update_layout(
        title={'text': 'Games Added to Database by Year', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 20}},
        xaxis_title='Year Added', yaxis_title='Number of Games',
        plot_bgcolor='white', paper_bgcolor='white', height=400,
        xaxis=dict(gridcolor='lightgray', showline=True, linecolor='black', mirror=True),
        yaxis=dict(gridcolor='lightgray', showline=True, linecolor='black', mirror=True, tickformat=',d')
    )
    
    return fig


def save_charts(season_overview_fig, cumulative_fig, annual_fig, summary_df, output_dir):
    """Save charts and data"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    season_overview_fig.write_html(os.path.join(output_dir, 'season_overview.html'), include_plotlyjs='cdn', config={'displayModeBar': True, 'displaylogo': False})
    cumulative_fig.write_html(os.path.join(output_dir, 'cumulative_games.html'), include_plotlyjs='cdn', config={'displayModeBar': True, 'displaylogo': False})
    annual_fig.write_html(os.path.join(output_dir, 'annual_additions.html'), include_plotlyjs='cdn', config={'displayModeBar': True, 'displaylogo': False})
    
    summary_dict = {
        'total_games': int(summary_df['Total_Games'].iloc[0]),
        'earliest_season': int(summary_df['Earliest_Season'].iloc[0]),
        'latest_season': int(summary_df['Latest_Season'].iloc[0]),
        'total_seasons': int(summary_df['Total_Seasons'].iloc[0]),
        'years_adding_data': int(summary_df['Years_Adding_Data'].iloc[0]),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(os.path.join(output_dir, 'statistics_summary.json'), 'w') as f:
        json.dump(summary_dict, f, indent=2)
    
    print(f"✅ Charts saved to {output_dir}")
    print(f"   - season_overview.html (NEW)")
    print(f"   - cumulative_games.html")
    print(f"   - annual_additions.html")
    print(f"   - statistics_summary.json")
    
    return summary_dict


def main():
    print("🏈 Generating Database Statistics Visualizations")
    print("=" * 60)
    
    print("\n📊 Extracting games data from database...")
    df, summary_df = get_games_data()
    print(f"   Found {len(df)} season/year combinations")
    
    print("\n📊 Extracting season overview data (games + ratings)...")
    season_df = get_season_overview_data()
    print(f"   Found {len(season_df)} seasons with data")
    
    print("\n📈 Creating season overview chart (games + ratings)...")
    season_overview_fig = create_season_overview_chart(season_df)
    
    print("📈 Creating cumulative chart...")
    cumulative_fig = create_cumulative_chart(df, summary_df)
    
    print("📊 Creating annual additions chart...")
    annual_fig = create_annual_additions_chart(df)
    
    output_dir = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/data/statistics"
    print(f"\n💾 Saving charts to {output_dir}...")
    summary_dict = save_charts(season_overview_fig, cumulative_fig, annual_fig, summary_df, output_dir)
    
    print("\n📋 Database Summary:")
    print(f"   Total Games: {summary_dict['total_games']:,}")
    print(f"   Seasons Covered: {summary_dict['earliest_season']} - {summary_dict['latest_season']}")
    print(f"   Total Seasons: {summary_dict['total_seasons']:,}")
    print(f"   Years Adding Data: {summary_dict['years_adding_data']}")
    print(f"   Last Updated: {summary_dict['last_updated']}")
    
    print("\n✅ Process complete!")


if __name__ == "__main__":
    main()
