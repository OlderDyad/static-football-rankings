import cv2
import numpy as np
import os
import subprocess
import pandas as pd
import re
from datetime import datetime, timedelta

def preprocess_image(input_path, output_path):
    """Preprocess the image to improve OCR quality"""
    # Load image
    img = cv2.imread(input_path)
    if img is None:
        print(f"Error: Could not load image {input_path}")
        return False
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to get black text on white background
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # Reduce noise
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    
    # Improve contrast
    alpha = 1.5  # Contrast control
    beta = 10    # Brightness control
    enhanced = cv2.convertScaleAbs(denoised, alpha=alpha, beta=beta)
    
    # Save the preprocessed image
    cv2.imwrite(output_path, enhanced)
    print(f"Preprocessed image saved to {output_path}")
    return True

def run_tesseract(input_image, output_prefix):
    """Run Tesseract OCR with optimized settings for sports scores"""
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    config_file = "sports.config"
    
    # Create config file if it doesn't exist
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            f.write("preserve_interword_spaces 1\n")
            f.write("tessedit_char_whitelist 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ(),-. \n")
            f.write("textord_tabfind_find_tables 1\n")
    
    # Build command
    cmd = [
        tesseract_path,
        input_image,
        output_prefix,
        "-c", "preserve_interword_spaces=1",
        "--psm", "6",
        "--oem", "1"
    ]
    
    # Add output format (txt instead of tsv for better compatibility)
    cmd.append("txt")
    
    # Run Tesseract
    try:
        subprocess.run(cmd, check=True)
        print(f"OCR completed. Output saved to {output_prefix}.txt")
        return f"{output_prefix}.txt"
    except subprocess.CalledProcessError as e:
        print(f"Error running Tesseract: {e}")
        return None

def extract_date_from_filename(filename):
    """Extract date from filename like The_Post_Standard_2003_10_19_41.jpg"""
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

def parse_football_scores(text, newspaper_date, season, newspaper_name):
    """Parse football scores from OCR text with date calculations"""
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
            # Process previous team's games
            if current_team and team_games:
                # Calculate dates and add games
                for idx, game in enumerate(team_games):
                    if not game.get('result'):
                        continue
                        
                    game_date = newspaper_date - timedelta(days=(len(team_games) - 1 - idx) * 7 + 1)
                    date_str = game_date.strftime("%Y-%m-%d")
                    
                    # Set home/away teams and scores
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
            
            # Determine scores based on result
            if result == 'W':
                team_score = max(score1, score2)
                opp_score = min(score1, score2)
            elif result == 'L':
                team_score = min(score1, score2)
                opp_score = max(score1, score2)
            else:  # Tie
                team_score = score1
                opp_score = score2
            
            # Add to team's games
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
            # Skip future games
            is_at_opponent = False
            opponent = None
            continue
    
    # Process any remaining games from the last team
    if current_team and team_games:
        for idx, game in enumerate(team_games):
            if not game.get('result'):
                continue
                
            game_date = newspaper_date - timedelta(days=(len(team_games) - 1 - idx) * 7 + 1)
            date_str = game_date.strftime("%Y-%m-%d")
            
            # Set home/away teams and scores
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

def process_newspaper_image(input_file, output_csv=None):
    """Process a newspaper image with sports scores and output to CSV"""
    # Extract date from filename
    filename = os.path.basename(input_file)
    newspaper_date, season = extract_date_from_filename(filename)
    
    if not newspaper_date:
        print("Error: Could not extract date from filename")
        return
    
    # Extract newspaper name
    newspaper_parts = []
    for part in filename.split('_'):
        if re.match(r'\d{4}', part):
            break
        newspaper_parts.append(part)
    
    newspaper_name = " ".join(newspaper_parts)
    
    print(f"Processing image: {filename}")
    print(f"Newspaper date: {newspaper_date.strftime('%Y-%m-%d')}")
    print(f"Newspaper: {newspaper_name}")
    
    # Set default output CSV path
    if not output_csv:
        output_csv = os.path.join(os.path.dirname(input_file), "cleaned_scores.csv")
    
    # Preprocess the image
    preproc_path = os.path.join(os.path.dirname(input_file), f"{os.path.splitext(filename)[0]}_preprocessed.jpg")
    if not preprocess_image(input_file, preproc_path):
        return
    
    # Run OCR
    ocr_output = run_tesseract(preproc_path, os.path.splitext(preproc_path)[0])
    if not ocr_output or not os.path.exists(ocr_output):
        print("Error: OCR processing failed")
        return
    
    # Read OCR output
    with open(ocr_output, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Parse football scores
    games = parse_football_scores(text, newspaper_date, season, newspaper_name)
    
    # Remove duplicates
    unique_games = []
    seen = set()
    
    for game in games:
        game_key = f"{game[0]}-{game[1]}-{game[2]}-{game[3]}-{game[5]}"
        if game_key not in seen:
            seen.add(game_key)
            unique_games.append(game)
    
    # Save to CSV
    if unique_games:
        df = pd.DataFrame(
            unique_games, 
            columns=["Home", "Home_Score", "Visitor", "Visitor_Score", "Forfeit", 
                    "Date", "Season", "Source", "Newspaper_Region"]
        )
        df.to_csv(output_csv, index=False)
        print(f"✅ Extracted {len(unique_games)} unique games and saved to {output_csv}")
        
        # Print a sample of extracted games
        print("\nSample of extracted games:")
        for i, game in enumerate(unique_games[:5]):
            print(f"{i+1}. [{game[5]}] {game[0]} {game[1]} vs {game[2]} {game[3]}")
        
        if len(unique_games) > 5:
            print(f"... and {len(unique_games) - 5} more games")
    else:
        print("❌ No games could be extracted")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_csv = sys.argv[2] if len(sys.argv) > 2 else None
        process_newspaper_image(input_file, output_csv)
    else:
        print("Usage: python process_newspaper.py input_image.jpg [output_csv.csv]")