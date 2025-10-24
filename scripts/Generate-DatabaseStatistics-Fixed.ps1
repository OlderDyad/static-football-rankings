###############################################################################
# Generate-DatabaseStatistics.ps1
# Generates database statistics visualizations and updates the website
###############################################################################

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "🏈 McKnight's Football Rankings - Database Statistics Generator" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

# Configuration
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$pythonScriptDir = Join-Path $rootDir "python_scripts"
$dataOutputDir = Join-Path $rootDir "docs\data\statistics"
$pageOutputDir = Join-Path $rootDir "docs\pages\public"
$venvPath = Join-Path $rootDir ".venv\Scripts\Activate.ps1"
$htmlTemplatePath = Join-Path $PSScriptRoot "database_statistics.html"

Write-Host "`n📁 Checking directories..." -ForegroundColor Yellow

# Ensure directories exist
if (-not (Test-Path $dataOutputDir)) {
    Write-Host "Creating statistics data directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $dataOutputDir -Force | Out-Null
}

if (-not (Test-Path $pageOutputDir)) {
    Write-Host "Creating page output directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $pageOutputDir -Force | Out-Null
}

# Step 1: Activate Python virtual environment
Write-Host "`n🐍 Activating Python virtual environment..." -ForegroundColor Yellow
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Error "Virtual environment not found at: $venvPath"
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  cd $rootDir" -ForegroundColor Gray
    Write-Host "  python -m venv .venv" -ForegroundColor Gray
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "  pip install pyodbc pandas plotly" -ForegroundColor Gray
    exit 1
}

# Step 2: Check for required Python packages
Write-Host "`n📦 Checking Python dependencies..." -ForegroundColor Yellow
$requiredPackages = @("pyodbc", "pandas", "plotly")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $installed = & python -c "import $package" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "⚠️  Missing packages: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "Installing missing packages..." -ForegroundColor Yellow
    foreach ($package in $missingPackages) {
        & pip install $package
    }
}
Write-Host "✅ All dependencies satisfied" -ForegroundColor Green

# Step 3: Copy Python script to python_scripts directory
Write-Host "`n📄 Setting up Python script..." -ForegroundColor Yellow
$pythonScript = @"
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
    
    output_dir = r'$dataOutputDir'
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
"@

$pythonScriptPath = Join-Path $pythonScriptDir "generate_statistics.py"
Set-Content -Path $pythonScriptPath -Value $pythonScript -Encoding UTF8
Write-Host "✅ Python script created" -ForegroundColor Green

# Step 4: Run Python script to generate visualizations
Write-Host "`n📊 Generating statistics visualizations..." -ForegroundColor Yellow
Set-Location $pythonScriptDir
& python generate_statistics.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Visualizations generated successfully" -ForegroundColor Green
} else {
    Write-Error "Failed to generate visualizations"
    exit 1
}

# Step 5: Copy HTML page to output directory
Write-Host "`n📄 Copying HTML page to website..." -ForegroundColor Yellow
$htmlDest = Join-Path $pageOutputDir "database-statistics.html"

# Check if the HTML template file exists
if (-not (Test-Path $htmlTemplatePath)) {
    Write-Host "⚠️  WARNING: Template file not found at $htmlTemplatePath" -ForegroundColor Yellow
    Write-Host "   Expected location: $htmlTemplatePath" -ForegroundColor Yellow
    Write-Host "`n   Please ensure the database_statistics.html template file exists in the scripts folder." -ForegroundColor Yellow
    Write-Host "   The file has been created for you in the current directory." -ForegroundColor Yellow
    Write-Host "`n   ACTION REQUIRED: Move the database_statistics.html file to:" -ForegroundColor Red
    Write-Host "   $PSScriptRoot" -ForegroundColor Red
    
    # Create the HTML file in the scripts directory if it doesn't exist
    $htmlTemplateContent = Get-Content (Join-Path $PSScriptRoot ".." "database_statistics.html") -Raw -ErrorAction SilentlyContinue
    if ($htmlTemplateContent) {
        Set-Content -Path $htmlTemplatePath -Value $htmlTemplateContent -Encoding UTF8
        Write-Host "`n✅ Template file created at: $htmlTemplatePath" -ForegroundColor Green
    }
} else {
    # Template file exists, so copy it
    Copy-Item -Path $htmlTemplatePath -Destination $htmlDest -Force
    Write-Host "✅ Copied database_statistics.html to $pageOutputDir" -ForegroundColor Green
    Write-Host "   Destination: $htmlDest" -ForegroundColor Gray
}

# Step 6: Verify output files
Write-Host "`n✅ Verifying output files..." -ForegroundColor Yellow
$expectedFiles = @(
    @{Path = (Join-Path $dataOutputDir "cumulative_games.html"); Name = "Cumulative Games Chart"},
    @{Path = (Join-Path $dataOutputDir "annual_additions.html"); Name = "Annual Additions Chart"},
    @{Path = (Join-Path $dataOutputDir "statistics_summary.json"); Name = "Statistics Summary JSON"},
    @{Path = $htmlDest; Name = "Database Statistics Page"}
)

$allFilesExist = $true
foreach ($file in $expectedFiles) {
    if (Test-Path $file.Path) {
        Write-Host "  ✓ $($file.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($file.Name) - MISSING" -ForegroundColor Red
        Write-Host "    Expected at: $($file.Path)" -ForegroundColor DarkGray
        $allFilesExist = $false
    }
}

if ($allFilesExist) {
    Write-Host "`n🎉 All files generated successfully!" -ForegroundColor Green
    Write-Host "`nFiles created:" -ForegroundColor Cyan
    Write-Host "  • $dataOutputDir\cumulative_games.html" -ForegroundColor Gray
    Write-Host "  • $dataOutputDir\annual_additions.html" -ForegroundColor Gray
    Write-Host "  • $dataOutputDir\statistics_summary.json" -ForegroundColor Gray
    Write-Host "  • $htmlDest" -ForegroundColor Gray
    
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Test locally by opening:" -ForegroundColor Gray
    Write-Host "     $htmlDest" -ForegroundColor DarkGray
    Write-Host "  2. If everything looks good, commit and push to GitHub:" -ForegroundColor Gray
    Write-Host "     cd $rootDir" -ForegroundColor DarkGray
    Write-Host "     git add docs/data/statistics/* docs/pages/public/database-statistics.html" -ForegroundColor DarkGray
    Write-Host "     git commit -m 'Add database statistics page'" -ForegroundColor DarkGray
    Write-Host "     git push origin main" -ForegroundColor DarkGray
    
    Write-Host "`n  3. After pushing, the page will be available at:" -ForegroundColor Gray
    Write-Host "     https://olderdyad.github.io/static-football-rankings/pages/public/database-statistics.html" -ForegroundColor DarkGray
} else {
    Write-Error "Some files were not generated. Please check for errors above."
    Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
    Write-Host "  • Ensure the database connection string is correct" -ForegroundColor Gray
    Write-Host "  • Verify Python and required packages are installed" -ForegroundColor Gray
    Write-Host "  • Check that the database_statistics.html template exists in the scripts folder" -ForegroundColor Gray
}

Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host "Process complete!" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
