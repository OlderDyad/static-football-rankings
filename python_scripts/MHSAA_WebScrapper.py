import time
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_mhsaa_schedule(url):
    print("Launching Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver_path = r"C:\\Users\\demck\\AppData\\Local\\SeleniumBasic\\chromedriver.exe"
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    print("Page loaded successfully!")
    time.sleep(3)

    schedule_data = []  # ✅ Ensures it's initialized

    try:
        print("\n🔹 **Manually set all filters on the webpage.**")
        print("👉 Set Sport, Start Date, End Date, Level, etc.")
        print("👉 Click the 'Search' button **manually**.")
        print("👉 After clicking search, return here and press `Enter` to continue scraping.")

        # **Pause execution until user manually presses Enter**
        input("\n⏳ Waiting for user... Press Enter AFTER setting filters and clicking search.")

        print("\n✅ User confirmed filters are set. Proceeding with scraping...")
        time.sleep(5)  # Additional wait for results to load

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        print(f"Total rows found: {len(rows)}")

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) < 6:
                continue  # Skip rows that don't have enough data

            try:
                # Extract standard fields
                sport = tds[0].text.strip()
                home_team = tds[1].text.strip()
                away_team = tds[2].text.strip()
                date_time = tds[3].text.strip()

                # Handle Score Extraction
                try:
                    score_td = tds[5]  # Score is in the 6th <td>
                    score_span = score_td.find_element(By.TAG_NAME, "span")  # Get <span> inside <td>
                    score = score_span.text.strip()  # Extract only score text
                except:
                    score = ""  # If score is not found, leave it blank

                game_info = {
                    "Sport": sport,
                    "Home": home_team,
                    "Away": away_team,
                    "Date/Time": date_time,
                    "Score": score,  # Now correctly extracting score
                    "Status": "Processed",
                    "ScrapedAt": datetime.now().isoformat()
                }

                print(f"✅ Scraped row: {game_info}")
                schedule_data.append(game_info)

            except Exception as e:
                print(f"❌ Error processing row: {e}")

    except Exception as e:
        print(f"❌ Error scraping schedule: {e}")

    finally:
        driver.quit()

    return schedule_data  # ✅ Ensures function always returns a value


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
            writer.writeheader()  # Only write headers if overwriting
        writer.writerows(scraped_games)

    print(f"\n🎉 Done! Wrote {len(scraped_games)} rows to {out_csv}")












