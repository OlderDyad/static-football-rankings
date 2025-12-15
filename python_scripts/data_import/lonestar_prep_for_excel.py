#!/usr/bin/env python3
"""
LoneStar Schedule Prep for Excel
=================================

Converts the raw CSV (one row per season) into Excel-ready format (one row per game).

Input:  lonestar_raw_schedules.csv (raw_schedule_text in one cell)
Output: lonestar_ready_for_excel.csv (each game as separate row)

Output format matches your screenshot:
- Column A: team_id (for reference)
- Column B: team_name (for reference)
- Column C: season (e.g., "2003")
- Column D: week (e.g., "10")
- Column E: Team 1 (with prefix like "nSan Angelo Centralv")
- Column F: Score 1
- Column G: Team 2 (with prefix like "LAmarillod")
- Column H: Score 2
- Column I: Notes (D, B, etc.)

Then you can apply your Excel formulas to clean the team names.
"""

import csv
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INPUT_FILE = "lonestar_raw_schedules.csv"
OUTPUT_FILE = "lonestar_ready_for_excel.csv"

def split_game_line(line: str, season: str):
    """
    Parse a game line like:
    "POdessa Permianv 28 LAmarillo3 21"
    OR with date: "11/20  LAmarillov 33 7 El Paso Irvin..."
    
    Note: We IGNORE any week/date info from LoneStar (unreliable).
    Week numbers are auto-generated starting at 35.
    
    Returns: (team1, score1, team2, score2, notes)
    """
    line = line.strip()
    if not line:
        return None
    
    # Remove any leading date or week number
    # Patterns: "11/20  " or "10  " or "WK 10  "
    line = re.sub(r'^\d{1,2}(/\d{1,2})?\s+', '', line)
    line = re.sub(r'^WK\s+\d{1,2}\s+', '', line)
    rest = line.strip()
    
    if not rest:
        return None
    
    # Find all digit sequences
    all_digits = list(re.finditer(r'\d+', rest))
    
    if len(all_digits) < 2:
        return None
    
    # High school football scores are typically 0-70 (1-2 digits)
    # Multi-digit sequences (3+) are likely to be misread compressed text
    
    # Strategy: Find the rightmost pair of 1-2 digit numbers as scores
    # If we have "v103", that's "v 10 3" where v=separator, 10=score, 3=junk
    
    # Split long digit sequences (3+) into smaller chunks
    split_digits = []
    for match in all_digits:
        digits = match.group()
        pos = match.start()
        
        if len(digits) >= 3:
            # Split into chunks: "103" -> ["10", "3"]
            # Try to parse as [2-digit][1-digit] or [1-digit][2-digit]
            if len(digits) == 3:
                # Could be 10,3 or 1,03 - assume 2+1
                split_digits.append((pos, digits[:2]))
                split_digits.append((pos + 2, digits[2:]))
            elif len(digits) == 4:
                # Could be 10,31 or 35,21 - assume 2+2
                split_digits.append((pos, digits[:2]))
                split_digits.append((pos + 2, digits[2:]))
            else:
                # Just take first 2 digits as score
                split_digits.append((pos, digits[:2]))
        else:
            split_digits.append((pos, digits))
    
    if len(split_digits) < 2:
        return None
    
    # Now find the last two reasonable scores (1-2 digits, value 0-70)
    score_candidates = [(pos, val) for pos, val in split_digits if 0 <= int(val) <= 99]
    
    if len(score_candidates) < 2:
        return None
    
    # NEW LOGIC: For compressed formats like "v103", we want 10 and the NEXT score
    # Not the last two digits (3, 7)
    # 
    # Strategy: Look for a pattern where we have multiple consecutive candidates
    # If we find [10, 3, ...7], take 10 and 7 (skip the middle junk digit)
    
    # Check if we have 3+ candidates with a suspicious single-digit in position 2
    if len(score_candidates) >= 3:
        # Check if candidate[1] is a single digit 0-9 (likely junk)
        # and candidate[0] and candidate[2] are reasonable scores
        _, val1 = score_candidates[0]
        _, val2 = score_candidates[1]  
        
        if len(val2) == 1 and int(val2) < 10:  # Middle value is single digit (junk)
            # Use first and third as scores, skip the middle
            score1_pos, score1 = score_candidates[0]
            score2_pos, score2 = score_candidates[2]
        else:
            # Normal case: take last two
            score1_pos, score1 = score_candidates[-2]
            score2_pos, score2 = score_candidates[-1]
    else:
        # Only 2 candidates, use them
        score1_pos, score1 = score_candidates[-2]
        score2_pos, score2 = score_candidates[-1]
    
    # Calculate where scores are in original string
    score1_len = len(score1)
    score2_len = len(score2)
    
    # Team1 is everything before score1
    team1 = rest[:score1_pos].strip()
    
    # Team2 is between score1 and score2
    team2_start = score1_pos + score1_len
    team2 = rest[team2_start:score2_pos].strip()
    
    # Notes are after score2
    notes = rest[score2_pos + score2_len:].strip()
    
    # Validate: team names should be at least 2 chars
    if len(team1) < 2 or len(team2) < 2:
        return None
    
    return (team1, score1, team2, score2, notes)

def process_schedule(raw_text: str, team_id: str, team_name: str, season: str):
    """
    Process a raw schedule text block and yield individual games.
    Auto-generates week numbers starting at 35 (late August).
    Ignores any week/date info from LoneStar (unreliable).
    """
    lines = raw_text.split('\n')
    
    # Start week numbering at 35 (late August)
    auto_week = 35
    
    for line in lines:
        # Skip header lines
        if 'Record:' in line or 'WK Team SC' in line or not line.strip():
            continue
        
        game = split_game_line(line, season)
        if game:
            team1, score1, team2, score2, notes = game
            
            yield {
                'team_id': team_id,
                'team_name': team_name,
                'season': season,
                'week': str(auto_week),
                'team1_raw': team1,
                'score1': score1,
                'team2_raw': team2,
                'score2': score2,
                'notes': notes
            }
            
            # Increment week for next game
            auto_week += 1

def main():
    logger.info("="*60)
    logger.info("LoneStar Schedule Prep")
    logger.info("="*60)
    
    total_schedules = 0
    total_games = 0
    
    output_rows = []
    
    # Read input CSV
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            team_id = row['team_id']
            team_name = row['team_name']
            season = row['season']
            raw_text = row['raw_schedule_text']
            
            total_schedules += 1
            
            # Process this schedule
            games = list(process_schedule(raw_text, team_id, team_name, season))
            total_games += len(games)
            output_rows.extend(games)
            
            if total_schedules % 100 == 0:
                logger.info(f"Processed {total_schedules} schedules, {total_games} games so far...")
    
    # Write output CSV
    logger.info(f"Writing {len(output_rows)} games to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['team_id', 'team_name', 'season', 'week', 'team1_raw', 'score1', 
                      'team2_raw', 'score2', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    
    logger.info("="*60)
    logger.info(f"COMPLETE!")
    logger.info(f"  Input:  {total_schedules} schedules")
    logger.info(f"  Output: {total_games} individual games")
    logger.info(f"  File:   {OUTPUT_FILE}")
    logger.info("="*60)
    logger.info("")
    logger.info("📄 Next steps:")
    logger.info("1. Open lonestar_ready_for_excel.csv in Excel")
    logger.info("2. Apply formulas to clean team1_raw and team2_raw columns")
    logger.info("3. Export cleaned data")
    logger.info("4. Import to HS_Scores")

if __name__ == "__main__":
    main()
