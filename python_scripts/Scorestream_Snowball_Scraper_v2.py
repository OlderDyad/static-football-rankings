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
MAX_TEAMS = 50 
SEASON_YEAR = "2025"

def extract_team_id(url):
    """Extract numeric team ID from ScoreStream URL"""
    match = re.search(r'/team/[^/]+-(\d+)', url)
    return match.group(1) if match else None

def detect_game_level(text):
    """
    Detect if game is JV, Varsity, Freshman, etc.
    Returns tuple: (level, is_jv_or_lower)
    """
    text_lower = text.lower()
    
    # JV indicators
    jv_patterns = ['jv', 'j.v.', 'junior varsity', 'boys jv']
    if any(pattern in text_lower for pattern in jv_patterns):
        return ('JV', True)
    
    # Freshman
    if 'freshman' in text_lower or 'frosh' in text_lower:
        return ('Freshman', True)
    
    # Junior (not JV, just Junior level)
    if 'junior' in text_lower and 'varsity' not in text_lower:
        return ('Junior', True)
    
    # Sophomore
    if 'sophomore' in text_lower or 'soph' in text_lower:
        return ('Sophomore', True)
    
    # Default to Varsity
    return ('Varsity', False)

def extract_full_team_name(driver, team_link_element):
    """
    Extract full team name by checking parent containers
    ScoreStream shows "St. Matthew Tigers" but link text might just be "ST. MATTHEW"
    """
    try:
        # Try to find the full name in parent container
        parent = team_link_element.find_element(By.XPATH, "./parent::*")
        full_text = parent.text.strip()
        
        # Split by newlines and look for team name pattern
        lines = full_text.split('\n')
        for line in lines:
            # Team names are usually longer than 3 chars and contain letters
            if len(line) > 3 and any(c.isalpha() for c in line):
                # Skip if it's just a score or location
                if not re.match(r'^\d+$', line) and 'final' not in line.lower():
                    # This might be the full team name
                    if any(word in line for word in ['high', 'school', 'college', 'tigers', 'falcons', 'saints']):
                        return line.strip()
        
        # Fallback to link text
        return team_link_element.text.strip()
    except:
        return team_link_element.text.strip()

def normalize_team_name(name, game_level='Varsity'):
    """
    Normalize team name and add JV suffix if needed
    Examples:
    - "ST. MATTHEW" -> "St. Matthew (ON)"
    - "Sacred Heart Catholic" + JV -> "Sacred Heart Catholic JV (ON)"
    """
    if not name or len(name) < 2:
        return name
    
    # Title case for better formatting
    name = name.title()
    
    # Fix common patterns
    name = name.replace(' High School', '')
    name = name.replace(' Hs', '')
    
    # Add JV suffix if needed and not already there
    if game_level in ['JV', 'Freshman', 'Sophomore', 'Junior'] and game_level not in name:
        name = f"{name} {game_level}"
    
    return name

def scrape_scorestream_snowball():
    print("Launching ScoreStream Snowball Scraper v2...")
    print("Features: JV detection, better team names, level tracking")
    
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(1920, 1080)

    urls_to_visit = [START_URL]
    visited_team_ids = set()
    all_games = []
    game_urls_visited = set()

    try:
        while urls_to_visit and len(visited_team_ids) < MAX_TEAMS:
            current_url = urls_to_visit.pop(0)
            
            if "/games" not in current_url:
                current_url = current_url.rstrip('/') + "/games"

            team_id = extract_team_id(current_url)
            if not team_id or team_id in visited_team_ids:
                continue
            
            print(f"\n{'='*60}")
            print(f"🕷️ TEAM #{len(visited_team_ids)+1}: {current_url}")
            print('='*60)
            driver.get(current_url)
            time.sleep(4)
            
            visited_team_ids.add(team_id)
            
            # --- EXTRACT HOST TEAM NAME ---
            host_name = None
            
            try:
                # Method 1: Look for team header
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
            
            if not host_name or len(host_name) < 3:
                try:
                    team_slug = re.search(r'/team/([^/]+)-\d+', current_url)
                    if team_slug:
                        host_name = team_slug.group(1).replace('-', ' ').title()
                except:
                    pass
            
            if not host_name or len(host_name) < 3:
                print(f"   ⚠️ Could not identify host team. Skipping.")
                continue
            
            print(f"🏠 Host Team: {host_name}")

            # --- SCROLL AND FIND GAMES ---
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
                print(f"   ⚠️ Error finding game links: {e}")

            print(f"📋 Found {len(game_links)} games to process")

            # --- PROCESS EACH GAME ---
            games_this_team = 0
            for idx, game_link in enumerate(game_links[:30], 1):
                if game_link in game_urls_visited:
                    continue
                    
                game_urls_visited.add(game_link)
                
                try:
                    print(f"\n   [{idx}/{min(len(game_links), 30)}] Game: ...{game_link[-30:]}")
                    driver.get(game_link)
                    time.sleep(3)
                    
                    # Get page source for level detection
                    page_source = driver.page_source
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    # Detect game level (JV, Varsity, etc.)
                    game_level, is_sub_varsity = detect_game_level(page_text)
                    level_indicator = " [JV]" if is_sub_varsity else ""
                    
                    print(f"      🎯 Level: {game_level}{level_indicator}")
                    
                    # Extract game info
                    game_date = "Unknown"
                    opponent_name = None
                    opponent_full_name = None
                    opponent_url = None
                    score1 = None
                    score2 = None
                    
                    # Find date
                    try:
                        date_elements = driver.find_elements(By.CSS_SELECTOR, 
                            "[class*='date'], [class*='Date'], time")
                        for elem in date_elements:
                            text = elem.text.strip()
                            if text and (SEASON_YEAR in text or "25" in text or "/" in text):
                                game_date = text
                                break
                    except:
                        pass
                    
                    # Find both teams on game page
                    team_links_on_game = driver.find_elements(By.CSS_SELECTOR, "a[href*='/team/']")
                    
                    for tlink in team_links_on_game:
                        try:
                            opp_href = tlink.get_attribute("href")
                            opp_text = tlink.text.strip()
                            opp_id = extract_team_id(opp_href)
                            
                            # Skip if this is the host team
                            if opp_id == team_id:
                                continue
                            
                            if opp_href and opp_id and len(opp_text) > 2:
                                # Try to get full team name
                                opponent_full_name = extract_full_team_name(driver, tlink)
                                opponent_name = opponent_full_name if opponent_full_name else opp_text
                                opponent_url = opp_href
                                
                                # Normalize team name with level
                                opponent_name = normalize_team_name(opponent_name, game_level)
                                
                                # Add to queue (only varsity teams to avoid duplicate crawling)
                                if opp_id not in visited_team_ids and not is_sub_varsity:
                                    opp_games_url = opp_href.split("/games")[0] + "/games"
                                    if opp_games_url not in urls_to_visit:
                                        urls_to_visit.append(opp_games_url)
                                        print(f"      ➕ Queue: {opponent_name}")
                                
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
                    
                    # Save game data
                    if opponent_name:
                        # Normalize host name too
                        normalized_host = normalize_team_name(host_name, game_level)
                        
                        game_data = {
                            "Date": game_date,
                            "Level": game_level,
                            "Host": normalized_host,
                            "Opponent": opponent_name,
                            "Score1": score1 or "",
                            "Score2": score2 or "",
                            "GameLink": game_link,
                            "OpponentLink": opponent_url,
                            "OpponentID": extract_team_id(opponent_url)
                        }
                        
                        all_games.append(game_data)
                        games_this_team += 1
                        
                        score_display = f"{score1}-{score2}" if score1 and score2 else "N/A"
                        print(f"      ✅ {normalized_host} vs {opponent_name} ({score_display})")
                    else:
                        print(f"      ⚠️ Could not identify opponent")
                    
                    # Return to schedule
                    driver.back()
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    try:
                        driver.get(current_url)
                        time.sleep(2)
                    except:
                        pass
            
            print(f"\n📊 Summary:")
            print(f"   - Games logged this team: {games_this_team}")
            print(f"   - Total games collected: {len(all_games)}")
            print(f"   - Teams visited: {len(visited_team_ids)}")
            print(f"   - Queue size: {len(urls_to_visit)}")

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")

    finally:
        driver.quit()

    return all_games

if __name__ == "__main__":
    start_time = time.time()
    data = scrape_scorestream_snowball()
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"✅ SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"⏱️  Time elapsed: {elapsed/60:.1f} minutes")
    print(f"🏈 Total games: {len(data)}")
    print(f"🏫 Unique teams: {len(set([g['Host'] for g in data] + [g['Opponent'] for g in data]))}")
    
    # Count by level
    varsity_count = len([g for g in data if g['Level'] == 'Varsity'])
    jv_count = len([g for g in data if g['Level'] == 'JV'])
    other_count = len(data) - varsity_count - jv_count
    
    print(f"\n📊 Games by Level:")
    print(f"   - Varsity: {varsity_count}")
    print(f"   - JV: {jv_count}")
    print(f"   - Other: {other_count}")
    
    if data:
        output_file = f"scorestream_games_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["Date", "Level", "Host", "Opponent", "Score1", "Score2", 
                         "GameLink", "OpponentLink", "OpponentID"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"\n📁 Saved to: {output_file}")
        
        # Also create separate varsity-only file
        varsity_games = [g for g in data if g['Level'] == 'Varsity']
        if varsity_games:
            varsity_file = f"scorestream_varsity_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(varsity_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(varsity_games)
            print(f"📁 Varsity only: {varsity_file}")
    else:
        print("⚠️ No games scraped")
    
    print("\n✨ Done!")