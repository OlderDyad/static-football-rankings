# debug_opponent_extraction.py
# Quick debug script to see exactly what's in the opponent cells

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def debug_opponent_cells(driver, url):
    print(f"\nDebugging opponent cells for: {url}")
    driver.get(url)
    time.sleep(5)
    
    try:
        # Find tables
        tables = driver.find_elements(By.CSS_SELECTOR, 'table')
        print(f"Found {len(tables)} tables")
        
        for table_num, table in enumerate(tables):
            print(f"\n--- TABLE {table_num} ---")
            rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # Skip header
            
            for i, row in enumerate(rows[:3]):  # First 3 rows only
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) >= 2:
                    opponent_cell = cells[1]
                    
                    print(f"\nRow {i}:")
                    print(f"  Raw text: '{opponent_cell.text}'")
                    print(f"  Text repr: {repr(opponent_cell.text)}")
                    
                    # Try to find links
                    links = opponent_cell.find_elements(By.TAG_NAME, 'a')
                    for j, link in enumerate(links):
                        link_text = link.text
                        link_href = link.get_attribute('href')
                        print(f"  Link {j}: '{link_text}' -> {link_href}")
                    
                    # Show inner HTML for structure
                    inner_html = opponent_cell.get_attribute('innerHTML')
                    print(f"  Inner HTML: {inner_html[:200]}...")
                    
    except Exception as e:
        print(f"Error: {e}")

def main():
    driver = setup_driver()
    
    try:
        # Test with the Abernathy URL that has the "vs" issue
        test_url = "https://www.maxpreps.com/tx/abernathy/abernathy-antelopes/football/schedule/"
        debug_opponent_cells(driver, test_url)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()