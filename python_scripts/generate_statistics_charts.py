"""
Generate cumulative games added visualization for McKnight's Football Rankings
This script creates an interactive chart showing the growth of the database over time
"""

import pyodbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import os

# Database connection
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;"

def get_games_data():
    """Extract games data from database"""
    conn = pyodbc.connect(conn_str)
    
    # Query to get games by season and year added
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
    
    # Get summary statistics
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

def create_cumulative_chart(df, summary_df):
    """Create cumulative stacked area chart"""
    
    # Pivot data to have seasons as rows and years_added as columns
    pivot_df = df.pivot_table(
        index='Season', 
        columns='Year_Added', 
        values='Games_Count', 
        fill_value=0
    )
    
    # Create cumulative sum for each year added
    cumulative_df = pivot_df.cumsum(axis=0)
    
    # Create the figure
    fig = go.Figure()
    
    # Add traces for each year (stacked)
    years = sorted(pivot_df.columns)
    
    # Define a color palette
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    
    for idx, year in enumerate(years):
        fig.add_trace(go.Scatter(
            x=cumulative_df.index,
            y=cumulative_df[year],
            name=f'Added in {int(year)}',
            mode='lines',
            stackgroup='one',
            fillcolor=colors[idx % len(colors)],
            line=dict(width=0.5, color=colors[idx % len(colors)]),
            hovertemplate='<b>Season %{x}</b><br>' +
                         f'Added in {int(year)}: %{{y:,.0f}} cumulative games<br>' +
                         '<extra></extra>'
        ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Cumulative Games Added to Database by Season',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        xaxis_title='Season',
        yaxis_title='Cumulative Number of Games',
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12),
        legend=dict(
            title='Year Added',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='lightgray',
            borderwidth=1
        ),
        margin=dict(r=200),
        height=600,
        xaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True
        ),
        yaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True,
            tickformat=',d'
        )
    )
    
    return fig

def create_annual_additions_chart(df):
    """Create bar chart showing games added each year"""
    
    # Sum games by year added
    annual_df = df.groupby('Year_Added')['Games_Count'].sum().reset_index()
    annual_df.columns = ['Year', 'Games_Added']
    annual_df = annual_df.sort_values('Year')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=annual_df['Year'],
        y=annual_df['Games_Added'],
        marker_color='steelblue',
        hovertemplate='<b>%{x}</b><br>' +
                     'Games Added: %{y:,.0f}<br>' +
                     '<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': 'Games Added to Database by Year',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'family': 'Arial, sans-serif'}
        },
        xaxis_title='Year Added',
        yaxis_title='Number of Games',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12),
        height=400,
        xaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True
        ),
        yaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True,
            tickformat=',d'
        )
    )
    
    return fig

def save_charts(cumulative_fig, annual_fig, summary_df, output_dir):
    """Save charts and data"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save cumulative chart
    cumulative_fig.write_html(
        os.path.join(output_dir, 'cumulative_games.html'),
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    # Save annual additions chart
    annual_fig.write_html(
        os.path.join(output_dir, 'annual_additions.html'),
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    # Save summary statistics as JSON
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
    print(f"   - cumulative_games.html")
    print(f"   - annual_additions.html")
    print(f"   - statistics_summary.json")
    
    return summary_dict

def main():
    print("🏈 Generating Database Statistics Visualizations")
    print("=" * 60)
    
    # Extract data
    print("\n📊 Extracting data from database...")
    df, summary_df = get_games_data()
    print(f"   Found {len(df)} season/year combinations")
    
    # Create charts
    print("\n📈 Creating cumulative chart...")
    cumulative_fig = create_cumulative_chart(df, summary_df)
    
    print("📊 Creating annual additions chart...")
    annual_fig = create_annual_additions_chart(df)
    
    # Save outputs
    output_dir = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/data/statistics"
    print(f"\n💾 Saving charts to {output_dir}...")
    summary_dict = save_charts(cumulative_fig, annual_fig, summary_df, output_dir)
    
    # Print summary
    print("\n📋 Database Summary:")
    print(f"   Total Games: {summary_dict['total_games']:,}")
    print(f"   Seasons Covered: {summary_dict['earliest_season']} - {summary_dict['latest_season']}")
    print(f"   Total Seasons: {summary_dict['total_seasons']:,}")
    print(f"   Years Adding Data: {summary_dict['years_adding_data']}")
    print(f"   Last Updated: {summary_dict['last_updated']}")
    
    print("\n✅ Process complete!")

if __name__ == "__main__":
    main()
