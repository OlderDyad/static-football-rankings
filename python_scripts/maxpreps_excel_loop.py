import time
import random
import re
import csv
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

def scrape_maxpreps_schedule(url, allow_base_page=False):
    """
    Navigates to a MaxPreps schedule URL,
    scrapes the schedule table,
    returns a list of dicts or an empty list if none found.
    
    If allow_base_page=False, we consider a page with 0 games to be "no schedule found".
    If allow_base_page=True, 0 games might still be considered valid (some teams use base page).
    """
    chrome_options = Options()
    chrome_options = Options()
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--log-level=3")  # Suppress logs
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--headless=new")  # Runs Chrome in headless mode (no window)
    chrome_options.add_argument("--disable-dev-shm-usage")  # Prevents memory issues in some environments

    driver_path = r"C:\Users\demck\AppData\Local\SeleniumBasic\chromedriver.exe"
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.get(url)
    time.sleep(3)

    # Attempt to locate schedule rows
    rows = driver.find_elements(By.CSS_SELECTOR, "table.sc-a79a1df3-0 tbody tr")
    if not rows:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    schedule_data = []
    for row_el in rows:
        row_text = row_el.text.strip()
        # skip header row
        if ("Date" in row_text) and ("Opponent" in row_text):
            continue

        tds = row_el.find_elements(By.TAG_NAME, "td")
        if len(tds) < 3:
            continue

        date_text = tds[0].text.strip()
        opp_cell_text = tds[1].text.strip()

        # Opponent URL
        anchors = tds[1].find_elements(By.TAG_NAME, "a")
        opponent_url = ""
        if anchors:
            href = anchors[0].get_attribute("href")
            if href.startswith("/"):
                href = "https://www.maxpreps.com" + href
            opponent_url = href

        # Location
        loc_indicator = ""
        if "@" in opp_cell_text:
            loc_indicator = "@"
        elif "vs" in opp_cell_text:
            loc_indicator = "vs"

        cleaned_opp = opp_cell_text.replace("@", "").replace("vs", "").replace("*", "").strip()

        # Result
        result_text = tds[2].text.strip()
        wl_char = ""
        if result_text.startswith("W"):
            wl_char = "W"
        elif result_text.startswith("L"):
            wl_char = "L"

        score_text = "Upcoming"
        match = re.search(r"\b\d{1,3}-\d{1,3}\b", result_text)
        if match:
            score_text = match.group(0)

        # Build a row dict
        row_dict = {
            "Date": date_text,
            "Location": loc_indicator,
            "Opponent": cleaned_opp,
            "WL": wl_char,
            "Score": score_text,
            "OpponentURL": opponent_url,
            # We add the timestamp here:
            "ScrapedAt": datetime.now().isoformat()
        }
        schedule_data.append(row_dict)

    driver.quit()
    return schedule_data


def process_active(df, all_results):
    """
    df: DataFrame with columns [URL, TeamName, State] (some might be missing)
    all_results: master list to append each row's data
    """
    for idx, row in df.iterrows():
        # Basic check for missing columns
        missing_cols = [c for c in ["URL", "TeamName", "State"] if c not in row]
        if missing_cols:
            print(f"Row {idx} missing columns {missing_cols}. Skipping.")
            continue
        
        url = row["URL"]
        team_name = row["TeamName"]
        state_str = row["State"]
        
        # Validate URL
        if not isinstance(url, str) or not url.startswith("http"):
            print(f"Row {idx}: invalid URL => {url}")
            all_results.append({
                "TeamName": team_name,
                "State": state_str,
                "URL": url,
                "Status": "Invalid URL"
            })
            continue

        print(f"Scraping row {idx}: {team_name} => {url}")
        try:
            games = scrape_maxpreps_schedule(url)

            if len(games) == 0:
                # Distinguish between "base page" vs "missing schedule"
                # If the URL doesn't end with "/schedule/", we can assume it's a base page
                if not url.endswith("/schedule/"):
                    status_str = "No schedule found (base team page?)"
                else:
                    status_str = "No schedule rows found"
                
                print(f"  Found 0 games => {status_str}")
                all_results.append({
                    "TeamName": team_name,
                    "State": state_str,
                    "URL": url,
                    "Status": status_str
                })
            else:
                print(f"  Found {len(games)} games")
                for g in games:
                    g["TeamName"] = team_name
                    g["State"] = state_str
                    g["URL"] = url
                    g["Status"] = "Processed"
                    all_results.append(g)

        except Exception as e:
            print(f"  Error scraping {url}: {e}")
            all_results.append({
                "TeamName": team_name,
                "State": state_str,
                "URL": url,
                "Status": f"Error: {str(e)}"
            })

        # optional random delay 2-4 seconds
        time.sleep(random.uniform(2, 4))


if __name__ == "__main__":
    excel_path = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\MaxPreps_Export.xlsx"
    
    df_active = pd.read_excel(excel_path, sheet_name="Active")
    
    all_results = []
    process_active(df_active, all_results)

    out_csv = "all_schedules.csv"
    fieldnames = [
        "TeamName", "State", "URL",
        "Date", "Location", "Opponent", "WL", "Score", "OpponentURL",
        "ScrapedAt",  # new timestamp column
        "Status"
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nDone! Wrote {len(all_results)} rows to {out_csv}")


