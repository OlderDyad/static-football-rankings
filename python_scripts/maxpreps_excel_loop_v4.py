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

def clean_text(text):
    """Generic cleaning: remove tabs/newlines and extra spaces"""
    if not isinstance(text, str):
        return ""
    text = text.replace('\t', ' ').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def clean_field(text, max_length=None):
    """Clean a field value and optionally truncate"""
    cleaned = clean_text(text)
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned

def clean_opponent_name(text, max_length=100):
    """Specific cleaning for opponent field"""
    text = text.replace("@", "").replace("vs", "").replace("*", "")
    text = clean_text(text)
    if len(text) > max_length:
        text = text[:max_length]
    return text

def clean_date(date_text):
    """Clean and validate date format"""
    if not date_text:
        return ""
    
    cleaned = clean_text(date_text)
    # Remove any non-digit/slash characters
    cleaned = re.sub(r'[^\d/]', '', cleaned)
    
    # Match common date patterns
    patterns = [
        (r'^(\d{1,2})/(\d{1,2})$', lambda m: f"{int(m.group(1))}/{int(m.group(2))}"),
        (r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', lambda m: f"{int(m.group(1))}/{int(m.group(2))}")
    ]
    
    for pattern, formatter in patterns:
        match = re.match(pattern, cleaned)
        if match:
            return formatter(match)
    
    return ""

def scrape_maxpreps_schedule(url, allow_base_page=False):
    """Scrape schedule from MaxPreps URL"""
    chrome_options = Options()
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver_path = r"C:\Users\demck\AppData\Local\SeleniumBasic\chromedriver.exe"
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)  # Wait up to 10 seconds for elements
    
    driver.get(url)
    time.sleep(3)

    rows = driver.find_elements(By.CSS_SELECTOR, "table.sc-a79a1df3-0 tbody tr")
    if not rows:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    schedule_data = []
    for row_el in rows:
        row_text = clean_text(row_el.text)
        if ("Date" in row_text) and ("Opponent" in row_text):
            continue

        tds = row_el.find_elements(By.TAG_NAME, "td")
        if len(tds) < 3:
            continue

        date_text = clean_date(tds[0].text)
        opp_cell_text = clean_text(tds[1].text)

        # Extract opponent URL
        anchors = tds[1].find_elements(By.TAG_NAME, "a")
        opponent_url = ""
        if anchors:
            href = anchors[0].get_attribute("href")
            if href.startswith("/"):
                href = "https://www.maxpreps.com" + href
            opponent_url = clean_text(href)

        # Location indicator
        loc_indicator = ""
        if "@" in opp_cell_text:
            loc_indicator = "@"
        elif "vs" in opp_cell_text:
            loc_indicator = "vs"

        cleaned_opp = clean_opponent_name(opp_cell_text)

        # Process result
        result_text = clean_text(tds[2].text)
        wl_char = ""
        if result_text.startswith("W"):
            wl_char = "W"
        elif result_text.startswith("L"):
            wl_char = "L"

        score_text = "Upcoming"
        match = re.search(r"\b\d{1,3}-\d{1,3}\b", result_text)
        if match:
            score_text = match.group(0)

        row_dict = {
            "Date": date_text,
            "Location": loc_indicator,
            "Opponent": cleaned_opp,
            "WL": wl_char,
            "Score": score_text,
            "OpponentURL": opponent_url,
            "ScrapedAt": datetime.now().isoformat()
        }
        schedule_data.append(row_dict)

    driver.quit()
    return schedule_data

def process_active(df, all_results):
    """Process active teams from the input DataFrame"""
    for idx, row in df.iterrows():
        missing_cols = [c for c in ["URL", "TeamName", "State"] if c not in row]
        if missing_cols:
            print(f"Row {idx} missing columns {missing_cols}. Skipping.")
            continue
        
        url = row["URL"]
        team_name = row["TeamName"]
        state_str = row["State"]
        
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
                status_str = "No schedule found (base team page?)" if not url.endswith("/schedule/") else "No schedule rows found"
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
                    g["TeamName"] = clean_field(team_name, 200)
                    g["State"] = clean_field(state_str, 10)
                    g["URL"] = clean_field(url, 500)
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

        time.sleep(random.uniform(2, 4))

if __name__ == "__main__":
    excel_path = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\MaxPreps_Export.xlsx"
    out_csv = "all_schedules_v4.csv"
    
    df_active = pd.read_excel(excel_path, sheet_name="Active")
    
    all_results = []
    process_active(df_active, all_results)

    fieldnames = [
        "TeamName", "State", "URL",
        "Date", "Location", "Opponent", "WL", "Score", "OpponentURL",
        "ScrapedAt", "Status"
    ]
    
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, 
                              lineterminator="\n", 
                              quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nDone! Wrote {len(all_results)} rows to {out_csv}")