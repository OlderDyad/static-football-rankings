"""
Ambiguous Games Research Assistant
===================================
Interactive tool for researching and correcting ambiguous opponent names
in the HS_Scores database (e.g., "Non-Varsity Opponent", "TBD").

Author: David McKnight
Date: December 2025
"""

import pyodbc
import pandas as pd
from datetime import datetime, timedelta
import sys

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

def get_connection():
    """Create and return a database connection."""
    try:
        return pyodbc.connect(CONN_STR)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

# ============================================================================
# DATA RETRIEVAL FUNCTIONS
# ============================================================================

def get_pending_ambiguous_games(limit=10):
    """Retrieve pending ambiguous games for research."""
    query = f"""
        SELECT TOP {limit}
            Review_ID,
            Date,
            Season,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Location,
            Location2,
            Source,
            Ambiguous_Team,
            Ambiguous_Name
        FROM HS_Scores_Ambiguous_Review
        WHERE Status = 'PENDING'
        ORDER BY Date DESC
    """
    
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

def get_context_games(known_team, game_date, days_window=14):
    """
    Find other games involving the known team around the same date.
    This helps identify the likely opponent based on schedule patterns.
    """
    query = """
        SELECT 
            Date,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Source
        FROM HS_Scores
        WHERE 
            (Home = ? OR Visitor = ?)
            AND Date BETWEEN DATEADD(DAY, ?, ?) AND DATEADD(DAY, ?, ?)
            AND Date != ?
        ORDER BY Date
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (
        known_team, known_team,
        -days_window, game_date,
        days_window, game_date,
        game_date
    ))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return pd.DataFrame()
    
    columns = ['Date', 'Home', 'Visitor', 'Home_Score', 'Visitor_Score', 'Source']
    return pd.DataFrame.from_records(rows, columns=columns)

def get_location_hints(location, location2, season):
    """
    Find teams that commonly play at a given location.
    Useful for neutral site games or when location is specified.
    """
    if not location and not location2:
        return pd.DataFrame()
    
    location_pattern = location or location2 or ""
    
    query = """
        SELECT 
            Home,
            Visitor,
            COUNT(*) as Times_At_Location
        FROM HS_Scores
        WHERE 
            (Location LIKE ? OR Location2 LIKE ?)
            AND Season BETWEEN ? - 2 AND ? + 2
        GROUP BY Home, Visitor
        HAVING COUNT(*) > 1
        ORDER BY Times_At_Location DESC
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (
        f'%{location_pattern}%',
        f'%{location_pattern}%',
        season,
        season
    ))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return pd.DataFrame()
    
    columns = ['Home', 'Visitor', 'Times_At_Location']
    return pd.DataFrame.from_records(rows, columns=columns)

def get_score_pattern_matches(home_score, visitor_score, season, known_team):
    """
    Find games with identical scores involving the known team.
    Helps identify opponent when multiple sources report same game.
    """
    query = """
        SELECT 
            Date,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Source
        FROM HS_Scores
        WHERE 
            ((Home_Score = ? AND Visitor_Score = ?) OR (Home_Score = ? AND Visitor_Score = ?))
            AND Season = ?
            AND (Home = ? OR Visitor = ?)
        ORDER BY Date
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (
        home_score, visitor_score,
        visitor_score, home_score,
        season,
        known_team, known_team
    ))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return pd.DataFrame()
    
    columns = ['Date', 'Home', 'Visitor', 'Home_Score', 'Visitor_Score', 'Source']
    return pd.DataFrame.from_records(rows, columns=columns)

def get_game_details(review_id):
    """Get details for a specific ambiguous game."""
    query = """
        SELECT 
            Review_ID,
            Date,
            Season,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Location,
            Location2,
            Source,
            Ambiguous_Team,
            Ambiguous_Name
        FROM HS_Scores_Ambiguous_Review
        WHERE Review_ID = ?
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (review_id,))
    
    game = cursor.fetchone()
    conn.close()
    
    return game

# ============================================================================
# RESEARCH FUNCTIONS
# ============================================================================

def research_ambiguous_game(review_id):
    """
    Main research function that gathers all context for an ambiguous game.
    """
    game = get_game_details(review_id)
    
    if not game:
        print(f"❌ No game found with Review_ID: {review_id}")
        return None
    
    # Extract game details
    review_id, date, season, home, visitor, home_score, visitor_score, \
        location, location2, source, ambiguous_team, ambiguous_name = game
    
    # Determine which team is known
    known_team = visitor if ambiguous_team == 'HOME' else home
    ambiguous_score = home_score if ambiguous_team == 'HOME' else visitor_score
    known_score = visitor_score if ambiguous_team == 'HOME' else home_score
    
    print("\n" + "="*80)
    print(f"RESEARCHING: Review ID {review_id}")
    print("="*80)
    print(f"Date: {date}")
    print(f"Known Team: {known_team}")
    print(f"Ambiguous Name: {ambiguous_name} ({ambiguous_team})")
    print(f"Score: {home_score}-{visitor_score}")
    if home_score is not None and visitor_score is not None:
        margin = abs(home_score - visitor_score)
        winner = "Known team won" if ((ambiguous_team == 'HOME' and home_score > visitor_score) or 
                                      (ambiguous_team == 'VISITOR' and visitor_score > home_score)) \
                 else "Ambiguous team won"
        print(f"Margin: {margin} points ({winner})")
    print(f"Location: {location or location2 or 'Not specified'}")
    print(f"Source: {source}")
    print("="*80)
    
    # Gather context
    print("\n📅 CONTEXT GAMES (games within ±2 weeks):")
    print("-" * 80)
    context_games = get_context_games(known_team, date, days_window=14)
    if not context_games.empty:
        for idx, row in context_games.iterrows():
            opponent = row['Visitor'] if row['Home'] == known_team else row['Home']
            location_marker = '@' if row['Home'] != known_team else 'vs'
            print(f"  {row['Date'].strftime('%Y-%m-%d')}: {location_marker} {opponent} "
                  f"({row['Home_Score']}-{row['Visitor_Score']}) [{row['Source']}]")
    else:
        print("  No other games found for this team in the date window.")
    
    print("\n📍 LOCATION HINTS:")
    print("-" * 80)
    if location or location2:
        location_hints = get_location_hints(location, location2, season)
        if not location_hints.empty:
            print(f"  Teams that frequently play at '{location or location2}':")
            for idx, row in location_hints.head(10).iterrows():
                print(f"    {row['Home']} vs {row['Visitor']} ({row['Times_At_Location']} times)")
        else:
            print("  No frequent matchups found at this location.")
    else:
        print("  No location specified in game record.")
    
    print("\n🎯 SCORE PATTERN MATCHES:")
    print("-" * 80)
    if home_score is not None and visitor_score is not None:
        score_matches = get_score_pattern_matches(home_score, visitor_score, season, known_team)
        if not score_matches.empty:
            print(f"  Other games with score {home_score}-{visitor_score} involving {known_team}:")
            for idx, row in score_matches.iterrows():
                if row['Date'] != date:  # Don't show the same game
                    opponent = row['Visitor'] if row['Home'] == known_team else row['Home']
                    print(f"    {row['Date'].strftime('%Y-%m-%d')}: vs {opponent} [{row['Source']}]")
        else:
            print("  No games found with matching scores.")
    else:
        print("  No score information available.")
    
    print("\n" + "="*80)
    
    return {
        'review_id': review_id,
        'date': date,
        'season': season,
        'known_team': known_team,
        'ambiguous_team': ambiguous_team,
        'ambiguous_name': ambiguous_name,
        'home_score': home_score,
        'visitor_score': visitor_score,
        'context_games': context_games,
        'location_hints': get_location_hints(location, location2, season) if (location or location2) else pd.DataFrame(),
        'score_matches': get_score_pattern_matches(home_score, visitor_score, season, known_team) if (home_score and visitor_score) else pd.DataFrame()
    }

def submit_research(review_id, proposed_name, notes, confidence='MEDIUM', researcher=None):
    """
    Submit research findings to the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            EXEC sp_Update_Ambiguous_Research 
                @Review_ID = ?,
                @Proposed_Team_Name = ?,
                @Research_Notes = ?,
                @Confidence_Level = ?,
                @Researched_By = ?
        """, (review_id, proposed_name, notes, confidence, researcher))
        
        conn.commit()
        print(f"\n✅ Research submitted for Review_ID {review_id}")
        print(f"   Proposed: {proposed_name}")
        print(f"   Confidence: {confidence}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error submitting research: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ============================================================================
# INTERACTIVE SESSION
# ============================================================================

def interactive_research_session():
    """
    Run an interactive session to research pending ambiguous games.
    """
    print("\n" + "="*80)
    print("🔍 AMBIGUOUS GAMES RESEARCH ASSISTANT")
    print("="*80)
    print("\nThis tool helps you investigate and correct ambiguous opponent names")
    print("like 'Non-Varsity Opponent', 'TBD', etc.")
    
    # Get pending games
    print("\n📊 Loading pending ambiguous games...")
    pending = get_pending_ambiguous_games(limit=100)
    
    if pending.empty:
        print("\n✅ No pending ambiguous games to research!")
        return
    
    print(f"\n📋 Found {len(pending)} pending ambiguous games")
    print("\nMost recent 10:")
    print("-" * 80)
    
    display_cols = ['Review_ID', 'Date', 'Home', 'Visitor', 'Ambiguous_Name']
    for idx, row in pending.head(10).iterrows():
        ambig_marker = "⚠️ HOME" if row['Ambiguous_Team'] == 'HOME' else "⚠️ VISITOR"
        print(f"  [{row['Review_ID']:4d}] {row['Date'].strftime('%Y-%m-%d')} | "
              f"{row['Home']:35s} vs {row['Visitor']:35s} | "
              f"{ambig_marker}: {row['Ambiguous_Name']}")
    
    print("\n" + "="*80)
    print("\nCommands:")
    print("  [number]   - Research a specific Review_ID")
    print("  'list'     - Show next 10 pending games")
    print("  'stats'    - Show summary statistics")
    print("  'quit'     - Exit the program")
    print("="*80)
    
    current_offset = 10
    
    while True:
        print()
        choice = input("Enter command or Review_ID to research: ").strip()
        
        if choice.lower() in ['quit', 'q', 'exit']:
            print("\n👋 Goodbye!")
            break
        
        elif choice.lower() == 'list':
            print(f"\nNext 10 pending games (showing {current_offset+1}-{current_offset+10}):")
            print("-" * 80)
            next_batch = pending.iloc[current_offset:current_offset+10]
            if next_batch.empty:
                print("  No more pending games.")
                current_offset = 0  # Reset to beginning
            else:
                for idx, row in next_batch.iterrows():
                    ambig_marker = "⚠️ HOME" if row['Ambiguous_Team'] == 'HOME' else "⚠️ VISITOR"
                    print(f"  [{row['Review_ID']:4d}] {row['Date'].strftime('%Y-%m-%d')} | "
                          f"{row['Home']:35s} vs {row['Visitor']:35s} | "
                          f"{ambig_marker}: {row['Ambiguous_Name']}")
                current_offset += 10
        
        elif choice.lower() == 'stats':
            print("\n📊 STATISTICS")
            print("-" * 80)
            print(f"Total pending: {len(pending)}")
            print("\nBy ambiguous name:")
            stats = pending.groupby('Ambiguous_Name').size().sort_values(ascending=False)
            for name, count in stats.items():
                print(f"  {name:30s}: {count:4d} games")
            print("\nBy season:")
            season_stats = pending.groupby('Season').size().sort_values(ascending=False)
            for season, count in season_stats.head(10).items():
                print(f"  {season}: {count:4d} games")
        
        else:
            try:
                review_id = int(choice)
                
                # Research the game
                research_data = research_ambiguous_game(review_id)
                
                if research_data:
                    print("\n💡 Based on the context above, what is your proposed team name?")
                    print("   (or enter 'skip' to move to the next game)")
                    proposed = input("\nProposed Team Name: ").strip()
                    
                    if proposed.lower() not in ['skip', 's', '']:
                        notes = input("Research Notes: ").strip()
                        
                        print("\nConfidence Level:")
                        print("  HIGH   - Multiple confirming sources, no ambiguity")
                        print("  MEDIUM - Strong context clues, one confirming source")
                        print("  LOW    - Educated guess based on limited context")
                        confidence = input("Confidence (HIGH/MEDIUM/LOW) [MEDIUM]: ").strip().upper()
                        
                        if confidence not in ['HIGH', 'MEDIUM', 'LOW']:
                            confidence = 'MEDIUM'
                        
                        researcher = input("Your Name (optional): ").strip()
                        if not researcher:
                            researcher = None
                        
                        # Submit to database
                        success = submit_research(review_id, proposed, notes, confidence, researcher)
                        
                        if success:
                            # Remove from pending list
                            pending = pending[pending['Review_ID'] != review_id]
                            print(f"\n📋 {len(pending)} pending games remaining.")
                    else:
                        print("\n⏭️  Skipped.")
                        
            except ValueError:
                print("❌ Invalid command. Please enter a number, 'list', 'stats', or 'quit'.")
            except Exception as e:
                print(f"❌ Error: {e}")

# ============================================================================
# BATCH RESEARCH MODE
# ============================================================================

def batch_research_by_pattern(ambiguous_name, proposed_name, notes, confidence='MEDIUM', researcher=None):
    """
    Research all instances of a specific ambiguous name pattern at once.
    Useful when you know that all instances of "TBD" should map to the same team.
    """
    query = """
        SELECT Review_ID
        FROM HS_Scores_Ambiguous_Review
        WHERE Status = 'PENDING'
          AND Ambiguous_Name = ?
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (ambiguous_name,))
    
    review_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not review_ids:
        print(f"No pending games found with ambiguous name: {ambiguous_name}")
        return
    
    print(f"\n🔄 Processing {len(review_ids)} games with ambiguous name '{ambiguous_name}'...")
    
    success_count = 0
    for review_id in review_ids:
        if submit_research(review_id, proposed_name, notes, confidence, researcher):
            success_count += 1
    
    print(f"\n✅ Batch research complete: {success_count}/{len(review_ids)} games updated.")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the research assistant."""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--batch':
            if len(sys.argv) < 5:
                print("Usage for batch mode:")
                print("  python research_ambiguous_games.py --batch 'Ambiguous Name' 'Proposed Name' 'Notes' [CONFIDENCE] [RESEARCHER]")
                sys.exit(1)
            
            ambiguous_name = sys.argv[2]
            proposed_name = sys.argv[3]
            notes = sys.argv[4]
            confidence = sys.argv[5] if len(sys.argv) > 5 else 'MEDIUM'
            researcher = sys.argv[6] if len(sys.argv) > 6 else None
            
            batch_research_by_pattern(ambiguous_name, proposed_name, notes, confidence, researcher)
        else:
            print("Unknown argument. Usage:")
            print("  Interactive mode: python research_ambiguous_games.py")
            print("  Batch mode: python research_ambiguous_games.py --batch 'Ambiguous Name' 'Proposed Name' 'Notes'")
            sys.exit(1)
    else:
        interactive_research_session()

if __name__ == "__main__":
    main()
