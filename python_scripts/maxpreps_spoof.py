import time
import re
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

def scrape_maxpreps_schedule(url):
    chrome_options = Options()
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument("--start-minimized")  # Tells Chrome to start minimized

chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

driver_path = r"C:\Users\demck\AppData\Local\SeleniumBasic\chromedriver.exe"
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Immediately minimize the window:
driver.minimize_window()
    
    driver.get(url)
    time.sleep(3)

    # First attempt a narrow table CSS
    rows = driver.find_elements(By.CSS_SELECTOR, "table.sc-a79a1df3-0 tbody tr")
    if not rows:
        # fallback if above fails
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    schedule_data = []

    for row_el in rows:
        row_text = row_el.text.strip()

        # Skip header row
        if ("Date" in row_text) and ("Opponent" in row_text):
            print("Skipping header row:", row_text)
            continue

        # Gather all <td>
        tds = row_el.find_elements(By.TAG_NAME, "td")
        if len(tds) < 3:
            continue

        # 1) Date
        date_text = tds[0].text.strip()

        # 2) Opponent cell => location + name + (URL in <a>)
        opp_cell_text = tds[1].text.strip()

        # Attempt to find <a> tag in tds[1]
        opponent_url = ""
        anchors = tds[1].find_elements(By.TAG_NAME, "a")
        if anchors:
            # Typically there's just one <a>
            href = anchors[0].get_attribute("href")
            if href.startswith("/"):
                # If it's a relative link, prepend the site domain
                href = "https://www.maxpreps.com" + href
            opponent_url = href

        # Determine location indicator (@ or vs)
        location_indicator = ""
        if "@" in opp_cell_text:
            location_indicator = "@"
        elif "vs" in opp_cell_text:
            location_indicator = "vs"

        # Clean out @, vs, asterisks
        cleaned_opp = opp_cell_text.replace("@", "").replace("vs", "").replace("*", "").strip()

        # 3) Result => tds[2]
        result_text = tds[2].text.strip()

        # W/L detection
        wl_char = ""
        if result_text.startswith("W"):
            wl_char = "W"
        elif result_text.startswith("L"):
            wl_char = "L"

        # Score detection
        score_text = "Upcoming"
        match = re.search(r"\b\d{1,3}-\d{1,3}\b", result_text)
        if match:
            score_text = match.group(0)

        # Add row dictionary
        schedule_data.append({
            "Date": date_text,
            "Location": location_indicator,
            "Opponent": cleaned_opp,
            "WL": wl_char,
            "Score": score_text,
            "OpponentURL": opponent_url
        })

    driver.quit()
    return schedule_data

if __name__ == "__main__":
    test_url = "https://www.maxpreps.com/ak/anchorage/bartlett-golden-bears/football/schedule/"
    data = scrape_maxpreps_schedule(test_url)

    print(f"\nScraped {len(data)} games:")
    for g in data:
        print(g)

    # Write CSV with the OpponentURL too
    out_csv = "bartlett_schedule.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Date", "Location", "Opponent", "WL", "Score", "OpponentURL"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"\nWrote {len(data)} rows to {out_csv}")



