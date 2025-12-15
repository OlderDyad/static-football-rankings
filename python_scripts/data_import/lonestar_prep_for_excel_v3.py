"""
LoneStar Football Data Parser - Version 3 (CORRECTED)
Fixes the prefix/suffix digit handling for both teams.

Key insight: The pattern is consistently:
[prefix][Team1][v/chars][Score1] [Team2][suffix][Score2] [playoff_flag]

Where:
- prefix on Team1 is a single digit (game type marker) - NOT a score
- suffix on Team2 is a single digit (obfuscation) - NOT a score
- Actual scores are the last two meaningful digit sequences
"""

import csv
import re
from pathlib import Path

# Input/Output files
INPUT_FILE = "lonestar_raw_schedules.csv"
OUTPUT_FILE = "lonestar_ready_for_excel_v3.csv"

def split_game_line(line):
    """
    Parse a single game line into components.
    
    The pattern from LoneStar:
    [digit][Team1]v [score1] [Team2][digit] [score2] [playoff_flag]
    
    Examples:
    "3Dallas White 3 21" → Teams: Dallas White, opponent; Scores: 3, 21
    "7Farmersville 3 21 D" → Teams: Farmersville, opponent; Scores: 3, 21
    "3Big Spring 8 13 D" → Teams: Big Spring, opponent; Scores: 8, 13
    
    Returns: (team1_raw, score1, team2_raw, score2, notes)
    """
    if not line or line.strip() == '':
        return None
    
    # Remove any leading date/week patterns
    line = re.sub(r'^(\d{1,2}/\d{1,2}\s+|WK\s+\d+\s+|\d+\s+)', '', line)
    line = line.strip()
    
    if not line:
        return None
    
    # Remove trailing playoff flags (single capital letters at end)
    playoff_flag = ''
    playoff_match = re.search(r'\s+([A-Z])$', line)
    if playoff_match:
        playoff_flag = playoff_match.group(1)
        line = line[:playoff_match.start()].strip()
    
    # Find ALL digit sequences in the line
    all_digits = [m.group() for m in re.finditer(r'\d+', line)]
    
    if len(all_digits) < 2:
        return None
    
    # Key insight: The scores are the LAST TWO digit sequences
    # Everything before that is part of team names (including prefix/suffix junk)
    score1 = all_digits[-2]
    score2 = all_digits[-1]
    
    # Now find where these scores are in the original text
    # We work backwards from the end to find score2 first
    score2_pattern = rf'\b{re.escape(score2)}\b'
    score2_match = None
    for match in re.finditer(score2_pattern, line):
        score2_match = match  # Take the last occurrence
    
    if not score2_match:
        return None
    
    # Find score1 (should be before score2)
    score1_pattern = rf'\b{re.escape(score1)}\b'
    score1_match = None
    for match in re.finditer(score1_pattern, line[:score2_match.start()]):
        score1_match = match  # Take the last occurrence before score2
    
    if not score1_match:
        return None
    
    # Extract team names based on score positions
    # Team1: from start to just before score1
    team1_raw = line[:score1_match.start()].strip()
    
    # Team2: from after score1 to just before score2
    team2_raw = line[score1_match.end():score2_match.start()].strip()
    
    # Clean team names
    team1_raw = clean_team_name(team1_raw)
    team2_raw = clean_team_name(team2_raw)
    
    # Remove leading single digit from team1 (prefix marker)
    team1_raw = re.sub(r'^(\d)\s*', '', team1_raw).strip()
    
    # Remove trailing single digit from team2 (suffix marker)
    team2_raw = re.sub(r'\s*(\d)$', '', team2_raw).strip()
    
    # Build notes
    notes = playoff_flag if playoff_flag else ''
    
    return (team1_raw, score1, team2_raw, score2, notes)

def clean_team_name(name):
    """
    Clean team name of common formatting issues.
    """
    if not name:
        return name
    
    # Strip neutral site marker (e.g., "@Location")
    name = re.sub(r'\s*@[A-Za-z\s]+$', '', name)
    
    # Remove common separator characters (but keep prefix letter)
    name = re.sub(r'[v\s]+$', '', name)  # Remove trailing 'v' and spaces
    
    # Remove trailing special characters
    name = re.sub(r'[$#*@]+$', '', name)
    
    return name.strip()

def detect_game_type(team1_raw, team2_raw):
    """
    Detect special game types for flagging.
    Returns: game_type_flag (or empty string)
    """
    combined = f"{team1_raw} {team2_raw}".lower()
    
    # Check for JV games
    if ' jv' in combined or 'jv ' in combined:
        return 'JV'
    
    # Check for College/Prep games
    college_keywords = ['college', 'university', 'prep']
    if any(keyword in combined for keyword in college_keywords):
        return 'COLLEGE'
    
    # Check for Bye/Forfeit games
    if 'bye' in combined:
        return 'BYE'
    
    return ''

def process_schedule(raw_schedule_text):
    """
    Process a full season schedule into individual games.
    Yields one game dict per line.
    """
    lines = [l.strip() for l in raw_schedule_text.split('\n') if l.strip()]
    
    week = 35  # Start at week 35 (late August)
    
    for line in lines:
        result = split_game_line(line)
        
        if not result:
            continue
        
        team1_raw, score1, team2_raw, score2, base_notes = result
        
        # Detect game type
        game_type = detect_game_type(team1_raw, team2_raw)
        
        # Skip only Bye games
        if game_type == 'BYE':
            continue
        
        # Skip obvious forfeit games (1-0 scores)
        if (score1 == '1' and score2 == '0') or (score1 == '0' and score2 == '1'):
            continue
        
        # Combine notes
        notes_parts = [base_notes, game_type]
        notes = ' '.join([n for n in notes_parts if n]).strip()
        
        yield {
            'team1_raw': team1_raw,
            'score1': score1,
            'team2_raw': team2_raw,
            'score2': score2,
            'week': week,
            'notes': notes
        }
        
        week += 1

def main():
    """Main processing function."""
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)
    
    if not input_path.exists():
        print(f"❌ Error: {INPUT_FILE} not found!")
        print(f"   Please ensure the raw schedules CSV is in the current directory.")
        return
    
    print(f"📖 Reading {INPUT_FILE}...")
    
    # Read input CSV
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"✅ Found {len(rows)} schedule records")
    print(f"\n🔄 Processing schedules...")
    
    # Process all schedules
    output_rows = []
    total_games = 0
    jv_games = 0
    college_games = 0
    
    for row in rows:
        team_id = row['team_id']
        team_name = row['team_name']
        season = row['season']
        raw_schedule = row['raw_schedule_text']
        
        # Process this schedule
        for game in process_schedule(raw_schedule):
            output_rows.append({
                'team_id': team_id,
                'team_name': team_name,
                'season': season,
                'week': game['week'],
                'team1_raw': game['team1_raw'],
                'score1': game['score1'],
                'team2_raw': game['team2_raw'],
                'score2': game['score2'],
                'notes': game['notes']
            })
            
            total_games += 1
            
            # Count special game types
            if 'JV' in game['notes']:
                jv_games += 1
            if 'COLLEGE' in game['notes']:
                college_games += 1
    
    print(f"\n📊 Processing complete:")
    print(f"   Total games: {total_games:,}")
    print(f"   JV games (flagged): {jv_games:,}")
    print(f"   College games (flagged): {college_games:,}")
    print(f"   Regular games: {total_games - jv_games - college_games:,}")
    
    # Write output CSV
    print(f"\n💾 Writing {OUTPUT_FILE}...")
    
    fieldnames = ['team_id', 'team_name', 'season', 'week', 
                  'team1_raw', 'score1', 'team2_raw', 'score2', 'notes']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    
    print(f"✅ Successfully wrote {len(output_rows):,} games to {OUTPUT_FILE}")
    print(f"\n📋 Next steps:")
    print(f"   1. Open {OUTPUT_FILE} in Excel")
    print(f"   2. Apply your VLOOKUP formulas to clean team names")
    print(f"   3. Filter by 'notes' column to handle JV/College games separately")
    print(f"   4. Export cleaned data for SQL import")

if __name__ == '__main__':
    main()
