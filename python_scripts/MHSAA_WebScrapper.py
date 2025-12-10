import time
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def scrape_mhsaa_schedule(url):
    print("Launching Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Use ChromeDriverManager to automatically install the matching driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    print("Page loaded successfully!")
    time.sleep(3)

    schedule_data = []
    current_date_header = None  # Stores the last seen "Header Date" (e.g., "OCTOBER 3")

    try:
        print("\n🔹 **Manually set all filters on the webpage.**")
        print("👉 Set Sport, Start Date, End Date, Level, etc.")
        print("👉 Click the 'Search' button **manually**.")
        print("👉 After clicking search, return here and press `Enter` to continue scraping.")

        # Pause execution until user manually presses Enter
        input("\n⏳ Waiting for user... Press Enter AFTER setting filters and clicking search.")

        print("\n✅ User confirmed filters are set. Proceeding with scraping...")
        time.sleep(5) 

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        print(f"Total rows found: {len(rows)}")

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            
            # --- SCENARIO 1: It's a Date Header Row (e.g., "OCTOBER 3") ---
            # These rows usually have fewer columns or special classes
            if len(tds) <= 1 or "date-header" in row.get_attribute("class"):
                header_text = row.text.strip()
                # Basic check: if it has a digit, treat it as a date header
                if any(char.isdigit() for char in header_text):
                    current_date_header = header_text
                    print(f"📅 Found Date Header: {current_date_header}")
                continue # Skip to next row, don't try to parse as a game

            # --- SCENARIO 2: It's a Game Row ---
            # We need at least 6 columns now due to the new Icon column
            if len(tds) < 6:
                continue 

            try:
                # NEW COLUMN MAPPING (Shifted +1 because of Icon at index 0)
                # td[0] is the Green Icon -> SKIP IT
                sport = tds[1].text.strip()      # Was 0
                home_team = tds[2].text.strip()  # Was 1
                away_team = tds[3].text.strip()  # Was 2
                date_time_col = tds[4].text.strip() # Was 3
                
                # Handling Score (It might be in col 5 or 6 depending on layout, usually 5 now)
                score = ""
                if len(tds) > 5:
                    score = tds[5].text.strip()

                # --- DATE LOGIC ---
                # 1. Use the specific row time/date if available
                final_date = date_time_col
                
                # 2. If the row only has time (no slash) and we have a header, combine them
                if "/" not in date_time_col and current_date_header:
                    final_date = f"{current_date_header} - {date_time_col}"
                
                # 3. If the row date is empty but we have a header, use the header
                elif not date_time_col and current_date_header:
                    final_date = current_date_header

                game_info = {
                    "Sport": sport,
                    "Home": home_team,
                    "Away": away_team,
                    "Date/Time": final_date,
                    "Score": score,
                    "Status": "Processed",
                    "ScrapedAt": datetime.now().isoformat()
                }

                print(f"✅ Scraped: {home_team} vs {away_team} ({final_date})")
                schedule_data.append(game_info)

            except Exception as e:
                print(f"❌ Error processing row: {e}")

    except Exception as e:
        print(f"❌ Error scraping schedule: {e}")

    finally:
        driver.quit()

    return schedule_data


if __name__ == "__main__":
    mhsaa_url = "https://www.mhsaa.com/scores"
    scraped_games = scrape_mhsaa_schedule(mhsaa_url)

    out_csv = "mhsaa_schedules.csv"
    fieldnames = ["Sport", "Home", "Away", "Date/Time", "Score", "Status", "ScrapedAt"]

    # Prompt user to append or overwrite the CSV file
    mode = input("Do you want to append to the existing CSV file (a) or overwrite it (w)? [a/w]: ").strip().lower()
    if mode not in ['a', 'w']:
        print("Invalid input. Defaulting to append mode.")
        mode = 'a'
    
    print(f"\nWriting {len(scraped_games)} rows to CSV file...")
    with open(out_csv, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader() 
        writer.writerows(scraped_games)

    print(f"\n🎉 Done! Wrote {len(scraped_games)} rows to {out_csv}")











