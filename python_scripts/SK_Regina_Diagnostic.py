import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def diagnose_regina(url):
    print("Launching Chrome WebDriver...")
    chrome_options = Options()
    # Remove headless so you can see if the page loads correctly
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    print("Page loaded. Waiting 5 seconds for dynamic content...")
    time.sleep(5)

    print("\n--- DIAGNOSTIC RESULTS FOR REGINA ---")

    # 1. Check for Iframes (common in this region)
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Iframe Count: {len(iframes)}")
    for i, frame in enumerate(iframes):
        print(f"   Iframe {i+1} ID: '{frame.get_attribute('id')}' Name: '{frame.get_attribute('name')}'")

    # 2. Check for Standard Tables
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"Table Count: {len(tables)}")
    
    for i, table in enumerate(tables):
        rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"   Table {i+1} has {len(rows)} rows.")
        if len(rows) > 0:
            print(f"   -> First Row Text: {rows[0].text[:60]}...")

    # 3. Check for Date Text (to see if data is visible)
    # We search for "2025" or a month name to see where the schedule text lives
    print("Searching for schedule text (e.g., 'Oct', 'Sep')...")
    try:
        # Try finding an element containing "Sep" or "Oct"
        element = driver.find_element(By.XPATH, "//*[contains(text(), 'Sep') or contains(text(), 'Oct')]")
        print(f"   -> Found text inside tag: <{element.tag_name}>")
        print(f"   -> Parent tag: <{element.find_element(By.XPATH, '..').tag_name}>")
        print(f"   -> Element Text: {element.text[:50]}...")
    except:
        print("   -> Could not find standard date text on the page.")

    driver.quit()

if __name__ == "__main__":
    diagnose_regina("https://www.rhsaa.ca/Home/Football")