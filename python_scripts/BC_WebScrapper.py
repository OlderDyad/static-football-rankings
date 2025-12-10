import time
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def scrape_bc_schedule(url):
    print("Launching Chrome WebDriver...")
    
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

   driver.get(url)
    print("Page loaded. Waiting 5 seconds...")
    time.sleep(5) 

    # --- NEW: Handle Cookie Popup ---
    try:
        # Look for a button that says "OK" or "Accept" or "I Agree"
        cookie_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'OK') or contains(text(), 'Accept')]")
        cookie_btn.click()
        print("🍪 Cookie popup dismissed.")
        time.sleep(1)
    except:
        print("No cookie popup found (or could not click).") 

    schedule_data = []
    
    try:
        # 1. Find all elements that look like Date Headers (Text contains "2025")
        # We search generically for any text block containing the year
        potential_headers = driver.find_elements(By.XPATH, "//*[contains(text(), '2025')]")
        
        date_map = []
        for header in potential_headers:
            text = header.text.strip()
            # Regex to confirm it's a date (Month + Year)
            if re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec).*2025', text, re.IGNORECASE):
                try:
                    loc = header.location['y'] # Get vertical position
                    # Avoid duplicates (sometimes the same text is found twice in nested tags)
                    if not any(d['y'] == loc for d in date_map):
                        date_map.append({'text': text, 'y': loc})
                        print(f"📍 Found Date Header at Y={loc}: '{text}'")
                except:
                    continue

        # Sort headers by position (top to bottom)
        date_map.sort(key=lambda x: x['y'])

        # 2. Find all Tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"Found {len(tables)} tables.")

        for i, table in enumerate(tables):
            try:
                table_y = table.location['y']
            except:
                continue
            
            # 3. Find the Date Header closest to (but above) this table
            closest_date = None
            for d in date_map:
                # If date is above the table (smaller Y value)
                if d['y'] < table_y:
                    closest_date = d['text']
                else:
                    break # We passed the table, stop checking
            
            if not closest_date:
                print(f"⚠️ Table {i+1} at Y={table_y} has no date above it. Skipping.")
                continue

            # Clean the date text (remove newlines if any)
            clean_date = closest_date.split('\n')[0].strip()
            print(f"✅ Table {i+1} matched to Date: {clean_date}")

            # 4. Scrape the Table Rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                tds = row.find_elements(By.TAG_NAME, "td")
                text = row.text.strip()
                
                # Skip headers
                if "Result" in text or "Filter" in text or len(tds) < 5:
                    continue

                try:
                    # Column Mapping
                    # td[1] = Away, td[2] = Away Score, td[3] = Home, td[4] = Home Score
                    away_raw = tds[1].text.strip().split('\n')[0]
                    a_score = tds[2].text.strip()
                    home_raw = tds[3].text.strip().split('\n')[0]
                    h_score = tds[4].text.strip()
                    location = tds[5].text.strip() if len(tds) > 5 else ""

                    game_info = {
                        "Date": clean_date,
                        "Away": away_raw,
                        "Away_Score": a_score,
                        "Home": home_raw,
                        "Home_Score": h_score,
                        "Location": location,
                        "Source": "BC_HS_Football",
                        "ScrapedAt": datetime.now().isoformat()
                    }
                    schedule_data.append(game_info)
                except Exception as e:
                    pass

    except Exception as e:
        print(f"❌ Error scraping: {e}")

    finally:
        driver.quit()

    return schedule_data

if __name__ == "__main__":
    url = "https://www.bchighschoolfootball.com/leagues/schedules.cfm?leagueID=6713&clientID=652"
    data = scrape_bc_schedule(url)
    
    print(f"\nWriting {len(data)} rows to CSV...")
    with open("bc_schedules.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Away", "Away_Score", "Home", "Home_Score", "Location", "Source", "ScrapedAt"])
        writer.writeheader()
        writer.writerows(data)
    print("Done.")