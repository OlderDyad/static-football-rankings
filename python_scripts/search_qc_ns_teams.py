"""
Search ScoreStream for Quebec and Nova Scotia teams from database
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pyodbc

# Teams to search for
QC_NS_TEAMS = [
    # Nova Scotia
    ("Antigonish Dr. J. H. Gillis", "NS"),
    ("Auburn West Kings", "NS"),
    ("Bedford Charles P. Allen", "NS"),
    ("Canning Northeast Kings", "NS"),
    ("Central Kings", "NS"),
    ("Cobequid Ed. Centre", "NS"),
    ("Dartmouth", "NS"),
    ("Dartmouth Cole Harbour", "NS"),
    ("Dartmouth Prince Andrew", "NS"),
    ("Fall River Lockview", "NS"),
    ("Halifax Auburn Drive", "NS"),
    ("Halifax Citadel", "NS"),
    ("Halifax J.L. Ilsley", "NS"),
    ("Halifax Queen Elizabeth", "NS"),
    ("Halifax St. Patrick's", "NS"),
    ("Halifax West", "NS"),
    ("Millwood", "NS"),
    ("Sackville", "NS"),
    ("Sydney", "NS"),
    ("Sydney Academy", "NS"),
    ("Truro Cobequid", "NS"),
    ("Upper Tantallon Sir John A. MacDonald", "NS"),
    ("Windsor Avon View", "NS"),
    ("Wolfville Horton", "NS"),
    # Quebec
    ("Cowansville Massey Vanier", "QC"),
    ("Hull Philemon Wright Regional", "QC"),  # We already have this one!
    ("Laval Liberty", "QC"),
    ("Le Vieux-Longueuil École secondaire Jacques-Rousseau", "QC"),
    ("Montreal College Jean-Eudes", "QC"),
    ("Montreal College Mont-Saint-Louis", "QC"),
    ("Montreal Lakeside Academy", "QC"),
    ("Quebec Externat Saint-Jean-Eudes", "QC"),
    ("Quebec Petit Seminaire de Quebec", "QC"),
    ("Terrebonne Ecole Armand-Corbeil", "QC"),
]

def search_scorestream(driver, team_name, state):
    """Search ScoreStream for a team and return URL if found"""
    try:
        # Clean up team name for search
        search_name = team_name.replace("(NS)", "").replace("(QC)", "").strip()
        search_query = f"{search_name} {state} football"
        search_url = f"https://scorestream.com/search?q={search_query.replace(' ', '+')}"
        
        print(f"  Searching: {search_name}")
        driver.get(search_url)
        time.sleep(3)
        
        # Look for team links in search results
        team_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/team/']")
        
        for link in team_links:
            href = link.get_attribute("href")
            text = link.text.strip().lower()
            
            # Check if this looks like our team
            team_words = search_name.lower().split()
            matches = sum(1 for word in team_words if word in text)
            
            if matches >= 2 and "/team/" in href:  # At least 2 words match
                print(f"    ✅ Found: {href}")
                return href
        
        print(f"    ❌ Not found")
        return None
        
    except Exception as e:
        print(f"    ⚠️ Error: {e}")
        return None

def main():
    print("="*70)
    print("🔍 SCORESTREAM SEARCH FOR QC/NS TEAMS")
    print("="*70)
    print(f"Searching for {len(QC_NS_TEAMS)} teams...")
    print("This will take ~5 minutes")
    print("="*70)
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(20)
    
    found_teams = []
    not_found = []
    
    try:
        for team_name, state in QC_NS_TEAMS:
            url = search_scorestream(driver, team_name, state)
            if url:
                found_teams.append((team_name, state, url))
            else:
                not_found.append((team_name, state))
            
            time.sleep(2)  # Be nice to ScoreStream
        
    finally:
        driver.quit()
    
    print("\n" + "="*70)
    print(f"✅ FOUND: {len(found_teams)} teams")
    print("="*70)
    
    if found_teams:
        with open('qc_ns_seeds.txt', 'w', encoding='utf-8') as f:
            f.write("# Quebec and Nova Scotia team URLs from database\n\n")
            for team_name, state, url in found_teams:
                f.write(f"# {team_name} ({state})\n")
                f.write(f"{url}\n\n")
        
        print("\nFound teams:")
        for team_name, state, url in found_teams:
            print(f"  {team_name} ({state})")
        
        print(f"\n📁 Saved to: qc_ns_seeds.txt")
        print(f"\nTo scrape these teams:")
        print(f"  python run_opponent_batch.py  (after updating to use qc_ns_seeds.txt)")
    
    print(f"\n❌ NOT FOUND: {len(not_found)} teams")
    if not_found:
        print("\nNot on ScoreStream:")
        for team_name, state in not_found[:10]:
            print(f"  {team_name} ({state})")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")
    
    print("\n✨ Search complete!")

if __name__ == "__main__":
    main()