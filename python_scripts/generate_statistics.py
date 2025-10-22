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

def create_cumulative_chart(df):
    pivot_df = df.pivot_table(index='Season', columns='Year_Added', values='Games_Count', fill_value=0)
    cumulative_df = pivot_df.cumsum(axis=0)
    
    fig = go.Figure()
    years = sorted(pivot_df.columns)
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
            hovertemplate='<b>Season %{x}</b><br>Added in ' + str(int(year)) + ': %{y:,.0f} cumulative games<extra></extra>'
        ))
    
    fig.update_layout(
        title='Cumulative Games Added by Season',
        xaxis_title='Season',
        yaxis_title='Cumulative Games',
        hovermode='x unified',
        height=600,
        showlegend=True,
        legend=dict(title='Year Added', orientation='v', yanchor='top', y=1, xanchor='left', x=1.02)
    )
    
    return fig

def create_annual_chart(df):
    annual_df = df.groupby('Year_Added')['Games_Count'].sum().reset_index()
    annual_df.columns = ['Year', 'Games_Added']
    
    fig = go.Figure(data=[go.Bar(x=annual_df['Year'], y=annual_df['Games_Added'], marker_color='steelblue')])
    fig.update_layout(
        title='Games Added by Year',
        xaxis_title='Year',
        yaxis_title='Games Added',
        height=400
    )
    
    return fig

def main():
    print('Extracting data...')
    df, summary_df = get_games_data()
    
    print('Creating charts...')
    cumulative_fig = create_cumulative_chart(df)
    annual_fig = create_annual_chart(df)
    
    output_dir = r'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\statistics'
    os.makedirs(output_dir, exist_ok=True)
    
    print('Saving charts...')
    cumulative_fig.write_html(os.path.join(output_dir, 'cumulative_games.html'), include_plotlyjs='cdn')
    annual_fig.write_html(os.path.join(output_dir, 'annual_additions.html'), include_plotlyjs='cdn')
    
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
    
    print(f'Charts saved to {output_dir}')
    print(f'Total games: {summary_dict["total_games"]:,}')

if __name__ == '__main__':
    main()
