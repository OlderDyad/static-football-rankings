#!/usr/bin/env python3
"""
LoneStar Game Parser - Mimics Excel Workflow Logic

This parser handles the obfuscated format like:
"PPort Arthur Jeffersonv33 7La Porte3 21"

Breaking it down:
- Random prefix: P, n, L, T, m, x, #, *, etc.
- Team name: "Port Arthur Jefferson"
- Separator: v, f, d, y (often 'v')
- Score: 33
- Pattern repeats for second team
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

def clean_team_name(raw_text: str) -> str:
    """
    Clean team name by removing prefix junk characters
    
    Excel formula: =TRIM(SUBSTITUTE(IFERROR(MID(C2,2,LEN(C2)-2),""),CHAR(160),CHAR(32)))
    
    This removes:
    - Leading single letters (P, n, L, T, m, x, #, *)
    - Non-breaking spaces (CHAR(160))
    - Trailing junk before score
    """
    if not raw_text:
        return ""
    
    # Remove leading single letter prefixes
    text = re.sub(r'^[a-zA-Z#*]{1,2}', '', raw_text)
    
    # Remove non-breaking spaces
    text = text.replace('\xa0', ' ')
    
    # Remove trailing single letters and digits
    text = re.sub(r'[a-z]\d*$', '', text)
    
    return text.strip()

def parse_game_cell(cell_text: str, team_id: int) -> Optional[Tuple[str, int, str, int, str]]:
    """
    Parse a game cell that looks like:
    "PPort Arthur Jeffersonv33 7La Porte3 21"
    
    Returns: (team1_name, team1_score, team2_name, team2_score, home_away)
    """
    if not cell_text or len(cell_text) < 10:
        return None
    
    try:
        # Split on spaces to get potential segments
        parts = cell_text.split()
        
        if len(parts) < 4:
            return None
        
        # Find all sequences of digits (scores)
        all_digits = re.findall(r'\d+', cell_text)
        
        if len(all_digits) < 2:
            return None
        
        # Last two digit sequences are usually the scores
        score1_str = all_digits[-2]
        score2_str = all_digits[-1]
        score1 = int(score1_str)
        score2 = int(score2_str)
        
        # Find positions of scores in original text
        score1_pos = cell_text.rfind(score1_str, 0, cell_text.rfind(score2_str))
        score2_pos = cell_text.rfind(score2_str)
        
        # Extract team names before each score
        # Team 1 is from start to first score
        team1_raw = cell_text[:score1_pos]
        # Team 2 is between scores
        team2_raw = cell_text[score1_pos+len(score1_str):score2_pos]
        
        # Clean team names
        team1 = clean_team_name(team1_raw)
        team2 = clean_team_name(team2_raw)
        
        if not team1 or not team2:
            return None
        
        # Determine home/away
        # '@' in first team indicates away game
        home_away = "Home"
        if '@' in team1_raw:
            home_away = "Away"
            team1 = team1.lstrip('@').strip()
        
        return (team1, score1, team2, score2, home_away)
        
    except Exception as e:
        logger.debug(f"Error parsing cell '{cell_text[:50]}...': {e}")
        return None

def parse_lonestar_schedule_text(page_text: str, team_id: int, season: int, 
                                 batch_id: int) -> List[Dict]:
    """
    Parse the raw text from a LoneStar schedule page
    
    The text will look like:
    "2003 Schedule
     Record: 6-5-0
     WK Team SC Team SC
     PPort Arthur Jeffersonv33 7La Porte3 21
     PPort Arthur Jeffersonv32 *Leed 7
     ..."
    """
    games = []
    
    # Split into lines
    lines = page_text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip headers and empty lines
        if not line or len(line) < 10:
            continue
        if 'Schedule' in line or 'Record:' in line or line == 'WK Team SC Team SC':
            continue
        
        # Try to parse this line as a game
        result = parse_game_cell(line, team_id)
        
        if result:
            team1, score1, team2, score2, home_away = result
            
            # Create game dictionary
            game = {
                'batch_id': batch_id,
                'team_id': team_id,
                'season': season,
                'week': "",  # Not reliably extractable
                'game_date': "",  # Not in this format
                'opponent_name_raw': team2 if home_away == "Home" else team1,
                'opponent_url': "",
                'opponent_team_id': None,
                'home_away': home_away,
                'team_score': score1 if home_away == "Home" else score2,
                'opponent_score': score2 if home_away == "Home" else score1,
                'result_text': line[:100]
            }
            
            games.append(game)
    
    return games


# Test with your samples
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    test_cases = [
        "PPort Arthur Jeffersonv33 7La Porte3 21",
        "PPort Arthur Jeffersonv32 *Leed 7",
        "PPort Arthur Jeffersonv27 PVidorv 9 D",
        "mDickinsonv20 PPort Arthur Jeffersonf 6 A",
        " 3Pampav31LAmarillov17",
        "POdessa Permianv28LAmarillov21",
    ]
    
    print("Testing LoneStar Parser:\n")
    for test in test_cases:
        result = parse_game_cell(test, 261)
        if result:
            team1, s1, team2, s2, ha = result
            print(f"✓ {test}")
            print(f"  → {team1} ({s1}) vs {team2} ({s2}) [{ha}]\n")
        else:
            print(f"✗ Failed: {test}\n")