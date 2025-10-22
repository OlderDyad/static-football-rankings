import re
import os
import pandas as pd
from datetime import datetime, timedelta

def extract_date_from_filename(filename):
    """Extract date from filename like The_Post_Standard_2003_10_19_41.txt"""
    match = re.search(r"(\d{4})_(\d{2})_(\d{2})", filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            return datetime(year, month, day), year
        except ValueError:
            print(f"⚠️ Invalid date in filename: {filename}")
            return None, None
    return None, None

def calculate_game_date(newspaper_date, game_index, games_in_section):
    """
    Calculate the date for a specific game based on its position in the team's schedule.
    
    Args:
        newspaper_date: Publication date of the newspaper
        game_index: Index of this game in the team's list (0-based, where 0 is the most recent)
        games_in_section: Total number of games in this team's section
    
    Returns:
        datetime: The calculated game date
    """
    # The most recent game is typically played the day before the newspaper (or Saturday)
    most_recent_game_date = newspaper_date - timedelta(days=1)
    
    # If the most recent date is a future date (has time component), it's a scheduled game
    if "p.m." in str(game_index) or "a.m." in str(game_index):
        return most_recent_game_date
    
    # Count backwards 7 days for each game before the most recent
    weeks_back = games_in_section - 1 - game_index  # Most recent game has index (games_in_section-1)
    return most_recent_game_date - timedelta(days=7 * weeks_back)

def parse_football_scores(text, newspaper_date, season, newspaper_name):
    """
    Parse football scores from OCR text with accurate date calculations.
    
    Args:
        text: The OCR text
        newspaper_date: Publication date of the newspaper (datetime)
        season: Season year
        newspaper_name: Name of the newspaper
    
    Returns:
        list: Game records for database import
    """
    lines = text.strip().split('\n')
    all_games = []
    
    current_team = None
    current_record = None
    team_games = []
    is_at_opponent = False
    opponent = None
    
    # Process lines one by one
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        if not line:
            continue
        
        # Check for team header: Team Name (W-L)
        team_match = re.match(r"(.*?)\s*\(([\d]-[\d])\)", line)
        if team_match:
            # If we were processing a team, handle their games
            if current_team and team_games:
                # Calculate dates and add all games to the main list
                for idx, game in enumerate(team_games):
                    # Skip games with no result (future games)
                    if not game.get('result'):
                        continue
                        
                    game_date = calculate_game_date(newspaper_date, idx, len(team_games))
                    date_str = game_date.strftime("%Y-%m-%d")
                    
                    # Set up home/away teams and scores
                    if game['location'] == 'away':
                        home_team = game['opponent']
                        home_score = game['opp_score']
                        visitor_team = current_team
                        visitor_score = game['team_score']
                    else:
                        home_team = current_team
                        home_score = game['team_score']
                        visitor_team = game['opponent']
                        visitor_score = game['opp_score']
                        
                    game_record = [
                        home_team,
                        home_score,
                        visitor_team,
                        visitor_score,
                        False,  # forfeit
                        date_str,
                        season,
                        newspaper_name,
                        newspaper_name
                    ]
                    
                    all_games.append(game_record)
            
            # Start new team
            current_team = team_match.group(1).strip()
            current_record = team_match.group(2)
            team_games = []
            is_at_opponent = False
            opponent = None
            continue
        
        # Check for away game indicator
        if line.startswith('at '):
            is_at_opponent = True
            opponent = line[3:].strip()
            continue
        
        # Check for home game (opponent line without "at")
        if current_team and not is_at_opponent and not re.match(r'^[WLT],', line) and not re.match(r'\d{1,2}/\d{1,2}', line):
            is_at_opponent = False
            opponent = line
            continue
        
        # Check for game result: W/L/T, Score-Score
        result_match = re.match(r'([WLT]),\s*([\d]+)-([\d]+)', line)
        if result_match and opponent:
            result = result_match.group(1)
            score1 = int(result_match.group(2))
            score2 = int(result_match.group(3))
            
            # Determine which team won based on the result code
            if result == 'W':
                team_score = max(score1, score2)
                opp_score = min(score1, score2)
            elif result == 'L':
                team_score = min(score1, score2)
                opp_score = max(score1, score2)
            else:  # Tie
                team_score = score1
                opp_score = score2
            
            # Add to this team's games
            team_games.append({
                'opponent': opponent,
                'location': 'away' if is_at_opponent else 'home',
                'result': result,
                'team_score': team_score,
                'opp_score': opp_score
            })
            
            # Reset for next game
            is_at_opponent = False
            opponent = None
            continue
        
        # Check for future game (no result yet)
        future_match = re.match(r'\d{1,2}/\d{1,2}', line)
        if future_match and opponent:
            # Add as a future game (no scores)
            team_games.append({
                'opponent': opponent,
                'location': 'away' if is_at_opponent else 'home',
                'result': None,  # No result yet
                'team_score': None,
                'opp_score': None,
                'future_date': line  # Keep the date info
            })
            
            # Reset for next game
            is_at_opponent = False
            opponent = None
            continue
    
    # Process any remaining games from the last team
    if current_team and team_games:
        for idx, game in enumerate(team_games):
            # Skip games with no result (future games)
            if not game.get('result'):
                continue
                
            game_date = calculate_game_date(newspaper_date, idx, len(team_games))
            date_str = game_date.strftime("%Y-%m-%d")
            
            # Set up home/away teams and scores
            if game['location'] == 'away':
                home_team = game['opponent']
                home_score = game['opp_score']
                visitor_team = current_team
                visitor_score = game['team_score']
            else:
                home_team = current_team
                home_score = game['team_score']
                visitor_team = game['opponent']
                visitor_score = game['opp_score']
                
            game_record = [
                home_team,
                home_score,
                visitor_team,
                visitor_score,
                False,  # forfeit
                date_str,
                season,
                newspaper_name,
                newspaper_name
            ]
            
            all_games.append(game_record)
    
    return all_games

def process_ocr_file(input_file, output_csv=None):
    """
    Process a newspaper OCR file with football scores and generate CSV for database import.
    
    Args:
        input_file: Path to the OCR text file
        output_csv: Path to save the output CSV
    """
    # Set default output path if not provided
    if not output_csv:
        output_csv = os.path.join(os.path.dirname(input_file), "cleaned_scores.csv")
    
    # Extract date from filename
    filename = os.path.basename(input_file)
    newspaper_date, season = extract_date_from_filename(filename)
    
    # Extract newspaper name from filename
    newspaper_parts = []
    for part in filename.split('_'):
        if re.match(r'\d{4}', part):
            break
        newspaper_parts.append(part)
    
    newspaper_name = " ".join(newspaper_parts)
    
    print(f"Processing scores from: {filename}")
    print(f"Newspaper date: {newspaper_date.strftime('%Y-%m-%d')}")
    print(f"Newspaper: {newspaper_name}")
    
    # Read the input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Parse the data
    records = parse_football_scores(text, newspaper_date, season, newspaper_name)
    
    # Remove potential duplicate games (same teams, scores, and date)
    unique_records = []
    seen = set()
    
    for record in records:
        # Create a key that identifies a unique game
        game_key = f"{record[0]}-{record[1]}-{record[2]}-{record[3]}-{record[5]}"
        
        if game_key not in seen:
            seen.add(game_key)
            unique_records.append(record)
    
    # Save to CSV
    if unique_records:
        df = pd.DataFrame(
            unique_records, 
            columns=["Home", "Home_Score", "Visitor", "Visitor_Score", "Forfeit", 
                    "Date", "Season", "Source", "Newspaper_Region"]
        )
        df.to_csv(output_csv, index=False)
        print(f"✅ Extracted {len(unique_records)} unique games and saved to {output_csv}")
        
        # Print a sample of extracted games
        print("\nSample of extracted games:")
        for i, record in enumerate(unique_records[:5]):
            print(f"{i+1}. [{record[5]}] {record[0]} {record[1]} vs {record[2]} {record[3]}")
        
        if len(unique_records) > 5:
            print(f"... and {len(unique_records) - 5} more games")
    else:
        print("❌ No games could be extracted from the input file.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_csv = sys.argv[2] if len(sys.argv) > 2 else None
        process_ocr_file(input_file, output_csv)
    else:
        print("Usage: python advanced_football_parser.py input_file.txt [output_file.csv]")
        print("\nThis script parses football scores from OCR text with accurate date calculations.")