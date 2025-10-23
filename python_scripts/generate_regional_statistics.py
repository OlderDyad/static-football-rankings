"""
Generate regional games coverage visualizations for McKnight's Football Rankings
This script creates charts showing game coverage by state within each region
"""

import pyodbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import os
import warnings

# Suppress pandas warning about pyodbc
warnings.filterwarnings("ignore", category=UserWarning, message='.*pandas only supports SQLAlchemy.*')

# Database connection
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;"

# Define regions and their states
REGIONS = {
    'Northeast': {
        'name': 'Northeast',
        'states': ['CT', 'DC', 'DE', 'ME', 'MA', 'NH', 'NJ', 'NY', 'PA', 'RI', 'VT'],
        'color_scheme': 'Blues'
    },
    'Southeast': {
        'name': 'Southeast', 
        'states': ['AL', 'AR', 'FL', 'GA', 'KY', 'LA', 'MD', 'MS', 'NC', 'SC', 'TN', 'VA', 'WV'],
        'color_scheme': 'Greens'
    },
    'Midwest': {
        'name': 'Midwest',
        'states': ['IL', 'IN', 'IA', 'KS', 'MI', 'MN', 'MO', 'NE', 'ND', 'OH', 'SD', 'WI'],
        'color_scheme': 'Oranges'
    },
    'Southwest': {
        'name': 'Southwest',
        'states': ['AZ', 'NM', 'OK', 'TX'],
        'color_scheme': 'Reds'
    },
    'West': {
        'name': 'West',
        'states': ['AK', 'CA', 'CO', 'HI', 'ID', 'MT', 'NV', 'OR', 'UT', 'WA', 'WY'],
        'color_scheme': 'Purples'
    },
    'Canada': {
        'name': 'Canada',
        'states': ['AB', 'BC', 'MB', 'NB', 'NS', 'QB', 'SK'],
        'color_scheme': 'RdPu'
    }
}

def get_regional_games_data(region_states):
    """Get games by season for states in a region"""
    conn = pyodbc.connect(conn_str)
    
    # Create state filter for SQL query
    state_patterns = [f"'% ({state})%'" for state in region_states]
    state_filter = " OR ".join([f"Home LIKE {pattern}" for pattern in state_patterns])
    
    query = f"""
    WITH GamesByState AS (
        SELECT 
            Season,
            CASE 
                {' '.join([f"WHEN Home LIKE '% ({state})%' THEN '{state}'" for state in region_states])}
                ELSE 'Other'
            END AS State,
            1 AS GameCount
        FROM [hs_football_database].[dbo].[HS_Scores]
        WHERE Season IS NOT NULL
            AND Season >= 1869
            AND ({state_filter})
    )
    SELECT 
        Season,
        State,
        COUNT(*) AS Games
    FROM GamesByState
    WHERE State != 'Other'
    GROUP BY Season, State
    ORDER BY Season, State
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

def get_region_summary(region_states):
    """Get summary statistics for a region"""
    conn = pyodbc.connect(conn_str)
    
    state_patterns = [f"'% ({state})%'" for state in region_states]
    state_filter = " OR ".join([f"Home LIKE {pattern}" for pattern in state_patterns])
    
    query = f"""
    SELECT 
        COUNT(*) AS Total_Games,
        MIN(Season) AS Earliest_Season,
        MAX(Season) AS Latest_Season,
        COUNT(DISTINCT Season) AS Total_Seasons,
        COUNT(DISTINCT CASE 
            {' '.join([f"WHEN Home LIKE '% ({state})%' THEN '{state}'" for state in region_states])}
        END) AS States_With_Data
    FROM [hs_football_database].[dbo].[HS_Scores]
    WHERE Season IS NOT NULL
        AND ({state_filter})
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

def create_region_chart(df, region_name, color_scheme):
    """Create line chart for a region showing games by state over time"""
    
    # Pivot data to have seasons as index and states as columns
    pivot_df = df.pivot_table(
        index='Season',
        columns='State',
        values='Games',
        fill_value=0
    )
    
    # Get color palette
    colors = getattr(px.colors.sequential, color_scheme)
    if len(colors) < len(pivot_df.columns):
        # Repeat colors if we need more
        colors = colors * (len(pivot_df.columns) // len(colors) + 1)
    
    fig = go.Figure()
    
    # Add a line for each state
    for idx, state in enumerate(sorted(pivot_df.columns)):
        fig.add_trace(go.Scatter(
            x=pivot_df.index,
            y=pivot_df[state],
            name=state,
            mode='lines',
            line=dict(width=2, color=colors[idx]),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Season: %{x}<br>' +
                          'Games: %{y:,.0f}<br>' +
                          '<extra></extra>'
        ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': f'{region_name} Region - Games by State',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        xaxis_title='Season',
        yaxis_title='Number of Games',
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12),
        legend=dict(
            title='State',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='lightgray',
            borderwidth=1
        ),
        margin=dict(r=150),
        height=600,
        xaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True,
            range=[1869, None]  # Start from 1869
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

def create_region_stacked_chart(df, region_name, color_scheme):
    """Create stacked area chart for a region"""
    
    pivot_df = df.pivot_table(
        index='Season',
        columns='State',
        values='Games',
        fill_value=0
    )
    
    colors = getattr(px.colors.sequential, color_scheme)
    if len(colors) < len(pivot_df.columns):
        colors = colors * (len(pivot_df.columns) // len(colors) + 1)
    
    fig = go.Figure()
    
    for idx, state in enumerate(sorted(pivot_df.columns)):
        fig.add_trace(go.Scatter(
            x=pivot_df.index,
            y=pivot_df[state],
            name=state,
            mode='lines',
            stackgroup='one',
            fillcolor=colors[idx],
            line=dict(width=0.5, color=colors[idx]),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Season: %{x}<br>' +
                          'Games: %{y:,.0f}<br>' +
                          '<extra></extra>'
        ))
    
    fig.update_layout(
        title={
            'text': f'{region_name} Region - Cumulative Games by State',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        xaxis_title='Season',
        yaxis_title='Number of Games (Cumulative)',
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12),
        legend=dict(
            title='State',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='lightgray',
            borderwidth=1
        ),
        margin=dict(r=150),
        height=600,
        xaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True,
            range=[1869, None]
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

def create_region_bar_chart(df, region_name, color_scheme):
    """Create bar chart showing total games by state"""
    
    # Sum up all games by state
    state_totals = df.groupby('State')['Games'].sum().sort_values(ascending=True)
    
    colors = getattr(px.colors.sequential, color_scheme)
    if len(colors) < len(state_totals):
        colors = colors * (len(state_totals) // len(colors) + 1)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=state_totals.index,
        x=state_totals.values,
        orientation='h',
        marker=dict(
            color=state_totals.values,
            colorscale=color_scheme,
            showscale=False
        ),
        hovertemplate='<b>%{y}</b><br>' +
                      'Total Games: %{x:,.0f}<br>' +
                      '<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': f'{region_name} Region - Total Games by State',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        xaxis_title='Total Games',
        yaxis_title='State',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12),
        height=max(400, len(state_totals) * 30),
        xaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True,
            tickformat=',d'
        ),
        yaxis=dict(
            showline=True,
            linecolor='black',
            mirror=True
        )
    )
    
    return fig

def save_region_data(region_key, region_info, output_dir):
    """Process and save data for a single region"""
    print(f"\nProcessing {region_info['name']}...")
    
    # Get data
    df = get_regional_games_data(region_info['states'])
    
    if df.empty:
        print(f"   No data found for {region_info['name']}")
        return None
    
    print(f"   Found {len(df)} season/state combinations")
    
    # Get summary
    summary_df = get_region_summary(region_info['states'])
    
    # Create output directory for this region
    region_dir = os.path.join(output_dir, region_key.lower())
    os.makedirs(region_dir, exist_ok=True)
    
    # Create charts
    print(f"   Creating line chart...")
    line_chart = create_region_chart(df, region_info['name'], region_info['color_scheme'])
    line_chart.write_html(
        os.path.join(region_dir, 'games_by_state.html'),
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    print(f"   Creating stacked area chart...")
    stacked_chart = create_region_stacked_chart(df, region_info['name'], region_info['color_scheme'])
    stacked_chart.write_html(
        os.path.join(region_dir, 'games_stacked.html'),
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    print(f"   Creating bar chart...")
    bar_chart = create_region_bar_chart(df, region_info['name'], region_info['color_scheme'])
    bar_chart.write_html(
        os.path.join(region_dir, 'total_by_state.html'),
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    # Save summary statistics
    summary_dict = {
        'region': region_info['name'],
        'states': region_info['states'],
        'total_games': int(summary_df['Total_Games'].iloc[0]),
        'earliest_season': int(summary_df['Earliest_Season'].iloc[0]),
        'latest_season': int(summary_df['Latest_Season'].iloc[0]),
        'total_seasons': int(summary_df['Total_Seasons'].iloc[0]),
        'states_with_data': int(summary_df['States_With_Data'].iloc[0]),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(os.path.join(region_dir, 'summary.json'), 'w') as f:
        json.dump(summary_dict, f, indent=2)
    
    print(f"   Saved charts and data for {region_info['name']}")
    
    return summary_dict

def create_all_regions_comparison():
    """Create a chart comparing all regions"""
    conn = pyodbc.connect(conn_str)
    
    all_data = []
    
    for region_key, region_info in REGIONS.items():
        state_patterns = [f"'% ({state})%'" for state in region_info['states']]
        state_filter = " OR ".join([f"Home LIKE {pattern}" for pattern in state_patterns])
        
        query = f"""
        SELECT 
            Season,
            '{region_info['name']}' AS Region,
            COUNT(*) AS Games
        FROM [hs_football_database].[dbo].[HS_Scores]
        WHERE Season IS NOT NULL
            AND ({state_filter})
        GROUP BY Season
        ORDER BY Season
        """
        
        df = pd.read_sql(query, conn)
        all_data.append(df)
    
    conn.close()
    
    # Combine all regions
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Create chart
    fig = go.Figure()
    
    color_map = {
        'Northeast': '#4472C4',
        'Southeast': '#70AD47', 
        'Midwest': '#FFC000',
        'Southwest': '#C00000',
        'West': '#7030A0',
        'Canada': '#E91E63'
    }
    
    for region in sorted(combined_df['Region'].unique()):
        region_data = combined_df[combined_df['Region'] == region]
        
        fig.add_trace(go.Scatter(
            x=region_data['Season'],
            y=region_data['Games'],
            name=region,
            mode='lines',
            line=dict(width=3, color=color_map.get(region, '#000000')),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Season: %{x}<br>' +
                          'Games: %{y:,.0f}<br>' +
                          '<extra></extra>'
        ))
    
    fig.update_layout(
        title={
            'text': 'Regional Comparison - Games by Season',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        xaxis_title='Season',
        yaxis_title='Number of Games',
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12),
        legend=dict(
            title='Region',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='right',
            x=0.99,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='lightgray',
            borderwidth=1
        ),
        height=600,
        xaxis=dict(
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            mirror=True,
            range=[1869, None]
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

def main():
    print("=" * 80)
    print("Generating Regional Games Coverage Visualizations")
    print("=" * 80)
    
    output_dir = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/docs/data/regional-statistics"
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each region
    all_summaries = {}
    for region_key, region_info in REGIONS.items():
        summary = save_region_data(region_key, region_info, output_dir)
        if summary:
            all_summaries[region_key] = summary
    
    # Create comparison chart
    print("\nCreating regional comparison chart...")
    comparison_chart = create_all_regions_comparison()
    comparison_chart.write_html(
        os.path.join(output_dir, 'regional_comparison.html'),
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    # Save master summary
    with open(os.path.join(output_dir, 'all_regions_summary.json'), 'w') as f:
        json.dump(all_summaries, f, indent=2)
    
    print("\n" + "=" * 80)
    print("Regional Statistics Generation Complete!")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    for region_key in REGIONS.keys():
        region_lower = region_key.lower()
        print(f"\n{REGIONS[region_key]['name']}:")
        print(f"   - {region_lower}/games_by_state.html")
        print(f"   - {region_lower}/games_stacked.html")
        print(f"   - {region_lower}/total_by_state.html")
        print(f"   - {region_lower}/summary.json")
    print(f"\nRegional Comparison:")
    print(f"   - regional_comparison.html")
    print(f"   - all_regions_summary.json")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("Regional Summary Statistics")
    print("=" * 80)
    for region_key, summary in all_summaries.items():
        print(f"\n{summary['region']}:")
        print(f"   Total Games: {summary['total_games']:,}")
        print(f"   Seasons: {summary['earliest_season']}-{summary['latest_season']}")
        print(f"   States with Data: {summary['states_with_data']}/{len(summary['states'])}")

if __name__ == "__main__":
    main()
