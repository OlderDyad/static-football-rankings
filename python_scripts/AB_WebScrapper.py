import time
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def scrape_ab_schedule(url):
    print("Launching Chrome WebDriver...")
    
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    print("Page loaded. Waiting 5 seconds...")
    time.sleep(5) 

    schedule_data = []
    
    try:
        # Find the main table rows
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        print(f"Found {len(rows)} rows in the table.")

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            
            # Skip headers/spacers (rows with fewer than 6 columns)
            if len(tds) < 6:
                continue
            
            # Extract text
            # 0: Date | 1: League | 2: Home | 3: Score | 4: Away | 5: Score
            date_text = tds[0].text.strip()
            league = tds[1].text.strip()
            home_team = tds[2].text.strip()
            home_score = tds[3].text.strip()
            away_team = tds[4].text.strip()
            away_score = tds[5].text.strip()

            # --- NEW FILTERS ---
            # 1. Skip if Home OR Away team is empty
            if not home_team or not away_team:
                continue

            # 2. Skip if "Date" header or "WEEK" divider
            if "date" in date_text.lower() or "week" in date_text.lower():
                continue

            # 3. Skip if "PRE-SEASON" or similar headers appear in the date column
            if "season" in date_text.lower():
                continue

            game_info = {
                "Date": date_text,
                "League": league,
                "Home": home_team,
                "Home_Score": home_score,
                "Away": away_team,
                "Away_Score": away_score,
                "Source": "www.footballalberta.ab.ca",
                "ScrapedAt": datetime.now().isoformat()
            }
            
            schedule_data.append(game_info)
            print(f"✅ Scraped: {home_team} vs {away_team} ({date_text})")

    except Exception as e:
        print(f"❌ Error scraping: {e}")

    finally:
        driver.quit()

    return schedule_data

if __name__ == "__main__":
    url = "https://www.footballalberta.ab.ca/content/span-stylecolor-0000ffhigh-school-schedule-span"
    data = scrape_ab_schedule(url)
    
    print(f"\nWriting {len(data)} rows to CSV...")
    with open("ab_schedules.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Date", "League", "Home", "Home_Score", "Away", "Away_Score", "Source", "ScrapedAt"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print("Done.")