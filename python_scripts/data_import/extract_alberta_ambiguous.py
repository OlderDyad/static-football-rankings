"""
Alberta Ambiguous Names - Game Extraction for Review
Purpose: Extract all games with ambiguous opponent names to Excel for detailed review
"""

import pandas as pd
import pyodbc
from datetime import datetime

# Database connection
SERVER = 'MCKNIGHTS-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
conn_str = f'DRIVER={{SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

# File paths
CSV_INPUT = r'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Alberta_Ambigious_Names.csv'
EXCEL_OUTPUT = r'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Alberta_Ambiguous_Games_Review.xlsx'

def load_ambiguous_names():
    """Load the ambiguous names from CSV"""
    print("Loading ambiguous names from CSV...")
    df = pd.read_csv(CSV_INPUT, header=None, names=['OpponentName'])
    # Clean any whitespace and BOM characters
    df['OpponentName'] = df['OpponentName'].str.strip()
    print(f"Loaded {len(df)} ambiguous opponent names")
    return df['OpponentName'].tolist()

def extract_ambiguous_games(ambiguous_names):
    """Extract all games involving ambiguous opponent names"""
    print(f"\nConnecting to database: {DATABASE}")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Create a temp table for the ambiguous names
    print("Creating temporary table for ambiguous names...")
    cursor.execute("""
        IF OBJECT_ID('tempdb..#AlbertaAmbiguousNames') IS NOT NULL
            DROP TABLE #AlbertaAmbiguousNames;
        
        CREATE TABLE #AlbertaAmbiguousNames (
            OpponentName NVARCHAR(255) PRIMARY KEY
        );
    """)
    
    # Insert ambiguous names into temp table in batches
    print("Inserting ambiguous names into temporary table...")
    insert_query = "INSERT INTO #AlbertaAmbiguousNames (OpponentName) VALUES (?)"
    cursor.executemany(insert_query, [(name,) for name in ambiguous_names])
    conn.commit()
    
    # Now query using the temp table - execute directly with cursor to maintain session
    query = """
    SELECT 
        hs.ID,
        hs.Date,
        hs.Season,
        hs.Home,
        hs.Visitor,
        hs.Home_Score,
        hs.Visitor_Score,
        hs.Margin,
        hs.Location,
        hs.Source,
        CASE 
            WHEN EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Home)
             AND EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Visitor)
                THEN 'Both Ambiguous'
            WHEN EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Home)
                THEN 'Home Ambiguous'
            WHEN EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Visitor)
                THEN 'Visitor Ambiguous'
            ELSE 'Unknown'
        END AS AmbiguousField,
        CASE 
            WHEN EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Home)
                THEN hs.Home
            WHEN EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Visitor)
                THEN hs.Visitor
            ELSE NULL
        END AS AmbiguousName
    FROM HS_Scores hs
    WHERE EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Home)
       OR EXISTS (SELECT 1 FROM #AlbertaAmbiguousNames WHERE OpponentName = hs.Visitor)
    ORDER BY hs.Season DESC, hs.Date DESC, hs.Home
    """
    
    print("Executing query to extract ambiguous games...")
    cursor.execute(query)
    
    # Fetch results and convert to DataFrame manually
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    df = pd.DataFrame.from_records(rows, columns=columns)
    
    # Clean up temp table
    cursor.execute("DROP TABLE #AlbertaAmbiguousNames")
    conn.commit()
    
    conn.close()
    
    print(f"Found {len(df)} games with ambiguous opponent names")
    return df

def create_summary_stats(df, ambiguous_names):
    """Create summary statistics for the review"""
    stats = []
    
    # Games by season
    season_summary = df.groupby('Season').agg({
        'ID': 'count',
        'Home': 'nunique',
        'Visitor': 'nunique'
    }).reset_index()
    season_summary.columns = ['Season', 'GameCount', 'UniqueHomeTeams', 'UniqueVisitors']
    
    # Games by ambiguous name
    ambiguous_summary = df.groupby('AmbiguousName').size().reset_index(name='OccurrenceCount')
    ambiguous_summary = ambiguous_summary.sort_values('OccurrenceCount', ascending=False)
    
    # Games by import source
    source_summary = df.groupby('Source').size().reset_index(name='GameCount')
    source_summary = source_summary.sort_values('GameCount', ascending=False)
    
    # Overall statistics
    overall_stats = pd.DataFrame({
        'Metric': [
            'Total Ambiguous Games',
            'Unique Ambiguous Names Used',
            'Seasons Affected',
            'Date Range',
            'Most Common Ambiguous Name',
            'Most Common Import Source'
        ],
        'Value': [
            len(df),
            df['AmbiguousName'].nunique(),
            df['Season'].nunique(),
            f"{df['Season'].min()} - {df['Season'].max()}",
            ambiguous_summary.iloc[0]['AmbiguousName'] if len(ambiguous_summary) > 0 else 'N/A',
            source_summary.iloc[0]['Source'] if len(source_summary) > 0 else 'N/A'
        ]
    })
    
    return {
        'overall': overall_stats,
        'by_season': season_summary,
        'by_name': ambiguous_summary,
        'by_source': source_summary
    }

def export_to_excel(df, stats):
    """Export games and statistics to Excel with multiple sheets"""
    print(f"\nExporting to Excel: {EXCEL_OUTPUT}")
    
    with pd.ExcelWriter(EXCEL_OUTPUT, engine='openpyxl') as writer:
        # Main games sheet
        df.to_excel(writer, sheet_name='Ambiguous Games', index=False)
        
        # Statistics sheets
        stats['overall'].to_excel(writer, sheet_name='Overall Stats', index=False)
        stats['by_season'].to_excel(writer, sheet_name='By Season', index=False)
        stats['by_name'].to_excel(writer, sheet_name='By Ambiguous Name', index=False)
        stats['by_source'].to_excel(writer, sheet_name='By Import Source', index=False)
        
        # Format the main sheet
        worksheet = writer.sheets['Ambiguous Games']
        
        # Set column widths
        column_widths = {
            'A': 38,  # ID (GUID)
            'B': 12,  # Date
            'C': 8,   # Season
            'D': 35,  # Home
            'E': 35,  # Visitor
            'F': 10,  # Home_Score
            'G': 12,  # Visitor_Score
            'H': 10,  # Margin
            'I': 20,  # Location
            'J': 20,  # Source
            'K': 18,  # AmbiguousField
            'L': 35   # AmbiguousName
        }
        
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
        
        # Freeze header row
        worksheet.freeze_panes = 'A2'
    
    print(f"Excel file created successfully!")
    print(f"\nFile location: {EXCEL_OUTPUT}")

def main():
    """Main execution function"""
    print("="*70)
    print("Alberta Ambiguous Names - Game Extraction")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Load ambiguous names
        ambiguous_names = load_ambiguous_names()
        
        # Extract games
        games_df = extract_ambiguous_games(ambiguous_names)
        
        if len(games_df) == 0:
            print("\nNo games found with ambiguous opponent names!")
            return
        
        # Create statistics
        print("\nGenerating summary statistics...")
        stats = create_summary_stats(games_df, ambiguous_names)
        
        # Display quick summary
        print("\n" + "="*70)
        print("QUICK SUMMARY")
        print("="*70)
        print(stats['overall'].to_string(index=False))
        
        print("\nTop 10 Most Common Ambiguous Names:")
        print(stats['by_name'].head(10).to_string(index=False))
        
        # Export to Excel
        export_to_excel(games_df, stats)
        
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Open the Excel file and review the 'Ambiguous Games' sheet")
        print("2. Check the statistics sheets to understand the scope")
        print("3. Confirm these games should be deleted")
        print("4. Run the SQL deletion script: Alberta_Ambiguous_Review.sql")
        print("="*70)
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()