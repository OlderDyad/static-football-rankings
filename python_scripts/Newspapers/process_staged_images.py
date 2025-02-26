import cv2
import pytesseract
import os
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import csv

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class OCRQualityMetrics:
    def __init__(self):
        self.uncertain_chars = 0
        self.bad_sections = 0
        self.questionable_scores = 0
        self.unrecognized_teams = 0
        self.total_lines = 0
        
    def get_quality_score(self):
        # Calculate a composite quality score (0-100, higher is better)
        total_issues = (
            self.uncertain_chars
            + (self.bad_sections * 5)  # Weight section issues more heavily
            + (self.questionable_scores * 3)
            + (self.unrecognized_teams * 2)
        )
        # Simple linear scaling, adjust as needed
        score = max(0, 100 - (total_issues * 100 / (self.total_lines + 1)))
        return round(score, 2)

class ScanQualityMetrics:
    def __init__(self):
        self.dark_regions = 0
        self.blurred_regions = 0
        self.skew_angle = 0.0
        self.contrast_score = 0.0
        
    def analyze_image_quality(self, image):
        """Analyze image quality metrics."""
        # Calculate contrast score
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        self.contrast_score = cv2.meanStdDev(gray)[1][0][0]
        
        # Detect skew
        coords = np.column_stack(np.where(gray > 0))
        angle = cv2.minAreaRect(coords)[-1]
        self.skew_angle = angle if angle < 45 else 90 - angle
        
        # Count dark regions
        dark_thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)[1]
        self.dark_regions = cv2.countNonZero(dark_thresh)
        
        return self.get_quality_summary()
        
    def get_quality_summary(self):
        return {
            'contrast': 'LOW' if self.contrast_score < 30 else 'MEDIUM' if self.contrast_score < 60 else 'HIGH',
            'skew': 'HIGH' if abs(self.skew_angle) > 5 else 'MEDIUM' if abs(self.skew_angle) > 2 else 'LOW',
            'readability': 'LOW' if self.dark_regions > 1000 else 'MEDIUM' if self.dark_regions > 500 else 'HIGH'
        }

class ScoreValidator:
    def __init__(self):
        self.verification_needed = []
        self.corrections_made = []
        
    def log_correction(self, original: str, corrected: str, reason: str):
        self.corrections_made.append({
            'original': original,
            'corrected': corrected,
            'reason': reason
        })
    
    def log_verification(self, line: str, reason: str):
        self.verification_needed.append({
            'line': line,
            'reason': reason
        })

class ProblemPatterns:
    def __init__(self):
        self.score_patterns = {
            r'Ti\b': '20',     # Ti at word boundary
            r'3%': '35',       # Percentage sign
            r'O': '0',         # Letter O to zero
            r'l(?=\d)': '1'    # lowercase L before digit
        }
        
        self.team_patterns = {
            r'0lean': 'Olean',
            r'Gr0nd': 'Grand',
            r'(?<!\w)Ti(?!\w)': '20'  # Standalone Ti
        }
        
        self.section_patterns = {
            r'Divisi0n': 'Division',
            r'Merverd Cap': 'Harvard Cup'
        }
    
    def apply_fixes(self, text: str) -> Tuple[str, List[Dict]]:
        fixes_made = []
        fixed_text = text
        
        # Apply all pattern types
        for pattern_type, patterns in [
            ('score', self.score_patterns),
            ('team', self.team_patterns),
            ('section', self.section_patterns)
        ]:
            for pattern, replacement in patterns.items():
                if re.search(pattern, fixed_text):
                    original = fixed_text
                    fixed_text = re.sub(pattern, replacement, fixed_text)
                    if original != fixed_text:
                        fixes_made.append({
                            'type': pattern_type,
                            'original': pattern,
                            'replacement': replacement
                        })
        
        return fixed_text, fixes_made

def fix_division_headers(text: str, validator: ScoreValidator, metrics: OCRQualityMetrics) -> str:
    """Fix common division header misreadings."""
    header_fixes = {
        'Division 10': 'Division II',
        'Division Il': 'Division II',
        'Division Vil': 'Division VIII',
        'Division V1': 'Division VI',
        'Division 1V': 'Division IV',
        'Division FV': 'Division IV',
        '0ivisi0n': 'Division',
        'Nen-league': 'Non-league',
        'Inter-division': 'Interdivision',
        'Interdivisi0n': 'Interdivision',
        'Harvard Cup': 'Harvard Cup',
        'Merverd Cap': 'Harvard Cup',
        'Msgr. Martin': 'Msgr. Martin Assn.',
        'Maer. Martin Assn.': 'Msgr. Martin Assn.'
    }
    
    fixed_text = text
    for wrong, right in header_fixes.items():
        if wrong.lower() in fixed_text.lower():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            original = fixed_text
            fixed_text = pattern.sub(right, fixed_text)
            if original != fixed_text:
                validator.log_correction(original, fixed_text, f"Header fix: {wrong} -> {right}")

    # Count bad sections AFTER fixes
    known_sections = ['division', 'league', 'cup', 'interdivision', 'harvard', 'msgr', 'non-league']
    for line in fixed_text.split('\n'):
        if any(x in line.lower() for x in ['division', 'league', 'cup', 'interdivision', 'harvard', 'msgr', 'non-league']):
            if not any(x in line.lower() for x in known_sections):
                metrics.bad_sections += 1

    return fixed_text

def fix_common_ocr_errors(text: str, validator: ScoreValidator, metrics: OCRQualityMetrics) -> str:
    """Fix predictable OCR errors with logging."""
    number_fixes = {
        '@': '0',
        'O': '0',
        'o': '0',
        '!': '1',
        'l': '1',
        'Z': '2',
        'B': '8',
        '&': '8',
        '%': '5'
    }

    char_fixes = {
        '|': '',
        '»': '',
        'vv': 'w',
        'rn': 'm',
        'ii': 'll',
        # ... [rest of your existing char_fixes]
    }

    fixed_text = text

    def replace_in_numbers(match):
        text_part = match.group(0)
        for wrong, right in number_fixes.items():
            text_part = text_part.replace(wrong, right)
        return text_part

    fixed_text = re.sub(r'\d+', replace_in_numbers, fixed_text)

    for wrong, right in char_fixes.items():
        if wrong in fixed_text:
            original = fixed_text
            fixed_text = fixed_text.replace(wrong, right)
            if original != fixed_text:
                validator.log_correction(original, fixed_text, f"Character fix: {wrong} → {right}")

    metrics.uncertain_chars += fixed_text.count('?')
    metrics.uncertain_chars += fixed_text.count('$')

    return fixed_text

def validate_score(score: str, context: str, validator: ScoreValidator, metrics: OCRQualityMetrics) -> Tuple[bool, Optional[int]]:
    """Validate scores with detailed logging."""
    try:
        score_num = int(score)
        
        if not (0 <= score_num <= 99):
            validator.log_verification(context, f"Score out of range: {score}")
            metrics.questionable_scores += 1
            return False, None

        if score_num > 70:
            validator.log_verification(context, f"Unusually high score: {score}")
            metrics.questionable_scores += 1
            return False, None
        
        return True, score_num

    except ValueError:
        validator.log_verification(context, f"Invalid score format: {score}")
        metrics.questionable_scores += 1
        return False, None

def extract_game_lines(text: str, validator: ScoreValidator, metrics: OCRQualityMetrics) -> List[Dict[str, str]]:
    """Extract and validate game scores with section tracking."""
    games = []
    current_section = "Unknown"

    for line in text.split('\n'):
        metrics.total_lines += 1
        line = line.strip()
        if not line:
            continue

        if any(x in line.lower() for x in ['division', 'league', 'cup', 'interdivision', 'harvard', 'msgr', 'non-league']):
            current_section = line
            continue

        score_pattern = r'(.+?)\s+(\d+)\s*[,]?\s*(.+?)\s+(\d+)'
        match = re.search(score_pattern, line)

        if match:
            team1, score1, team2, score2 = match.groups()
            valid1, clean_score1 = validate_score(score1, line, validator, metrics)
            valid2, clean_score2 = validate_score(score2, line, validator, metrics)

            if valid1 and valid2:
                games.append({
                    'section': current_section,
                    'home_team': team1.strip(),
                    'home_score': clean_score1,
                    'away_team': team2.strip(),
                    'away_score': clean_score2,
                    'original_line': line,
                    'needs_review': 'No'
                })

    return games

def process_scores_image(image_path: str) -> Tuple[List[Dict[str, str]], str, OCRQualityMetrics, ScoreValidator]:
    """Process image with validation and logging."""
    validator = ScoreValidator()
    metrics = OCRQualityMetrics()
    scan_metrics = ScanQualityMetrics()

    # Read and process image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    # Analyze image quality
    scan_quality = scan_metrics.analyze_image_quality(image)

    # Create debug directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = f"debug_images_{timestamp}"
    os.makedirs(debug_dir, exist_ok=True)

    # Process image and extract text
    processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    debug_path = os.path.join(debug_dir, f"{os.path.splitext(os.path.basename(image_path))[0]}_enhanced.png")
    cv2.imwrite(debug_path, processed)

    # Extract text
    custom_config = '--oem 3 --psm 6'
    text = pytesseract.image_to_string(processed, config=custom_config)

    # Fix OCR errors and headers
    text = fix_common_ocr_errors(text, validator, metrics)
    text = fix_division_headers(text, validator, metrics)
    
    # Extract and validate games
    games = extract_game_lines(text, validator, metrics)

    return games, text, metrics, validator

def main():
    staged_folder = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged"
    
    for image_file in [f for f in os.listdir(staged_folder) if f.endswith(('.jpg', '.jpeg', '.png'))]:
        print(f"\n📄 Processing: {image_file}")
        image_path = os.path.join(staged_folder, image_file)
        
        try:
            games, text, metrics, validator = process_scores_image(image_path)
            
            # Print extracted games
            print("\n📊 Extracted Games:")
            print("-" * 50)
            
            current_section = None
            for game in games:
                if game['section'] != current_section:
                    current_section = game['section']
                    print(f"\n{current_section}")
                    print("-" * len(current_section))
                print(f"{game['home_team']} {game['home_score']} - {game['away_team']} {game['away_score']}")
            
            # Print corrections made
            if validator.corrections_made:
                print("\n🔧 OCR Corrections Made:")
                print("-" * 50)
                for correction in validator.corrections_made:
                    print(f"• {correction['original']} → {correction['corrected']}")
                    print(f"  Reason: {correction['reason']}")
            
            # Print verification needs
            if validator.verification_needed:
                print("\n⚠️ Manual Verification Needed:")
                print("-" * 50)
                for verify in validator.verification_needed:
                    print(f"• {verify['line']}")
                    print(f"  Reason: {verify['reason']}")
            
            print(f"\n✅ Processed {len(games)} valid games")
            print(f"💾 Full text saved to: {os.path.splitext(image_file)[0]}.txt")
            
        except Exception as e:
            print(f"❌ Error processing {image_file}: {str(e)}")
            raise

if __name__ == "__main__":
    main()