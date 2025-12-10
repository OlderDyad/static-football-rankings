"""
Quick test to verify Selenium/Chrome is working
"""

print("Testing Selenium setup...\n")

try:
    print("1. Importing modules...")
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    print("   ✅ Imports successful")
    
    print("\n2. Setting up Chrome options...")
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    print("   ✅ Options configured")
    
    print("\n3. Installing/finding ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    print("   ✅ ChromeDriver ready")
    
    print("\n4. Starting Chrome browser...")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("   ✅ Browser started")
    
    print("\n5. Testing navigation...")
    driver.get("https://scorestream.com")
    print(f"   ✅ Loaded: {driver.title}")
    
    print("\n6. Testing specific team page...")
    test_url = "https://scorestream.com/team/philemon-wright-high-school-falcons-291529/games"
    driver.get(test_url)
    print(f"   ✅ Loaded: {driver.title}")
    
    import time
    time.sleep(3)
    
    print("\n7. Checking for content...")
    from selenium.webdriver.common.by import By
    
    # Try to find body content
    body = driver.find_element(By.TAG_NAME, "body")
    body_text = body.text[:200]
    print(f"   ✅ Body text (first 200 chars): {body_text}")
    
    # Try to find links
    links = driver.find_elements(By.TAG_NAME, "a")
    print(f"   ✅ Found {len(links)} links on page")
    
    # Try to find game links
    game_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
    print(f"   ✅ Found {len(game_links)} game links")
    
    if game_links:
        print(f"   Sample game link: {game_links[0].get_attribute('href')}")
    
    print("\n✅ ALL TESTS PASSED!")
    print("\nSelenium is working correctly. The scraper should work.")
    
    input("\nPress Enter to close browser...")
    driver.quit()
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    
    if 'driver' in locals():
        try:
            driver.quit()
        except:
            pass
