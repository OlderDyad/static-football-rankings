"""
LoneStar Football Data Parser - Version 2
Converts raw schedule data into Excel-ready format with improved parsing.

Key Improvements:
- Better compressed score detection (fixes "7Caddo Mills8 13" pattern)
- Flags JV games instead of filtering them
- Flags College/Prep games instead of filtering them
- Strips neutral site markers (@Location)
- Cleans trailing special characters
- Filters only Bye/Forfeit games
"""

import csv
import re
from pathlib import Path

# Input/Output files
INPUT_FILE = "lonestar_raw_schedules.csv"
OUTPUT_FILE = "lonestar_ready_for_excel_v2.csv"

def clean_team_name(name):
    """
    Clean team name of common formatting issues.
    - Strip neutral site markers: @Location
    - Remove trailing special characters: $, #, etc.
    """
    if not name:
        return name
    
    # Strip neutral site marker (e.g., "7Gorman @Decatur" → "7Gorman")
    name = re.sub(r'\s*@[A-Za-z\s]+$', '', name)
    
    # Remove trailing special characters (but keep the prefix character)
    name = re.sub(r'[$#*@]+$', '', name)
    
    return name.strip()

def detect_game_type(team1_raw, team2_raw):
    """
    Detect special game types for flagging.
    Returns: ('JV', 'College', 'Bye', or None), notes
    """
    combined = f"{team1_raw} {team2_raw}".lower()
    
    # Check for JV games
    if ' jv' in combined:
        return 'JV', 'JV_GAME'
    
    # Check for College/Prep games
    college_keywords = ['college', 'university', 'prep']
    if any(keyword in combined for keyword in college_keywords):
        return 'College', 'COLLEGE_GAME'
    
    # Check for Bye/Forfeit games
    if 'bye' in combined:
        return 'Bye', 'BYE_GAME'
    
    return None, ''

def split_compressed_numbers(text):
    """
    Find all digit sequences and split 3+ digit numbers into chunks.
    Example: "103" → ["10", "3"]
             "321" → ["32", "1"]
    """
    all_digits = []
    for match in re.finditer(r'\d+', text):
        num_str = match.group()
        if len(num_str) >= 3:
            # Split into chunks: first N-1 digits, then last digit
            all_digits.append(num_str[:-1])
            all_digits.append(num_str[-1])
        else:
            all_digits.append(num_str)
    return all_digits

def is_likely_junk_digit(digit_str, all_digits, index):
    """
    Determine if a digit is likely obfuscation junk.
    
    Pattern: If we have [XX, Y, ZZ] where Y is single digit 0-9
    and it's surrounded by 2-digit numbers, Y is likely junk.
    """
    if len(digit_str) != 1:
        return False
    
    # Check if single digit is 0-9 (common junk)
    if digit_str not in '0123456789':
        return False
    
    # If it's in the middle of the sequence
    if 0 < index < len(all_digits) - 1:
        prev_digit = all_digits[index - 1]
        next_digit = all_digits[index + 1]
        
        # If surrounded by larger numbers, it's likely junk
        if len(prev_digit) >= 2 and len(next_digit) >= 1:
            return True
    
    return False

def extract_scores_smart(all_digits):
    """
    Smart score extraction with junk detection.
    
    Patterns:
    1. "Amarillov103Pampad7" → [10, 3, 7] → scores: 10, 7 (skip middle junk 3)
    2. "7Caddo Mills8 13" → [7, 8, 13] → scores: 8, 13 (skip leading junk 7)
    3. Normal case: last two are scores
    """
    if len(all_digits) < 2:
        return None, None
    
    # Case: Exactly 3 digits
    if len(all_digits) == 3:
        # Check if middle digit is likely junk
        if is_likely_junk_digit(all_digits[1], all_digits, 1):
            # Use first and third as scores
            return all_digits[0], all_digits[2]
    
    # Case: 4+ digits - find the likely pair
    if len(all_digits) >= 4:
        # Look for pattern where we have junk digits
        # Often the last meaningful pair is the scores
        
        # Try to find two consecutive non-junk digits at the end
        for i in range(len(all_digits) - 1, 0, -1):
            if not is_likely_junk_digit(all_digits[i], all_digits, i):
                # Found a good score, look for its pair
                if i > 0 and not is_likely_junk_digit(all_digits[i-1], all_digits, i-1):
                    return all_digits[i-1], all_digits[i]
    
    # Default: Use last two digits as scores
    return all_digits[-2], all_digits[-1]

def split_game_line(line):
    """
    Parse a single game line into components.
    
    Returns: (team1_raw, score1, team2_raw, score2, notes)
    """
    if not line or line.strip() == '':
        return None
    
    # Remove any leading date/week patterns
    line = re.sub(r'^(\d{1,2}/\d{1,2}\s+|WK\s+\d+\s+|\d+\s+)', '', line)
    line = line.strip()
    
    if not line:
        return None
    
    # Find all digit sequences and split compressed numbers
    all_digits = split_compressed_numbers(line)
    
    if len(all_digits) < 2:
        return None
    
    # Extract scores using smart detection
    score1, score2 = extract_scores_smart(all_digits)
    
    if not score1 or not score2:
        return None
    
    # Find positions of scores in original text
    # We need to find where these scores appear to split team names
    
    # Build pattern to find the scores in text
    # Look for the score digits with possible spaces/chars around them
    score1_pattern = rf'[^\d]*({re.escape(score1)})[^\d]+'
    score2_pattern = rf'[^\d]*({re.escape(score2)})[^\d]*'
    
    # Try to split at the scores
    # Pattern: [team1][score1][team2][score2]
    
    # Find score1 position
    score1_match = None
    for match in re.finditer(r'\d+', line):
        if match.group() == score1 or match.group().endswith(score1):
            score1_match = match
            break
    
    if not score1_match:
        return None
    
    # Find score2 position (after score1)
    score2_match = None
    for match in re.finditer(r'\d+', line[score1_match.end():]):
        digit_seq = match.group()
        if digit_seq == score2 or score2 in digit_seq:
            # Adjust position relative to original string
            score2_match = match
            break
    
    if not score2_match:
        return None
    
    # Extract team names based on score positions
    team1_raw = line[:score1_match.start()].strip()
    team2_start = score1_match.end()
    team2_end = score1_match.end() + score2_match.start()
    team2_raw = line[team2_start:team2_end].strip()
    
    # Clean up team names
    team1_raw = clean_team_name(team1_raw)
    team2_raw = clean_team_name(team2_raw)
    
    # Remove digits that might have stuck to team names
    team1_raw = re.sub(r'\d+$', '', team1_raw).strip()
    team2_raw = re.sub(r'\d+$', '', team2_raw).strip()
    
    return (team1_raw, score1, team2_raw, score2, '')

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
        game_type, type_notes = detect_game_type(team1_raw, team2_raw)
        
        # Skip only Bye games (keep JV and College)
        if game_type == 'Bye':
            continue
        
        # Also skip obvious forfeit games (1-0 scores)
        if (score1 == '1' and score2 == '0') or (score1 == '0' and score2 == '1'):
            continue
        
        # Combine notes
        notes = f"{base_notes} {type_notes}".strip()
        
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
    skipped_games = 0
    
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
            if 'JV_GAME' in game['notes']:
                jv_games += 1
            if 'COLLEGE_GAME' in game['notes']:
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