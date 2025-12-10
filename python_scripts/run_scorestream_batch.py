import time
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
START_URL = "https://scorestream.com/team/philemon-wright-high-school-falcons-291529/games"
MAX_TEAMS_PER_BATCH = 50  # Process in batches

# PERFORMANCE OPTIONS
HEADLESS_MODE = True  # Run browser in background (faster, less resource intensive)
PAGE_LOAD_TIMEOUT = 20  # Max seconds to wait for page load (reduced for slow sites)

# TARGET STATES/PROVINCES (add more as needed)
TARGET_REGIONS = ['ON', 'QC', 'NS', 'Ontario', 'Quebec', 'Nova Scotia']

# SEASON FILTER - Include recent historical seasons for Canadian teams
TARGET_SEASONS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

# OUTPUT FILES
PROGRESS_FILE = "scraper_progress.csv"
QUEUE_FILE = "scraper_queue.csv"

def dismiss_popups(driver):
    """
    Try to dismiss any popups, ads, or overlays that might be blocking content
    """
    try:
        # Common popup close button selectors
        close_selectors = [
            "button[class*='close']",
            "button[class*='dismiss']",
            "[class*='modal-close']",
            "[class*='popup-close']",
            "button[aria-label='Close']",
            ".close",
            "#close",
            "button.btn-close",
        ]
        
        for selector in close_selectors:
            try:
                close_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in close_buttons:
                    if button.is_displayed():
                        button.click()
                        time.sleep(0.5)
            except:
                continue
    except:
        pass

def extract_team_id(url):
    """Extract numeric team ID from ScoreStream URL"""
    match = re.search(r'/team/[^/]+-(\d+)', url)
    return match.group(1) if match else None

def extract_state_from_text(text):
    """
    Extract state/province from text like "Ottawa, ON" or "(ON)" or "Ontario"
    """
    if not text:
        return None
    
    # Look for common patterns
    patterns = [
        r'\(([A-Z]{2})\)',  # (ON)
        r',\s*([A-Z]{2})\s*$',  # , ON at end of line
        r',\s*([A-Z]{2})\s+',  # , ON followed by space
        r'[,\s]+(ON|QC|NS|NB|AB|BC|MB|SK|PE|NL|NT|YT|NU)\s*[,\.\s]',  # Province codes
        r',\s*(Ontario|Quebec|Nova Scotia|New Brunswick)',  # Full province names
        r'(Ottawa|Gatineau|Toronto|Montreal|Halifax)',  # Major cities (implies province)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            state = match.group(1).strip()
            
            # Normalize full names and cities to codes
            state_map = {
                'Ontario': 'ON', 'Quebec': 'QC', 'Nova Scotia': 'NS',
                'New Brunswick': 'NB', 'Alberta': 'AB', 'British Columbia': 'BC',
                'Manitoba': 'MB', 'Saskatchewan': 'SK', 
                'Ottawa': 'ON', 'Gatineau': 'QC', 'Toronto': 'ON',
                'Montreal': 'QC', 'Halifax': 'NS'
            }
            
            return state_map.get(state, state.upper())
    
    return None

def is_target_region(text):
    """Check if text contains a target region"""
    if not text:
        return False
    
    text_upper = text.upper()
    for region in TARGET_REGIONS:
        if region.upper() in text_upper:
            return True
    return False

def parse_scorestream_date(date_text, game_text=""):
    """
    Parse ScoreStream date formats:
    - "Boys Varsity Football - Oct 18 '18"
    - "Oct 18 '25"
    - "Sep 1, 18"
    
    Note: '18 means 2018, '25 means 2025
    """
    if not date_text or date_text == "Unknown":
        return None
    
    # Try to extract from full game text first
    full_text = f"{game_text} {date_text}"
    
    # Pattern 1: "Oct 18 '18" or "Sep 1 '25"
    match = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})\s+'(\d{2})", full_text)
    if match:
        month_str, day, year_short = match.groups()
        year_short_int = int(year_short)
        
        # Smart year conversion:
        # 16-25 = 2016-2025 (recent/current)
        # 00-15 = 2000-2015 (early 2000s)
        # 26-99 = 1926-1999 (last century - unlikely for high school games)
        if year_short_int <= 25:
            year = 2000 + year_short_int
        else:
            year = 1900 + year_short_int
        
        try:
            date_obj = datetime.strptime(f"{month_str} {day} {year}", "%b %d %Y")
            return date_obj
        except:
            pass
    
    # Pattern 2: "Sep 1, 18" (comma format)
    match = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s*(\d{2})", full_text)
    if match:
        month_str, day, year_short = match.groups()
        year_short_int = int(year_short)
        
        if year_short_int <= 25:
            year = 2000 + year_short_int
        else:
            year = 1900 + year_short_int
        
        try:
            date_obj = datetime.strptime(f"{month_str} {day} {year}", "%b %d %Y")
            return date_obj
        except:
            pass
    
    # Pattern 3: Standard date formats
    for fmt in ['%b %d %Y', '%m/%d/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_text, fmt)
        except:
            continue
    
    return None

def detect_game_level(text):
    """Detect if game is JV, Varsity, etc."""
    text_lower = text.lower()
    
    jv_patterns = ['jv', 'j.v.', 'junior varsity', 'boys jv']
    if any(pattern in text_lower for pattern in jv_patterns):
        return ('JV', True)
    
    if 'freshman' in text_lower or 'frosh' in text_lower:
        return ('Freshman', True)
    
    if 'junior' in text_lower and 'varsity' not in text_lower:
        return ('Junior', True)
    
    if 'sophomore' in text_lower or 'soph' in text_lower:
        return ('Sophomore', True)
    
    return ('Varsity', False)

def normalize_team_name(name, state=None, game_level='Varsity'):
    """Normalize team name and add state/JV suffix"""
    if not name or len(name) < 2:
        return name
    
    # Remove common prefixes
    name = re.sub(r'^The\s+', '', name, flags=re.IGNORECASE)
    
    # Title case
    name = name.title()
    
    # Remove redundant words
    name = name.replace(' High School', '').replace(' Hs', '')
    
    # Add JV suffix if needed
    if game_level in ['JV', 'Freshman', 'Sophomore', 'Junior'] and game_level not in name:
        name = f"{name} {game_level}"
    
    # Add state if provided and not already there
    if state and f"({state})" not in name:
        name = f"{name} ({state})"
    
    return name

def load_progress():
    """Load previously visited teams"""
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return set(row['TeamID'] for row in reader)
    except FileNotFoundError:
        return set()

def save_progress(team_id, team_name, state, games_found):
    """Save progress to file"""
    file_exists = False
    try:
        with open(PROGRESS_FILE, 'r'):
            file_exists = True
    except FileNotFoundError:
        pass
    
    with open(PROGRESS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['TeamID', 'TeamName', 'State', 'GamesFound', 'Timestamp'])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'TeamID': team_id,
            'TeamName': team_name,
            'State': state,
            'GamesFound': games_found,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

def load_queue():
    """Load queue from file"""
    try:
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [row['URL'] for row in reader]
    except FileNotFoundError:
        return []

def save_queue(urls):
    """Save queue to file"""
    with open(QUEUE_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['URL', 'Timestamp'])
        writer.writeheader()
        for url in urls:
            writer.writerow({
                'URL': url,
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

def scrape_scorestream_batch(start_urls=None, resume=False):
    """
    Scrape ScoreStream in controlled batches with geographic filtering
    """
    print("="*70)
    print("🏈 SCORESTREAM CANADIAN FOOTBALL SCRAPER")
    print("="*70)
    print(f"Target Regions: {', '.join(TARGET_REGIONS)}")
    print(f"Target Seasons: {', '.join(map(str, TARGET_SEASONS))}")
    print(f"Batch Size: {MAX_TEAMS_PER_BATCH} teams")
    print("="*70)
    
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Performance options
    if HEADLESS_MODE:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        print("🚀 Running in headless mode (faster)")
    
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    
    # Ad blocking and popup handling
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,  # Block notifications
        "profile.default_content_setting_values.media_stream": 2,   # Block media
    })
    
    print("🔧 Initializing Chrome driver...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_window_size(1920, 1080)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        print("✅ Chrome driver initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize Chrome driver: {e}")
        print("   Make sure Chrome browser is installed and up to date.")
        return [], []

    # Load progress and queue
    visited_team_ids = load_progress()
    
    if resume and load_queue():
        urls_to_visit = load_queue()
        print(f"📂 Resuming: {len(urls_to_visit)} teams in queue")
    elif start_urls:
        urls_to_visit = start_urls
        print(f"🆕 Starting fresh with {len(start_urls)} seed URLs")
    else:
        urls_to_visit = [START_URL]
        print(f"🆕 Starting with default seed URL")
    
    all_games = []
    game_urls_visited = set()
    teams_this_batch = 0
    skipped_regions = []

    try:
        print(f"📋 Starting with {len(urls_to_visit)} URLs in queue")
        print(f"🎯 Will process up to {MAX_TEAMS_PER_BATCH} teams\n")
        
        while urls_to_visit and teams_this_batch < MAX_TEAMS_PER_BATCH:
            current_url = urls_to_visit.pop(0)
            
            if "/games" not in current_url:
                current_url = current_url.rstrip('/') + "/games"

            team_id = extract_team_id(current_url)
            if not team_id or team_id in visited_team_ids:
                print(f"   ⏭️  Skipping: Already visited or invalid ID")
                continue
            
            print(f"\n{'='*70}")
            print(f"🕷️  TEAM {teams_this_batch + 1}/{MAX_TEAMS_PER_BATCH}")
            print(f"ID: {team_id} | URL: {current_url}")
            print('='*70)
            
            driver.get(current_url)
            time.sleep(4)
            
            # Get page text for region detection
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # --- EXTRACT TEAM INFO ---
            host_name = None
            team_state = None
            
            # Try to get team name
            try:
                team_header = driver.find_element(By.CSS_SELECTOR, "h1, .team-name, [class*='TeamHeader']")
                host_name = team_header.text.strip()
            except:
                pass
            
            if not host_name or len(host_name) < 3:
                try:
                    title = driver.title
                    host_name = title.split(' - ')[0].strip()
                except:
                    pass
            
            # Extract state from page
            team_state = extract_state_from_text(page_text)
            
            # --- REGION FILTER ---
            # First try to extract state from page text if not found yet
            if not team_state:
                team_state = extract_state_from_text(page_text)
            
            # Check if team is in target region
            in_target = False
            if team_state and is_target_region(team_state):
                in_target = True
            elif is_target_region(page_text):
                # State not explicitly found, but page mentions target regions
                in_target = True
                # Try harder to find the state
                for region in TARGET_REGIONS:
                    if region.upper() in page_text.upper():
                        team_state = region if len(region) == 2 else region[:2].upper()
                        break
            
            if not in_target:
                print(f"⏭️  SKIPPING: Not in target regions (detected: {team_state or 'Unknown'})")
                skipped_regions.append((host_name or "Unknown", team_state or "Unknown", current_url))
                visited_team_ids.add(team_id)
                save_progress(team_id, host_name or "Unknown", team_state or "Unknown", 0)
                continue
            
            print(f"✅ IN TARGET REGION: {team_state or 'Detected on page'}")
            print(f"🏠 Team: {host_name}")
            
            teams_this_batch += 1
            visited_team_ids.add(team_id)
            
            # Scroll and load games
            body = driver.find_element(By.TAG_NAME, "body")
            for scroll in range(5):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.8)
            time.sleep(2)

            # Find game links
            game_links = []
            try:
                potential_game_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
                for link in potential_game_links:
                    href = link.get_attribute("href")
                    if href and "/game/" in href and href not in game_urls_visited:
                        game_links.append(href)
            except Exception as e:
                print(f"   ⚠️  Error finding games: {e}")

            print(f"📋 Found {len(game_links)} games")

            # Process games
            games_this_team = 0
            for idx, game_link in enumerate(game_links[:30], 1):
                if game_link in game_urls_visited:
                    continue
                    
                game_urls_visited.add(game_link)
                
                # Try to load game page with retries
                max_retries = 2
                game_loaded = False
                
                for retry in range(max_retries):
                    try:
                        print(f"   [{idx}] ...{game_link[-40:]}")
                        
                        # Try to load page with aggressive timeout handling
                        try:
                            driver.get(game_link)
                        except Exception as load_error:
                            # If timeout, try to stop the page load and use what we have
                            if "timeout" in str(load_error).lower():
                                print(f"       ⏱️  Page load timeout, stopping page load...")
                                try:
                                    driver.execute_script("window.stop();")
                                except:
                                    pass
                            else:
                                raise
                        
                        time.sleep(2)  # Brief wait for dynamic content
                        
                        # Try to dismiss any popups/ads
                        dismiss_popups(driver)
                        
                        game_loaded = True
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        if "timeout" in str(e).lower():
                            print(f"       ⏱️  Timeout loading page (attempt {retry + 1}/{max_retries})")
                            if retry < max_retries - 1:
                                # Try to stop the page load
                                try:
                                    driver.execute_script("window.stop();")
                                except:
                                    pass
                                time.sleep(2)
                            else:
                                print(f"       ❌ Failed after {max_retries} attempts, skipping game")
                        else:
                            print(f"       ❌ Error loading page: {e}")
                            break
                
                if not game_loaded:
                    # Skip this game and move to next
                    continue
                
                try:
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    # DEBUG: Show snippet of page to understand date format
                    if '[1]' in f"[{idx}]":  # Only for first game
                        date_snippet = page_text[:500]
                        print(f"       🔍 DEBUG - Page text sample: {date_snippet[:200]}...")
                    
                    # Detect level
                    game_level, is_sub_varsity = detect_game_level(page_text)
                    
                    # Extract date from page
                    game_date = None
                    game_date_str = "Unknown"
                    
                    # Look for date in multiple formats on the page
                    # Format 1: "Oct 19, 2017" or "October 19, 2017" (full year with comma)
                    date_match = re.search(r"([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})", page_text)
                    if date_match:
                        month_str, day, year = date_match.groups()
                        try:
                            # Try full month name first
                            game_date = datetime.strptime(f"{month_str} {day} {year}", "%B %d %Y")
                            game_date_str = game_date.strftime('%b %d, %Y')
                            print(f"       📅 Parsed date: {game_date.strftime('%Y-%m-%d')} from '{month_str} {day}, {year}'")
                        except ValueError:
                            # Try abbreviated month name
                            try:
                                game_date = datetime.strptime(f"{month_str} {day} {year}", "%b %d %Y")
                                game_date_str = game_date.strftime('%b %d, %Y')
                                print(f"       📅 Parsed date: {game_date.strftime('%Y-%m-%d')} from '{month_str} {day}, {year}'")
                            except:
                                pass
                    
                    # Format 2: "Oct 19 '18" (abbreviated year - fallback)
                    if not game_date:
                        date_match2 = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})\s+'(\d{2})", page_text)
                        if date_match2:
                            game_date_str = date_match2.group(0)
                            game_date = parse_scorestream_date(game_date_str, page_text)
                            if game_date:
                                print(f"       📅 Parsed date: {game_date.strftime('%Y-%m-%d')} from '{game_date_str}'")
                    
                    # Season filter
                    if game_date and game_date.year not in TARGET_SEASONS:
                        print(f"       ⏭️  Skipping: {game_date.year} (not in target seasons)")
                        continue
                    
                    # Find teams
                    opponent_name = None
                    opponent_url = None
                    opponent_state = None
                    score1 = None
                    score2 = None
                    
                    team_links_on_game = driver.find_elements(By.CSS_SELECTOR, "a[href*='/team/']")
                    
                    for tlink in team_links_on_game:
                        try:
                            opp_href = tlink.get_attribute("href")
                            opp_text = tlink.text.strip()
                            opp_id = extract_team_id(opp_href)
                            
                            if opp_id == team_id:
                                continue
                            
                            if opp_href and opp_id and len(opp_text) > 2:
                                # Get opponent state from their link text or context
                                opponent_state = None
                                
                                # Method 1: Check parent element for location text
                                try:
                                    opp_parent = tlink.find_element(By.XPATH, "./parent::*")
                                    opp_context = opp_parent.text
                                    opponent_state = extract_state_from_text(opp_context)
                                except:
                                    pass
                                
                                # Method 2: Look for city, state pattern near the team name
                                if not opponent_state:
                                    # Common patterns: "Ottawa, ON" or "Gatineau, QC"
                                    try:
                                        # Get more context - grandparent container
                                        grandparent = tlink.find_element(By.XPATH, "./parent::*/parent::*")
                                        full_context = grandparent.text
                                        opponent_state = extract_state_from_text(full_context)
                                    except:
                                        pass
                                
                                # Method 3: Check entire page for this team's location
                                if not opponent_state:
                                    # Look for pattern like "ASHBURY COLLEGE...Ottawa, ON"
                                    team_name_upper = opp_text.upper()
                                    pattern = rf"{team_name_upper}[^,]*,\s*([A-Z]{{2}})"
                                    match = re.search(pattern, page_text.upper())
                                    if match:
                                        opponent_state = match.group(1)
                                
                                opponent_name = opp_text
                                opponent_url = opp_href
                                
                                print(f"       🏫 Found opponent: {opponent_name} (State: {opponent_state or 'Unknown'})")
                                
                                # Only add to queue if in target region
                                if opp_id not in visited_team_ids:
                                    if opponent_state and is_target_region(opponent_state):
                                        opp_games_url = opp_href.split("/games")[0] + "/games"
                                        if opp_games_url not in urls_to_visit:
                                            urls_to_visit.append(opp_games_url)
                                            print(f"       ➕ Queued: {opponent_name} ({opponent_state})")
                                    else:
                                        # Even if state unknown, check if it's mentioned on page as Canadian
                                        if is_target_region(page_text):
                                            # Assume it's Canadian if page mentions ON/QC/NS
                                            opp_games_url = opp_href.split("/games")[0] + "/games"
                                            if opp_games_url not in urls_to_visit:
                                                urls_to_visit.append(opp_games_url)
                                                print(f"       ➕ Queued (region detected on page): {opponent_name}")
                                        else:
                                            print(f"       ⏭️  Not queuing: {opponent_name} ({opponent_state or 'Unknown'})")
                                
                                break
                        except:
                            continue
                    
                    # Extract scores
                    try:
                        score_elements = driver.find_elements(By.CSS_SELECTOR, 
                            "[class*='score'], [class*='Score'], .final-score")
                        scores_text = " ".join([s.text for s in score_elements])
                        scores = re.findall(r'\b(\d{1,3})\b', scores_text)
                        
                        if len(scores) >= 2:
                            score1 = scores[0]
                            score2 = scores[1]
                    except:
                        pass
                    
                    # Save game
                    if opponent_name:
                        normalized_host = normalize_team_name(host_name, team_state, game_level)
                        normalized_opp = normalize_team_name(opponent_name, opponent_state, game_level)
                        
                        game_data = {
                            "Date": game_date.strftime('%Y-%m-%d') if game_date else game_date_str,
                            "Season": game_date.year if game_date else "",
                            "Level": game_level,
                            "Host": normalized_host,
                            "HostState": team_state or "",
                            "Opponent": normalized_opp,
                            "OpponentState": opponent_state or "",
                            "Score1": score1 or "",
                            "Score2": score2 or "",
                            "GameLink": game_link,
                            "OpponentLink": opponent_url,
                            "OpponentID": extract_team_id(opponent_url)
                        }
                        
                        all_games.append(game_data)
                        games_this_team += 1
                        
                        score_display = f"{score1}-{score2}" if score1 and score2 else "N/A"
                        date_display = game_date.strftime('%b %d, %Y') if game_date else "Unknown"
                        print(f"       ✅ {date_display}: vs {normalized_opp} ({score_display})")
                    
                    driver.back()
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"       ❌ Error: {e}")
                    try:
                        driver.get(current_url)
                        time.sleep(2)
                    except:
                        pass
            
            # Save progress
            save_progress(team_id, host_name, team_state, games_this_team)
            
            print(f"\n   📊 Team Summary: {games_this_team} games logged")
            print(f"   📈 Batch Progress: {teams_this_batch}/{MAX_TEAMS_PER_BATCH} teams")
            print(f"   📋 Queue: {len(urls_to_visit)} teams waiting")

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Save remaining queue
        save_queue(urls_to_visit)
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass

    # Display skipped regions summary
    if skipped_regions:
        print(f"\n{'='*70}")
        print(f"⏭️  SKIPPED TEAMS (Outside target regions): {len(skipped_regions)}")
        print('='*70)
        for name, state, url in skipped_regions[:10]:
            print(f"   {name} ({state})")
        if len(skipped_regions) > 10:
            print(f"   ... and {len(skipped_regions) - 10} more")

    return all_games, urls_to_visit

if __name__ == "__main__":
    start_time = time.time()
    
    print("\n🏈 Starting batch scrape...")
    print("Press Ctrl+C to stop early and save progress\n")
    
    games, remaining_queue = scrape_scorestream_batch(resume=False)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"✅ BATCH COMPLETE")
    print(f"{'='*70}")
    print(f"⏱️  Time: {elapsed/60:.1f} minutes")
    print(f"🏈 Games scraped: {len(games)}")
    print(f"📋 Remaining queue: {len(remaining_queue)} teams")
    
    if games:
        # Save to timestamped file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"scorestream_batch_{timestamp}.csv"
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["Date", "Season", "Level", "Host", "HostState", "Opponent", 
                         "OpponentState", "Score1", "Score2", "GameLink", "OpponentLink", "OpponentID"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(games)
        
        print(f"📁 Saved: {output_file}")
        
        # Stats
        varsity_count = len([g for g in games if g['Level'] == 'Varsity'])
        jv_count = len([g for g in games if g['Level'] == 'JV'])
        
        print(f"\n📊 Games by Level:")
        print(f"   Varsity: {varsity_count}")
        print(f"   JV: {jv_count}")
        
        unique_teams = set([g['Host'] for g in games] + [g['Opponent'] for g in games])
        print(f"\n🏫 Unique teams involved: {len(unique_teams)}")
        
        # Region breakdown
        states = [g['HostState'] for g in games if g['HostState']] + \
                 [g['OpponentState'] for g in games if g['OpponentState']]
        from collections import Counter
        state_counts = Counter(states)
        print(f"\n🗺️  Regions:")
        for state, count in state_counts.most_common():
            print(f"   {state}: {count}")
    
    if remaining_queue:
        print(f"\n💡 To continue: Run script again with resume=True")
        print(f"   Queue saved to: {QUEUE_FILE}")
    
    print("\n✨ Done!")