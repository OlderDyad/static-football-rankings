🏈 Master Football Data Workflow (2025 Edition)
Goal: Scrape, clean, and import high school football scores for Michigan (MI), British Columbia (BC), Alberta (AB), and Saskatchewan (SK).

1. Michigan (MHSAA)
Script: python MHSAA_WebScrapper.py (Interactive Mode: select filters manually, then press Enter).

Generate: python Generate_SQL_MHSAA_Import.py.

Result: Import_MHSAA_Clean.sql -> Run in SSMS.

2. British Columbia (BC)
Source: bchighschoolfootball.com

Script: python BC_WebScrapper.py.

Note: Uses "Visual Position" logic (matches dates by Y-coordinate). Auto-clicks cookies.

Generate: python Generate_SQL_BC_Import.py.

Result: Import_BC_Clean.sql -> Run in SSMS.

3. Alberta (AB)
Source: footballalberta.ab.ca

Script: python AB_WebScrapper.py.

Generate: python Generate_SQL_AB_Import.py.

Note: Filters out "WEEK" headers and handles "DNP".

Result: Import_AB_Clean.sql -> Run in SSMS.

4. Saskatchewan (SK)
Strategy: Manual Copy-Paste (due to complex site structures).

Part A: Saskatoon (SSSAD)
Go to sssad.net/schedule/. Select Football > Table View.

Copy table -> Paste into sk_saskatoon_schedules.csv.

Generate: python Generate_SQL_SK_Saskatoon.py.

Note: Script extracts scores from names like Cent (38).

Result: Import_SK_Saskatoon.sql -> Run in SSMS.

Part B: Regina (RHSAA)
Go to rhsaa.ca/Home/Football.

Copy Schedule table -> Paste into sk_regina_schedules.csv.

Generate: python Generate_SQL_SK_Regina.py.

Result: Import_SK_Regina.sql -> Run in SSMS.

Part C: Provincial Finals
Check shsaa.ca for the Provincial Final scores (Nov 7-8).

If missing, manually insert them using SQL (e.g., Holy Cross vs Miller).

Common Fixes:

Null Margins: UPDATE HS_Scores SET Margin = Home_Score - Visitor_Score WHERE Margin IS NULL;

Double Suffixes: UPDATE HS_Scores SET Home = REPLACE(Home, '(SK) (AB)', '(SK)') ...

Bad Scores (0-0): Delete rows (DELETE FROM HS_Scores WHERE Source='...') and re-import.

5. Manitoba (MB)
Source: whsfl.ca/whsfl/Scores

Strategy: Manual Copy-Paste (due to messy text formatting).

Process:

Copy the "Scores" table from the website.

Paste into mb_schedules.csv.

Run: python Generate_SQL_MB_Import.py.

Key Fixes: This script uses "Nuclear Cleanup" to remove wide spacing (e.g., W e s t) and hidden characters (ÿ). It also auto-detects "JV" teams and adds the (MB) suffix.

Result: Import_MB_Clean.sql -> Run in SSMS.

6. New Brunswick (NB)
Source: gridironnewbrunswick.org

Strategy: Manual Copy-Paste (headers included).

Process:

Copy the schedule table (ensure headers Date, Away Team, Home Team... are included).

Paste into nb_schedules.csv.

Run: python Generate_SQL_NB_Import.py.

Key Fixes: Script uses "Nuclear Cleanup" to strip ÿ characters and splits team names from scores (e.g., Titans52 -> Titans, 52). Maps "Home Team" and "Away Team" columns correctly.

Result: Import_NB_Clean.sql -> Run in SSMS.

We have now conquered: Michigan (MI), British Columbia (BC), Alberta (AB), Saskatchewan (SK), Manitoba (MB), and New Brunswick (NB).
==================================================================================

Quebec/Ontario/Nova Scotia

ScoreStream Canadian Football Scraper - Complete Guide
🎯 Overview
This toolkit scrapes Canadian high school football data from ScoreStream with:

✅ Geographic filtering - Only ON, QC, NS teams
✅ Date extraction - Properly parses "Oct 18 '18" format
✅ Season filtering - Only 2024-2025 seasons
✅ JV detection - Identifies and labels JV vs Varsity
✅ Batch control - Process 50 teams at a time
✅ Progress tracking - Resume anytime
✅ Regional monitoring - Stop before drifting to Florida


📁 Files
Core Scripts

scorestream_batch_scraper.py - Main scraper with filtering
batch_controller.py - Interactive batch management
reseed_scraper.py - Generate seed URLs for missing teams

Helper Scripts (from previous)

analyze_scorestream_data.py - Analyze scraped data
prepare_sql_import.py - Format for SQL Server


🚀 Quick Start - Basic Workflow
Step 1: First Batch (50 teams)
bashpython scorestream_batch_scraper.py
What it does:

Starts with Philemon Wright HS (Quebec)
Scrapes their games
Finds Ontario/Quebec opponents
Adds them to queue
Stops after 50 teams
Saves progress to scraper_progress.csv
Saves queue to scraper_queue.csv
Creates scorestream_batch_TIMESTAMP.csv

Output Example:
🕷️  TEAM 1/50
ID: 291529 | URL: https://...philemon-wright...
✅ IN TARGET REGION: QC
🏠 Team: Philemon Wright Falcons
📋 Found 4 games
   [1] Game...
       ✅ Oct 18, 2024: vs Immaculata (ON) (13-29)
   [2] Game...
       ✅ Sep 15, 2024: vs Ashbury College (ON) (34-20)
   
📊 Team Summary: 4 games logged
📈 Batch Progress: 1/50 teams
📋 Queue: 3 teams waiting
Step 2: Review Results
bashpython analyze_scorestream_data.py scorestream_batch_TIMESTAMP.csv
Check:

Are dates extracted correctly?
Is it staying in target regions (ON, QC, NS)?
Are team names formatted well?
Any Florida teams appearing yet?

Step 3: Continue or Reseed
Option A: Continue from Queue
bashpython scorestream_batch_scraper.py
# It automatically resumes from scraper_queue.csv
Option B: Use Batch Controller (Recommended)
bashpython batch_controller.py
Interactive mode - asks after each batch if you want to continue.
Option C: Reseed from Database
bash# Get missing teams from your HS_Team_Names table
python reseed_scraper.py db

# Or use unvisited opponents
python reseed_scraper.py opponents

🎮 Using Batch Controller (Alternative Method)
The batch controller provides an interactive way to manage batches, but requires manual reseeding between sessions:
bashpython batch_controller.py
It will:

Show current progress
Run a batch of 50 teams
Show updated statistics
Ask: "Continue with next batch? (y/n/stats)"

⚠️ Known Limitation: The queue file may not persist correctly between runs.
Recommended workflow:

Run batch_controller for one batch
Use python reseed_scraper.py opponents before next batch
Run scraper with opponent seeds
Repeat

Or just use the direct method:
bash# Batch 1
python scorestream_batch_scraper.py

# Reseed
python reseed_scraper.py opponents

# Batch 2 with seeds
python -c "
from scorestream_batch_scraper import scrape_scorestream_batch
with open('opponent_seeds.txt', 'r') as f:
    seeds = [l.strip() for l in f if l.strip() and l.startswith('http')]
scrape_scorestream_batch(start_urls=seeds)
"

# Repeat...

📊 Managing Regional Drift
Detecting Drift
Watch for these signs:
🗺️  Games by Region:
   ON: 502
   QC: 116
   FL: 10  ⚠️ 
   TX: 5   ⚠️
Handling Drift
When you see US states appearing:
1. Don't panic - US teams playing Canadian schools are valuable cross-reference data. Your duplicate detection will handle any overlaps.
2. Use reseed between batches (RECOMMENDED):
bash# After each batch, reseed from unvisited opponents
python reseed_scraper.py opponents

# This finds Canadian opponents from your scraped data
# Creates opponent_seeds.txt

# Run next batch with those seeds
python -c "
from scorestream_batch_scraper import scrape_scorestream_batch
with open('opponent_seeds.txt', 'r') as f:
    seeds = [line.strip() for line in f if line.strip() and line.startswith('http')]
games, queue = scrape_scorestream_batch(start_urls=seeds)
"
3. Check progress regularly:
bash# See what teams you've visited
type scraper_progress.csv

# Check stats
python analyze_scorestream_data.py scorestream_batch_TIMESTAMP.csv
⚠️ Important: Queue File Issues
The scraper_queue.csv file can sometimes get corrupted or overwritten. Don't rely on it for resuming! Instead:
✅ DO: Use python reseed_scraper.py opponents between batches
❌ DON'T: Assume the queue file will work for resuming
This ensures you always have a fresh, accurate list of teams to scrape next.

🌱 Reseeding Strategies
Strategy 1: Use Unvisited Opponents
bashpython reseed_scraper.py opponents
Finds Canadian opponents that were mentioned but not visited yet.
Strategy 2: Use Your Database
bashpython reseed_scraper.py db
Gets all Canadian teams from your HS_Team_Names table.
Strategy 3: Find Missing Teams
bashpython reseed_scraper.py missing
Compares database vs scraped to find gaps.
Strategy 4: Manual Seeds
Create seed_urls_verified.txt:
https://scorestream.com/team/st-matthew-high-school-tigers-292135/games
https://scorestream.com/team/colonel-by-secondary-school-cougars-298304/games
https://scorestream.com/team/st-josephs-high-school-291234/games
Then in Python:
pythonfrom scorestream_batch_scraper import scrape_scorestream_batch

with open('seed_urls_verified.txt', 'r') as f:
    seed_urls = [line.strip() for line in f if line.strip() and line.startswith('http')]

games, queue = scrape_scorestream_batch(start_urls=seed_urls)

📈 Progress Tracking
Files Created
scraper_progress.csv - Visited teams
csvTeamID,TeamName,State,GamesFound,Timestamp
291529,Philemon Wright Falcons,QC,4,2024-12-08 14:32:15
298303,Immaculata Saints,ON,10,2024-12-08 14:35:22
scraper_queue.csv - Remaining teams
csvURL,Timestamp
https://scorestream.com/team/ashbury-college-colts-279779/games,2024-12-08 14:32:15
https://scorestream.com/team/colonel-by-secondary-school-cougars-298304/games,2024-12-08 14:32:17
scorestream_batch_TIMESTAMP.csv - Scraped games
csvDate,Season,Level,Host,HostState,Opponent,OpponentState,Score1,Score2,GameLink,OpponentLink,OpponentID
2024-10-18,2024,Varsity,Philemon Wright Falcons (QC),QC,Immaculata (ON),ON,13,29,https://...,https://...,298303
Checking Progress
bash# How many teams visited?
wc -l scraper_progress.csv

# How many teams in queue?
wc -l scraper_queue.csv

# How many games total?
wc -l scorestream_batch_*.csv

# What regions?
python analyze_scorestream_data.py scorestream_batch_TIMESTAMP.csv

🔧 Configuration
Adjust Batch Size
Edit scorestream_batch_scraper.py:
pythonMAX_TEAMS_PER_BATCH = 50  # Change to 25, 100, etc.
Change Target Regions
pythonTARGET_REGIONS = ['ON', 'QC', 'NS', 'NB']  # Add/remove provinces
Change Target Seasons
pythonTARGET_SEASONS = [2023, 2024, 2025]  # Add more years
Adjust Scraping Speed
pythontime.sleep(4)  # Increase to 5, 6 for slower/safer scraping

🛠️ Troubleshooting
Problem: No dates extracted
Solution: Date extraction improved in batch scraper. Look for:
pythondate_match = re.search(r"([A-Z][a-z]{2}\s+\d{1,2}\s*[',]\s*\d{2})", page_text)
Problem: Florida teams in queue
Solution: Stop scraper, clean queue, reseed with Canadian teams
Problem: "Unknown" states
Solution: Some teams don't show location clearly. The scraper skips these.
Problem: Duplicate games
Solution: Use analyze script to remove duplicates:
bashpython analyze_scorestream_data.py scorestream_batch_TIMESTAMP.csv
# Creates cleaned_all_levels.csv without duplicates
Problem: Scraper crashes
Solution: Progress is saved automatically. Just restart:
bashpython scorestream_batch_scraper.py  # Resumes from queue

📊 Final Data Processing
1. Merge All Batches
bashpython batch_controller.py
# Select 'y' when asked to merge at end

# Or manually:
python -c "
import pandas as pd
import glob

dfs = [pd.read_csv(f) for f in glob.glob('scorestream_batch_*.csv')]
merged = pd.concat(dfs, ignore_index=True)
merged.drop_duplicates(subset=['GameLink'], inplace=True)
merged.to_csv('scorestream_all_games.csv', index=False)
"
2. Clean and Analyze
bashpython analyze_scorestream_data.py scorestream_all_games.csv
# Creates: cleaned_all_levels.csv, cleaned_varsity.csv, cleaned_jv.csv
3. Prepare for SQL
bashpython prepare_sql_import.py cleaned_varsity.csv
# Creates: sql_import_teams.csv, sql_import_games.csv, import_scorestream_data.sql
4. Import to SQL Server
sql-- Run import_scorestream_data.sql in SSMS
-- Or use bulk insert commands provided

💡 Tips & Best Practices

Always reseed between batches: Don't rely on the queue file

bash   python reseed_scraper.py opponents  # After every batch

Backup your progress files regularly:

bash   copy scraper_progress.csv scraper_progress_backup_%date%.csv

Keep all data (including US teams): Your duplicate detection will handle overlaps, and US opponents provide valuable cross-reference data
Monitor progress with analyze script:

bash   python analyze_scorestream_data.py scorestream_batch_*.csv

Run batches of 50: Don't try to do everything at once. Take breaks between batches.
Check dates are parsing correctly: Spot-check a few games manually to ensure years are right
Use headless mode for speed: Already enabled by default (HEADLESS_MODE = True)
The reseed workflow is most reliable:

bash   # This is the most stable approach:
   1. Run batch → 2. Reseed → 3. Run with seeds → 4. Repeat

🎯 Complete Example Workflow (RECOMMENDED)
bash# Day 1: Initial scrape (50 teams)
del scraper_progress.csv scraper_queue.csv  # Start fresh
python scorestream_batch_scraper.py
python analyze_scorestream_data.py scorestream_batch_20241208_143022.csv

# Day 2: Reseed and continue (IMPORTANT: Don't rely on queue file)
python reseed_scraper.py opponents  # Finds unvisited opponents
# Creates opponent_seeds.txt with 100+ teams

# Run next batch with opponent seeds
python -c "
from scorestream_batch_scraper import scrape_scorestream_batch
with open('opponent_seeds.txt', 'r') as f:
    seeds = [line.strip() for line in f if line.strip() and line.startswith('http')]
games, queue = scrape_scorestream_batch(start_urls=seeds, resume=False)
"

# Day 3: Repeat reseed process
python reseed_scraper.py opponents  # Get next batch of unvisited
# Run batch with new seeds
# Repeat until you've covered all target teams

# Day 4: Check database for missing teams
python reseed_scraper.py missing  # Compare DB vs scraped
# Manually add any missing team URLs to seed file

# Day 5: Merge and import
# Merge all batch files
python -c "
import pandas as pd
import glob
dfs = [pd.read_csv(f) for f in glob.glob('scorestream_batch_*.csv')]
merged = pd.concat(dfs, ignore_index=True)
merged.drop_duplicates(subset=['GameLink'], inplace=True)
merged.to_csv('scorestream_all_games.csv', index=False)
print(f'Merged {len(merged)} games')
"

python analyze_scorestream_data.py scorestream_all_games.csv
python prepare_sql_import.py cleaned_varsity.csv
# Import to SQL Server via SSMS

📞 Summary
Recommended workflow (most reliable):

Initial batch: python scorestream_batch_scraper.py
Reseed: python reseed_scraper.py opponents
Next batch with seeds:

pythonpython -c "
from scorestream_batch_scraper import scrape_scorestream_batch
with open('opponent_seeds.txt', 'r') as f:
    seeds = [l.strip() for l in f if l.strip() and l.startswith('http')]
scrape_scorestream_batch(start_urls=seeds)
"

Repeat steps 2-3 until you've covered all target teams

Alternative: Batch controller (requires manual reseeding between sessions)
Key principles:

✅ Always reseed between batches (don't rely on queue file)
✅ Keep all data (US teams provide valuable cross-reference)
✅ Run in batches of 50 teams
✅ Monitor with analyze script
✅ Dates parsing correctly (full 4-digit years)
✅ States detecting from cities (Ottawa → ON, Gatineau → QC)

Files you'll use most:

scorestream_batch_scraper.py - Main scraper
reseed_scraper.py - Find next teams to scrape
analyze_scorestream_data.py - Check data quality

Good luck with your Canadian football data collection! 🏈🍁