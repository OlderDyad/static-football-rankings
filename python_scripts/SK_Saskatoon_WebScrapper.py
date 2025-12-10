import time
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def scrape_saskatoon_schedule(url):
    print("Launching Chrome WebDriver...")
    
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    print("Page loaded.")
    time.sleep(2) 

    schedule_data = []
    
    try:
        # --- MANUAL FILTER SELECTION ---
        print("\n🔹 **Manually set filters on the webpage.**")
        print("👉 Select Season: '2025 Fall Season'")
        print("👉 Select Sport: 'Football'")
        print("👉 Select Team: 'All Teams' (if needed)")
        print("👉 Click 'Table View' or ensure the table is visible.")
        
        # Pause execution until user manually presses Enter
        input("\n⏳ Waiting for user... Press Enter AFTER the schedule table is visible on screen.")

        print("\n✅ User confirmed. Scraping table...")
        
        # --- SCRAPE TABLE ---
        # Look for standard table rows
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        print(f"Found {len(rows)} rows.")

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) < 6:
                continue

            # Col Mapping (based on your image): 
            # 0: Date | 1: Time | 2: Title | 3: Home | 4: Away | 5: Location
            date_text = tds[0].text.strip()
            home_raw = tds[3].text.strip()
            away_raw = tds[4].text.strip()
            location = tds[5].text.strip()

            # --- PARSE SCORES FROM NAMES ---
            # Format: "Team Name (Score)" -> Regex: r"(.*)\((\d+)\)"
            def extract_score(text):
                match = re.search(r"(.*)\s*\((\d+)\)", text)
                if match:
                    return match.group(1).strip(), match.group(2)
                return text.strip(), "0" # Default to 0 if no score found

            home_team, home_score = extract_score(home_raw)
            away_team, away_score = extract_score(away_raw)

            game_info = {
                "Date": date_text,
                "Home": home_team,
                "Home_Score": home_score,
                "Away": away_team,
                "Away_Score": away_score,
                "Location": location,
                "Source": "SSSAD_Saskatoon",
                "ScrapedAt": datetime.now().isoformat()
            }
            schedule_data.append(game_info)
            print(f"✅ Scraped: {home_team} vs {away_team}")

    except Exception as e:
        print(f"❌ Error scraping: {e}")

    finally:
        driver.quit()

    return schedule_data

if __name__ == "__main__":
    url = "https://sssad.net/schedule/"
    data = scrape_saskatoon_schedule(url)
    
    print(f"\nWriting {len(data)} rows to CSV...")
    with open("sk_saskatoon_schedules.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Date", "Home", "Home_Score", "Away", "Away_Score", "Location", "Source", "ScrapedAt"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print("Done.")