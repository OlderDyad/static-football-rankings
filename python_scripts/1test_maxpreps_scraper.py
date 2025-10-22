# maxpreps_scraper_final.py
# Final robust version addressing timeout and opponent extraction issues

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import csv
import re
import random
from urllib.parse import urljoin

# === CONFIGURATION ===
URL_LIST_FILE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/excel_files/MaxPreps_Export.xlsx"
OUTPUT_CSV_FILE = "C:/Users/demck/OneDrive/Football_2024/static-football-rankings/python_scripts/final_schedules.csv"
URL_PROCESS_LIMIT = 5
WAIT_TIMEOUT = 15
MAX_RETRIES = 2

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_driver():
    """Set up Chrome driver with anti-detection measures"""
    chrome_options = Options()
    
    # Stealth options
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Performance options
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    
    # User agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Anti-detection scripts
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Set timeouts
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    
    return driver

def extract_opponent_name_from_cell(opponent_cell):
    """Extract opponent name from cell using multiple strategies"""
    
    # Strategy 1: Extract from link text (most reliable)
    try:
        links = opponent_cell.find_elements(By.TAG_NAME, 'a')
        if links:
            link = links[0]
            href = link.get_attribute('href')
            link_text = link.text.strip()
            
            # Method 1a: Extract from URL
            if href and 'maxpreps.com' in href:
                url_parts = href.rstrip('/').split('/')
                if len(url_parts) >= 5:
                    city_name = url_parts[4]  # Position 4 in URL structure
                    if city_name and city_name != 'tx':
                        return city_name.replace('-', ' ').title(), href
            
            # Method 1b: Extract from link text, removing indicators
            if link_text:
                # Remove prefixes like @, vs, at
                clean_text = link_text
                for prefix in ['@\n', '@', 'vs\n', 'vs', 'at\n', 'at']:
                    clean_text = clean_text.replace(prefix, '', 1).strip()
                
                # Take first line if multi-line
                lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
                if lines and lines[0] not in ['vs', 'at', '@']:
                    return lines[0], href
    except Exception as e:
        logger.debug(f"Error extracting from link: {e}")
    
    # Strategy 2: Extract from cell text as fallback
    try:
        cell_text = opponent_cell.text.strip()
        lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
        
        for line in lines:
            # Skip indicator-only lines
            if line.lower() in ['vs', 'at', '@']:
                continue
            # Remove prefixes and take the name
            clean_line = line
            for prefix in ['@', 'vs ', 'at ']:
                if clean_line.lower().startswith(prefix):
                    clean_line = clean_line[len(prefix):].strip()
            
            if clean_line and len(clean_line) > 1:
                return clean_line, ""
    except Exception as e:
        logger.debug(f"Error extracting from cell text: {e}")
    
    return None, ""

def scrape_schedule_data_robust(driver):
    """Robust schedule data extraction with multiple fallbacks"""
    logger.info("Extracting schedule data...")
    games_data = []
    
    try:
        # Wait for page load with shorter timeout
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)
        
        # Extract team name
        primary_team_name = "Unknown Team"
        try:
            title_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.title'))
            )
            title_text = title_element.text.strip()
            if 'Football Schedule' in title_text:
                team_name = title_text.replace('Football Schedule', '').strip()
                url_parts = driver.current_url.split('/')
                if len(url_parts) >= 4:
                    state_code = url_parts[3].upper()
                    primary_team_name = f"{team_name} ({state_code})"
        except:
            # Fallback: extract from URL
            try:
                url_parts = driver.current_url.split('/')
                if len(url_parts) >= 5:
                    city_part = url_parts[4]
                    state_part = url_parts[3].upper() if len(url_parts[3]) == 2 else ""
                    team_name = city_part.replace('-', ' ').title()
                    primary_team_name = f"{team_name} ({state_part})" if state_part else team_name
            except:
                pass
        
        logger.info(f"Identified team: {primary_team_name}")
        
        # Find tables with multiple selectors
        tables = []
        table_selectors = [
            'table[class*="sc-"]',  # Dynamic class pattern
            'table.hTFoSx',         # Specific class
            'table tbody',          # Generic fallback
            'table'                 # Last resort
        ]
        
        for selector in table_selectors:
            try:
                found_tables = driver.find_elements(By.CSS_SELECTOR, selector)
                if found_tables:
                    tables = found_tables
                    logger.info(f"Found {len(tables)} tables with selector: {selector}")
                    break
            except:
                continue
        
        if not tables:
            logger.warning("No schedule tables found")
            return []
        
        # Process tables
        for table_num, table in enumerate(tables):
            try:
                rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # Skip header
                logger.info(f"Processing table {table_num} with {len(rows)} rows")
                
                for i, row in enumerate(rows):
                    try:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if len(cells) < 3:
                            continue
                        
                        # Extract data
                        date = cells[0].text.strip()
                        if not date:
                            continue
                        
                        # Extract opponent using robust method
                        opponent_name, opponent_url = extract_opponent_name_from_cell(cells[1])
                        if not opponent_name or opponent_name.lower() in ['vs', 'at', '@']:
                            logger.debug(f"Skipping row {i}: invalid opponent '{opponent_name}'")
                            continue
                        
                        # Determine home/away
                        opponent_cell_text = cells[1].text.strip()
                        is_away_game = opponent_cell_text.startswith('@') or '@\n' in opponent_cell_text
                        
                        if is_away_game:
                            home_team = opponent_name
                            away_team = primary_team_name
                        else:
                            home_team = primary_team_name
                            away_team = opponent_name
                        
                        # Parse scores
                        home_score = ""
                        away_score = ""
                        
                        if len(cells) >= 3:
                            result_text = cells[2].text.strip()
                            if any(indicator in result_text.upper() for indicator in ['W ', 'L ', 'T ']):
                                score_match = re.search(r'(\d+)[^\d]*(\d+)', result_text)
                                if score_match:
                                    score1, score2 = int(score_match.group(1)), int(score_match.group(2))
                                    
                                    if result_text.upper().startswith('W'):
                                        primary_score, opponent_score = max(score1, score2), min(score1, score2)
                                    elif result_text.upper().startswith('L'):
                                        primary_score, opponent_score = min(score1, score2), max(score1, score2)
                                    else:
                                        primary_score, opponent_score = score1, score2
                                    
                                    if is_away_game:
                                        home_score, away_score = opponent_score, primary_score
                                    else:
                                        home_score, away_score = primary_score, opponent_score
                        
                        # Create game record
                        game_data = {
                            'Home': home_team,
                            'HomeScore': home_score,
                            'Away': away_team,
                            'AwayScore': away_score,
                            'Date': date,
                            'OpponentURL': opponent_url or ""
                        }
                        
                        games_data.append(game_data)
                        logger.debug(f"Extracted: {date} - {home_team} vs {away_team}")
                        
                    except Exception as e:
                        logger.debug(f"Error processing row {i}: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Error processing table {table_num}: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(games_data)} games")
        
    except Exception as e:
        logger.error(f"Error in schedule extraction: {e}")
    
    return games_data

def process_url_with_retry(driver, url, max_retries=MAX_RETRIES):
    """Process a single URL with retry logic"""
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry {attempt}/{max_retries} for {url}")
                time.sleep(random.uniform(5, 10))  # Longer delay on retry
            
            driver.get(url)
            return scrape_schedule_data_robust(driver)
            
        except TimeoutException:
            logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
            if attempt == max_retries:
                logger.error(f"Max retries exceeded for {url}")
                return []
        except WebDriverException as e:
            logger.warning(f"WebDriver error on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                logger.error(f"WebDriver error, giving up on {url}")
                return []
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            return []
    
    return []

def main():
    logger.info("=== Starting Final MaxPreps Scraper ===")
    
    try:
        # Read URLs
        url_df = pd.read_excel(URL_LIST_FILE)
        all_urls = url_df['URL'].dropna().tolist()
    except Exception as e:
        logger.error(f"Failed to read URLs: {e}")
        return
    
    urls_to_process = all_urls[:URL_PROCESS_LIMIT]
    logger.info(f"Processing {len(urls_to_process)} URLs")
    
    # Setup driver
    driver = setup_driver()
    all_games_data = []
    
    try:
        for i, url in enumerate(urls_to_process, 1):
            logger.info(f"[{i}/{len(urls_to_process)}] Processing: {url}")
            
            # Random delay between requests
            if i > 1:
                delay = random.uniform(8, 15)  # Increased delay
                logger.info(f"Waiting {delay:.1f} seconds...")
                time.sleep(delay)
            
            games = process_url_with_retry(driver, url)
            
            if games:
                all_games_data.extend(games)
                logger.info(f"✓ Extracted {len(games)} games")
            else:
                logger.warning(f"✗ No games found")
    
    finally:
        driver.quit()
    
    # Write results
    if all_games_data:
        try:
            logger.info(f"Writing {len(all_games_data)} games to {OUTPUT_CSV_FILE}")
            with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['Home', 'HomeScore', 'Away', 'AwayScore', 'Date', 'OpponentURL']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_games_data)
            
            logger.info("🎉 Scraping completed successfully!")
            
            # Print sample results
            logger.info("=== SAMPLE RESULTS ===")
            for game in all_games_data[:5]:
                logger.info(f"{game['Date']}: {game['Home']} vs {game['Away']}")
                
        except Exception as e:
            logger.error(f"Failed to write results: {e}")
    else:
        logger.warning("No data was successfully scraped")

if __name__ == "__main__":
    main()

