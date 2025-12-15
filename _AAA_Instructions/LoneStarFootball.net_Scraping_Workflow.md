# LoneStarFootball.net Scraping Workflow
## Texas High School Football Historical Data (Pre-2004)

---
python lonestar_raw_collector.py

This workflow scrapes historical Texas high school football data from LoneStarFootball.net, focusing on pre-2004 seasons to fill gaps in your MaxPreps data. The system uses a two-phase approach similar to your Ontario/Quebec scrapers:

1. **Phase 1: Team Discovery** - Find all 1,500+ Texas teams
2. **Phase 2: Batch Scraping** - Scrape historical schedules in manageable batches

**Key Features:**
- ✅ Scrapes only pre-2004 seasons (1869-2003)
- ✅ Batch processing with progress tracking
- ✅ Database-backed queue system (resumable)
- ✅ Alias-based team name standardization
- ✅ Regional context for Texas teams

---

## 🎯 Scope

**Target:** 1,500+ Texas teams
**Seasons:** 1869-2003 (pre-MaxPreps era)
**Estimated Pages:** ~500,000+ (1,500 teams × ~50 seasons × 6 pages average)
**Strategy:** Batch processing with database checkpoints

---

## 🏗️ Architecture

### Database Tables

```
lonestar_teams              → Master list of all teams
lonestar_batches            → Batch tracking
lonestar_scraping_status    → Per-team progress
lonestar_games_raw          → Raw scraped data
lonestar_unmatched_games    → Teams needing aliases
HS_Team_Name_Alias          → Name standardization (shared)
```

### Scraper Design

```
Phase 1: Discovery
└── Visit search.asp
    └── Extract all team URLs
        └── Store in lonestar_teams

Phase 2: Scraping (Batches of 50)
└── For each team:
    ├── Visit team page
    ├── Find season links (1869-2003)
    ├── For each season:
    │   ├── Visit schedule page
    │   ├── Extract games
    │   └── Store in lonestar_games_raw
    └── Update scraping_status
```

---

## 🚀 Quick Start Guide

### Prerequisites

1. **Python Environment:**
```bash
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
.\..\.venv\Scripts\Activate
```

2. **Required Packages:**
```bash
pip install selenium pyodbc pandas
```

3. **SQL Server Setup:**
- Ensure hs_football_database is accessible
- Run table creation (automatic on first run)

### Step 1: Place Script

Save `lonestar_scraper.py` to:
```
C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\
```

### Step 2: Run Team Discovery (One-Time)

```bash
python lonestar_scraper.py
# Select: 1 (Discover all teams)
```

**What happens:**
- Scraper visits https://lonestarfootball.net/search.asp
- Extracts all team URLs (~1,500 teams)
- Stores in `lonestar_teams` table
- Takes ~5-10 minutes

**Output:**
```
Team discovery complete: 1,542 teams found
```

### Step 3: Run First Batch (50 Teams)

```bash
python lonestar_scraper.py
# Select: 2 (Scrape team schedules)
# Enter: 50 (teams per batch)
```

**What happens:**
- Creates Batch ID (e.g., Batch 1)
- Scrapes 50 teams' historical schedules (1869-2003)
- Stores raw games in `lonestar_games_raw`
- Takes ~30-60 minutes depending on team size
- **Progress is saved** - can resume if interrupted

**Output:**
```
Starting batch 1: 50 teams to process
[1/50] Processing: Abilene High (ID: 1001)
✓ Saved 345 games for Abilene High
[2/50] Processing: Alamo Heights (ID: 1002)
...
Batch 1 complete
```

### Step 4: Finalize Batch in SQL

Open **SQL Server Management Studio** and run:

```sql
EXEC dbo.FinalizeLoneStarData @BatchID = 1;
```

**What happens:**
- Standardizes team names via alias system
- Matches home/away teams
- Inserts completed games into HS_Scores
- Logs unmatched teams for alias creation

**Output:**
```
Processing LoneStar Batch: 1
Matched games: 3,245
Unmatched games: 156

UNMATCHED TEAMS REQUIRING ALIASES:
Raw Name           | Count | Region    | Standardized Name
Rockwall Heath     | 24    | LoneStar  | *** UPDATE ME ***
Lake Belton        | 18    | LoneStar  | *** UPDATE ME ***
```

### Step 5: Add Missing Aliases (If Needed)

If unmatched teams found, add aliases:

```sql
-- Find proper team names in your database
SELECT Team_Name 
FROM HS_Team_Names 
WHERE Team_Name LIKE '%Rockwall%' 
  AND State = 'TX';

-- Add aliases
INSERT INTO HS_Team_Name_Alias (Alias_Name, Standardized_Name, Newspaper_Region)
VALUES 
    ('Rockwall Heath', 'Rockwall-Heath (TX)', 'LoneStar'),
    ('Lake Belton', 'Belton Lake Belton (TX)', 'LoneStar'),
    ('FW Paschal', 'Fort Worth Paschal (TX)', 'LoneStar');

-- Re-run finalization
EXEC dbo.FinalizeLoneStarData @BatchID = 1;
```

**Repeat until:**
```
All games successfully imported! ✓
```

### Step 6: Continue with Next Batch

```bash
# The scraper automatically picks up where it left off
python lonestar_scraper.py
# Select: 3 (Scrape team schedules)
# Enter: 50
```

**Resume capability:**
- Scraper checks `lonestar_scraping_status` table
- Only processes teams marked 'pending' or 'failed'
- Never re-scrapes completed teams

---

## 📊 Monitoring Progress

### Check Overall Progress

```sql
-- How many teams completed?
SELECT 
    status,
    COUNT(*) as team_count,
    SUM(games_found) as total_games
FROM lonestar_scraping_status
GROUP BY status;

-- Output:
-- completed | 150  | 45,678
-- pending   | 1,392| 0
-- failed    | 0    | 0
```

### View Batch History

```sql
SELECT 
    batch_id,
    batch_name,
    created_date,
    completed_date,
    status
FROM lonestar_batches
ORDER BY batch_id DESC;
```

### Check Unmatched Teams

```sql
EXEC dbo.GetLoneStarUnmatchedSummary @BatchID = NULL;  -- All batches

-- OR specific batch:
EXEC dbo.GetLoneStarUnmatchedSummary @BatchID = 1;
```

---

## 🔧 Common Tasks

### Resume After Interruption

If scraper crashes or you stop it:

```bash
python lonestar_scraper.py
# Select: 2
# Enter: 50

# It automatically finds the running batch and resumes
```

### Process Failed Teams

```sql
-- Mark failed teams as pending to retry
UPDATE lonestar_scraping_status
SET status = 'pending',
    attempts = 0,
    error_message = NULL
WHERE status = 'failed';
```

Then run scraper again.

### Change Batch Size

Adjust based on your schedule:

```bash
python lonestar_scraper.py
# Select: 2
# Enter: 25   # Smaller batch (faster)
# OR
# Enter: 100  # Larger batch (fewer runs needed)
```

**Recommendation:** 50 teams = ~1 hour = manageable session

### Skip Team Discovery (If Already Done)

If you've already run discovery:

```bash
python lonestar_scraper.py
# Select: 2 (Go straight to scraping)
```

---

## ⚙️ Configuration Options

Edit `lonestar_scraper.py` to adjust:

```python
# Batch size
TEAMS_PER_BATCH = 50  # Change to 25, 100, etc.

# Season range
EARLIEST_SEASON = 1869
LATEST_SEASON = 2003  # Only scrape pre-2004

# Headless mode (no visible browser)
HEADLESS_MODE = True  # Change to False for debugging

# Delays (seconds)
WAIT_TIMEOUT = 15  # Page load timeout
```

---

## 🐛 Troubleshooting

### Problem: "No teams to scrape in this batch"

**Cause:** All teams already completed.

**Solution:** Check progress:
```sql
SELECT COUNT(*) 
FROM lonestar_teams 
WHERE team_id NOT IN (
    SELECT team_id 
    FROM lonestar_scraping_status 
    WHERE status = 'completed'
);
```

If 0, you're done! Otherwise, the scraper logic needs adjustment.

---

### Problem: Too many unmatched teams

**Cause:** Need to build up alias table for Texas teams.

**Solution:** Batch add aliases:

1. Export unmatched list:
```sql
SELECT DISTINCT opponent_name_raw, COUNT(*) as cnt
FROM lonestar_unmatched_games
GROUP BY opponent_name_raw
ORDER BY cnt DESC;
```

2. Use Excel to prepare aliases (match with HS_Team_Names)

3. Bulk insert:
```sql
INSERT INTO HS_Team_Name_Alias (Alias_Name, Standardized_Name, Newspaper_Region)
VALUES 
    ('Team1', 'Proper Name (TX)', 'LoneStar'),
    ('Team2', 'Proper Name (TX)', 'LoneStar'),
    ...
```

---

### Problem: Scraper too slow

**Cause:** Website rate limiting or network issues.

**Solution:** Increase delays:
```python
# In scraper code, find and increase:
time.sleep(random.uniform(5, 10))  # Change to (10, 20)
```

---

### Problem: Selenium crashes

**Cause:** ChromeDriver version mismatch or memory issues.

**Solution:**
1. Update ChromeDriver:
```bash
pip install --upgrade selenium
```

2. Add memory limit to Chrome options:
```python
chrome_options.add_argument("--max-memory-usage=2000")
```

---

## 📈 Estimated Timeline

Based on 1,500 teams:

| Batch Size | Batches Needed | Time Per Batch | Total Time |
|------------|----------------|----------------|------------|
| 25 teams   | 60 batches     | ~30 min        | ~30 hours  |
| 50 teams   | 30 batches     | ~60 min        | ~30 hours  |
| 100 teams  | 15 batches     | ~120 min       | ~30 hours  |

**Recommendation:** 
- Run in 50-team batches
- Schedule 1-2 batches per day
- Complete project in 2-3 weeks

---

## 🎓 Advanced Usage

### Run Full Automation

```bash
# Discover + scrape in one command
python lonestar_scraper.py
# Select: 3
```

**Warning:** This will run discovery then immediately start scraping. Ensure you have time for the full process.

---

### Custom Season Range

Edit configuration to scrape specific decades:

```python
# Only 1980s and 1990s
EARLIEST_SEASON = 1980
LATEST_SEASON = 1999
```

---

### Scrape Specific Teams Only

```sql
-- Create a custom batch for specific teams
INSERT INTO lonestar_batches (batch_name, total_teams, status)
VALUES ('Highland Park Focus', 10, 'running');

DECLARE @CustomBatchID INT = SCOPE_IDENTITY();

-- Add specific teams to this batch
INSERT INTO lonestar_scraping_status (team_id, batch_id, status)
SELECT team_id, @CustomBatchID, 'pending'
FROM lonestar_teams
WHERE team_name LIKE '%Highland Park%'
   OR team_name LIKE '%Rockwall%';
```

Then run scraper - it will pick up this custom batch.

---

## 📝 SQL Queries Reference

### Most Valuable Teams (Most Historical Games)

```sql
SELECT TOP 20
    lt.team_name,
    COUNT(DISTINCT r.season) as seasons_found,
    COUNT(*) as games_found
FROM lonestar_teams lt
JOIN lonestar_games_raw r ON lt.team_id = r.team_id
GROUP BY lt.team_name
ORDER BY COUNT(*) DESC;
```

### Seasons with Most Coverage

```sql
SELECT 
    season,
    COUNT(DISTINCT team_id) as teams_with_data,
    COUNT(*) as total_games
FROM lonestar_games_raw
GROUP BY season
ORDER BY season DESC;
```

### Identify Gaps in Coverage

```sql
-- Teams with no scraped data yet
SELECT 
    lt.team_id,
    lt.team_name,
    lt.team_url
FROM lonestar_teams lt
LEFT JOIN lonestar_games_raw r ON lt.team_id = r.team_id
WHERE r.team_id IS NULL;
```

---

## 🔄 Integration with Existing Workflow

### After LoneStar Import Complete

1. **Recalculate Rankings:**
```sql
EXEC [dbo].[CalculateRankings_v4_Optimized]
    @LeagueType = '1',
    @BeginSeason = 1869,
    @EndSeason = 2003,
    @Week = 52,
    @MaxLoops = 2048;
```

2. **Regenerate Website:**
```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts
.\run_update_cycle.ps1
```

3. **Verify Texas Teams:**
```sql
-- Check Texas team count in HS_Scores
SELECT 
    LEFT(Home, CHARINDEX('(', Home) - 1) as Team,
    COUNT(*) as Games,
    MIN(Season) as First_Season,
    MAX(Season) as Last_Season
FROM HS_Scores
WHERE Home LIKE '%(TX)%'
  AND Season < 2004
GROUP BY LEFT(Home, CHARINDEX('(', Home) - 1)
ORDER BY COUNT(*) DESC;
```

---

## 📊 Success Metrics

### Target Goals

- [ ] 1,500+ teams discovered
- [ ] 30+ batches completed
- [ ] 500,000+ historical games scraped
- [ ] <5% unmatched games (after aliases added)
- [ ] Pre-2004 Texas data 90%+ complete

### Quality Checks

```sql
-- Check for suspicious game counts (possible duplicates)
SELECT 
    Home, Season, COUNT(*) as game_count
FROM HS_Scores
WHERE Home LIKE '%(TX)%'
  AND Source LIKE 'LoneStar%'
GROUP BY Home, Season
HAVING COUNT(*) > 15  -- High school teams rarely play 15+ games
ORDER BY COUNT(*) DESC;

-- Check for impossible scores
SELECT * 
FROM HS_Scores
WHERE Source LIKE 'LoneStar%'
  AND (Home_Score > 100 OR Visitor_Score > 100);
```

---

## 🚧 Known Limitations

1. **Date Parsing:** LoneStar uses inconsistent date formats. Scraper attempts multiple parsing strategies but some dates may default to September 1st.

2. **Playoff Games:** Not always clearly marked. May need manual review.

3. **Neutral Site Games:** Difficult to detect automatically. Defaults to home team's location.

4. **Historical Team Names:** Teams that changed names over decades may appear as separate entries. Requires manual merge after scraping.

---

## 📞 Support

If you encounter issues:

1. Check `lonestar_scraper.log` file
2. Review SQL error messages
3. Verify ChromeDriver is up to date
4. Ensure network connectivity to lonestarfootball.net

---

## 🎯 Next Steps

After completing LoneStar scraping:

1. ✅ Texas pre-2004 data complete
2. 🔄 Consider other states with similar sites
3. 📊 Focus on filling remaining gaps via newspaper OCR
4. 🏆 Update national rankings with complete Texas data

---

*Last Updated: December 2025*

LoneStar Parser - Revised Strategy (Keep JV & College Games)
Philosophy: Flag, Don't Filter
Instead of removing JV and College games, we flag them so they can be:

Handled with separate parsing logic
Imported to different tables (HS_Scores_JV, HS_Scores_College)
Filtered in/out of rankings as needed
Preserved as valuable historical data


Updated Error Handling Strategy
Category 1: Compressed Score Parsing (HIGHEST PRIORITY)
~25% of current errors | Action: Fix parser logic
Problem Examples
7Caddo Mills8 13            → Scores: 8, 13 (not 7, 8)
3Dallas White3 21           → Scores: 3, 21 (both attached to teams)
PCelina3 21                 → Score 21 stuck to team
LAmarillo8 13               → Score 13 stuck to team
Amarillov103Pampad7         → Scores: 10, 7 (not 10, 3)
Solution
Enhanced detection logic:

Split compressed numbers: 103 → [10, 3]
Detect junk single-digits between scores
Clean digit suffixes from team names
Use position-based splitting

Expected Impact

Fixes 600+ games (25% of errors)
Reduces VLOOKUP errors from 6.5% to ~4.5%


Category 2: JV Games
~40% of current errors | Action: Flag with "JV_GAME" tag
Examples
nFarmersville JVy           → Flag as JV
*Plano JVy                  → Flag as JV
7Conroe JVy                 → Flag as JV
Implementation
pythonif 'JV' in team1_raw or 'JV' in team2_raw:
    notes = 'JV_GAME'
Workflow

Parser adds JV_GAME to notes column
Excel can filter: =IF(notes="JV_GAME", "SKIP", "KEEP")
SQL import can route to HS_Scores_JV table
Can be excluded from varsity rankings

Why Keep Them?

Historical record of program depth
Shows when programs had JV teams (program size indicator)
Useful for cross-referencing schedules
Some teams only have JV records in early years


Category 3: College/Prep Games
~8% of current errors | Action: Flag with "COLLEGE_GAME" tag
Examples
PThorp Springs Collegef     → Flag as College
mClarendon Collegev         → Flag as College
3Schreiner Prepy           → Flag as College
LTarleton College JVy       → Flag as College
Implementation
pythoncollege_keywords = ['College', 'University', 'Prep']
if any(keyword in combined for keyword in college_keywords):
    notes = 'COLLEGE_GAME'
Workflow
Same as JV games - flag, then handle separately.
Why Keep Them?

Important for early football history (1900-1930)
Shows strength of programs that could compete with colleges
Context for understanding regional football development
Can be useful for "mythical national championship" debates


Category 4: Neutral Site Markers
~5% of errors | Action: Strip @Location suffix
Examples
7Gorman @Decatury           → Clean to: 7Gorman
7Sonora @Sonorav            → Clean to: 7Sonora
Implementation
pythonteam_name = re.sub(r'\s*@[A-Za-z\s]+$', '', team_name)
Expected Impact

Fixes 120+ games (5% of errors)
Reduces VLOOKUP errors to ~4.0%


Category 5: Special Characters
~3% of errors | Action: Strip trailing $, #, etc.
Examples
TGunter$                    → Clean to: TGunter
LAthens$                    → Clean to: LAthens
xBelton$                    → Clean to: xBelton
Implementation
pythonteam_name = re.sub(r'[$#*@]+$', '', team_name)
Expected Impact

Fixes 70+ games (3% of errors)
Reduces VLOOKUP errors to ~3.7%


Category 6: Bye/Forfeit Games
~2% of errors | Action: Filter out
Examples
Lbyey                       → Skip entirely
nCopperas Covev 1 Lbyey 0   → Skip entirely
Implementation
pythonif 'bye' in combined.lower():
    continue  # Skip this game
if (score1 == '1' and score2 == '0'):
    continue  # Skip forfeit
Why Filter?

Not real games
No value for rankings or historical record
Just administrative markers

Expected Impact

Removes 50+ games (2% of errors)


Category 7: Out-of-State Opponents
~15% of errors | Action: Keep, create optional aliases
Examples
mPauls Valley, OKy          (1936)
TOklahoma Cityf             (1929)
mLiberal, KSy               (1929)
mTucumcari, NMy             (1927)
Strategy
These are legitimate games, just formatted differently.
Option A: Create aliases in VLOOKUP table
"mPauls Valley, OKy" → "Pauls Valley (OK)"
"TOklahoma Cityf" → "Oklahoma City (OK)"
Option B: Accept as unmapped (they're mostly pre-1940)
Option C: Bulk alias generation script
Recommendation
Start with Option B (accept), then create aliases for frequently appearing opponents.

Revised Error Reduction Projection
FixImpactCumulative Error RateCurrent state-6.5% (1,537 errors)Fix compressed scores-25%4.9% (1,160 errors)Strip neutral sites-5%4.6% (1,088 errors)Clean special chars-3%4.5% (1,063 errors)Filter Bye games-2%4.4% (1,040 errors)After automated fixes-35%4.4% (1,040 errors)
Remaining 4.4% errors:

~60% JV games (flagged, not errors) → 624 games
~15% College games (flagged, not errors) → 156 games
~15% Out-of-state (need aliases) → 156 games
~10% True errors/edge cases → 104 games

Effective error rate after flagging JV/College: ~1.1% (260 games)

Updated Workflow
Step 1: Run Updated Parser
bashpython lonestar_prep_for_excel_v2.py
Output columns:

team_id
team_name
season
week
team1_raw
score1
team2_raw
score2
notes (NEW: contains JV_GAME, COLLEGE_GAME flags)

Step 2: Excel Processing
Filter Options:
excel=IF(notes="JV_GAME", "JV", 
   IF(notes="COLLEGE_GAME", "College", 
      "Varsity"))
Separate workflows:

Varsity games → Standard VLOOKUP → HS_Scores
JV games → JV VLOOKUP table → HS_Scores_JV
College games → College VLOOKUP table → HS_Scores_College

Step 3: Create Separate VLOOKUP Tables
Varsity VLOOKUP (existing)

Maps obfuscated varsity team names

JV VLOOKUP (new)
nFarmersville JVy → Farmersville JV (TX)
*Plano JVy → Plano JV (TX)
College VLOOKUP (new)
PThorp Springs Collegef → Thorp Springs College (TX)
3Schreiner Prepy → Schreiner Prep (TX)
Step 4: SQL Import
Three separate imports:
sql-- Varsity games
BULK INSERT HS_Scores FROM 'varsity_games.csv' ...

-- JV games (new table)
BULK INSERT HS_Scores_JV FROM 'jv_games.csv' ...

-- College games (new table)
BULK INSERT HS_Scores_College FROM 'college_games.csv' ...

Benefits of This Approach
✅ Data Preservation

Complete historical record
Nothing discarded
Future research opportunities

✅ Flexible Analysis

Can include/exclude JV in rankings
Can analyze program depth over time
Can study college-HS competition era

✅ Better Organization

Clear separation of game types
Easier to maintain VLOOKUP tables
Reduces confusion in main database

✅ Scalability

Easy to add new game type flags
Can handle future data sources
Consistent pattern for all special cases


Implementation Notes
Parser Features (v2)

✅ Improved score extraction
✅ Game type detection (JV, College, Bye)
✅ Neutral site stripping
✅ Special character cleaning
✅ Preserves all legitimate games
✅ Flags instead of filters

Excel Formula Updates Needed
Add game type detection:
excel=IF(notes="JV_GAME", 
   VLOOKUP(team_raw, JV_Lookup, 6, FALSE),
   IF(notes="COLLEGE_GAME",
      VLOOKUP(team_raw, College_Lookup, 6, FALSE),
      VLOOKUP(team_raw, Varsity_Lookup, 6, FALSE)))
SQL Table Structure
sql-- New table for JV games
CREATE TABLE HS_Scores_JV (
    -- Same structure as HS_Scores
    -- Plus: JV_Level (Varsity playing JV? Or JV vs JV?)
);

-- New table for College games
CREATE TABLE HS_Scores_College (
    -- Same structure as HS_Scores
    -- Plus: College_Name, College_Level (JV vs Varsity)
);

Summary
Old approach: Filter out 48% of errors (JV + College)
New approach: Flag and preserve, focusing on real parsing errors
Result:

Better data preservation
More flexible analysis
Lower true error rate (1.1% vs 6.5%)
Maintains historical integ


================================================================================
LONESTAR FOOTBALL DATA IMPORT WORKFLOW
Complete Process from Excel to Production Database
================================================================================

OVERVIEW:
This workflow imports historical Texas high school football data (1902-2003)
from LoneStar Football website data that has been scraped and prepared in Excel.

PREREQUISITES:
- Excel file: C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HSF Texas 2025.xlsx
- Sheet: "Lonestar"
- Data columns: AA through AO (Date, Season, Visitor, etc.)
- Python environment: .venv activated
- SQL Server: MCKNIGHTS-PC\SQLEXPRESS01, database: hs_football_database

================================================================================
PART 1: SETUP (One-time per database)
================================================================================

STEP 1.1: Create Staging Table (if not exists)
--------------------------------------------------------------------------------
Run in SSMS:

CREATE TABLE HS_Scores_LoneStar_Staging (
    Date DATE,
    Season INT,
    Home VARCHAR(111),
    Visitor VARCHAR(111),
    Neutral BIT,
    Location VARCHAR(111),
    Location2 VARCHAR(255),
    Line INT,
    Future_Game BIT,
    Source VARCHAR(255),
    OT INT,
    Forfeit BIT,
    Visitor_Score INT,
    Home_Score INT,
    Margin INT,
    BatchID INT
);

STEP 1.2: Create Import Stored Procedure
--------------------------------------------------------------------------------
Run in SSMS: Create_sp_Import_LoneStar_Batch.sql

This creates the procedure that will:
- Parse @Location strings from team names
- Extract locations to Location field
- Set Neutral = 1 for neutral site games
- Validate team names
- Fix margin calculations
- Import to HS_Scores with unique IDs
- Remove duplicates

================================================================================
PART 2: BATCH IMPORT PROCESS (Repeat for each batch)
================================================================================

STEP 2.1: Prepare Excel Data
--------------------------------------------------------------------------------
In Excel file "HSF Texas 2025.xlsx", sheet "Lonestar":
- Ensure data is in columns AA-AO
- Column mapping:
  * AA = Date
  * AB = Season  
  * AC = Visitor (may contain "@Location" strings)
  * AD = Visitor_Score
  * AE = Home (may contain "@Location" strings)
  * AF = Home_Score
  * AG = Margin
  * AH = Neutral
  * AI = Location
  * AJ = Location2
  * AK = (skipped - Line not used)
  * AL = (skipped - Future_Game not used)
  * AM = Source (LoneStar URL with Team ID)
  * AN = (skipped - OT not tracked)
  * AO = Forfeit

NOTES:
- Team names may include "@Location" (e.g., "La Marque @Hou Astrodome (TX)")
- This is NORMAL - the import script will parse these automatically
- Don't try to fix them in Excel - let the SQL handle it

STEP 2.2: Run Python Import to Staging
--------------------------------------------------------------------------------
Open PowerShell:

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
.\venv\Scripts\Activate
python import_lonestar_excel.py

What this does:
- Reads columns AA-AO from Excel (skipping unused columns)
- Converts Excel dates to SQL dates
- Detects forfeits (1-0 or 0-1 scores)
- Handles NaN/NULL values properly
- Imports to HS_Scores_LoneStar_Staging with BatchID
- Reports success/error count

Expected output:
✓ Loaded 24042 rows from Excel
✓ Removed 0 rows with missing teams
✓ Data cleaned, 24042 rows ready for import
✓ Connected to SQL Server
✓ Using Batch ID: 1 (or 2, 3, etc.)
  Imported 500 rows...
  Imported 1000 rows...
  ...
✓ Transaction committed
Successfully imported: 24042 rows
Errors: 0 rows

STEP 2.3: Verify Staging Data (Optional but Recommended)
--------------------------------------------------------------------------------
Run in SSMS:

-- Quick check
SELECT TOP 10 
    Date, Season, Home, Visitor, Home_Score, Visitor_Score, 
    Neutral, Location, Source
FROM HS_Scores_LoneStar_Staging 
WHERE BatchID = 1  -- Use your actual BatchID
ORDER BY Date;

-- Check for @Location strings (these will be parsed automatically)
SELECT COUNT(*) as GamesWithLocations
FROM HS_Scores_LoneStar_Staging
WHERE BatchID = 1 
  AND (Home LIKE '%@%' OR Visitor LIKE '%@%');

-- Season distribution
SELECT Season, COUNT(*) as GameCount
FROM HS_Scores_LoneStar_Staging
WHERE BatchID = 1
GROUP BY Season
ORDER BY Season;

STEP 2.4: Run Import to Production
--------------------------------------------------------------------------------
Run in SSMS:

EXEC dbo.sp_Import_LoneStar_Batch @BatchID = 1;  -- Use your actual BatchID

What this does:
Step 1: Parse location strings
   - Finds team names with "@Location"
   - Extracts actual team name (e.g., "La Marque (TX)")
   - Moves location to Location field (e.g., "Hou Astrodome")
   - Sets Neutral = 1
   
Step 2: Check team names
   - Compares against HS_Team_Names table
   - Warns about missing teams (but still imports them)
   - Shows list of teams to add later
   
Step 3: Verify margins
   - Checks Margin = Home_Score - Visitor_Score
   - Fixes any incorrect calculations
   
Step 4: Import to HS_Scores
   - Generates unique ID (GUID) for each game
   - Inserts all games with current timestamp
   - Preserves BatchID for tracking
   
Step 5: Remove duplicates
   - Finds exact duplicate games (same date, teams, scores)
   - Keeps most recent import
   - Reports count of duplicates removed

Expected output:
============================================================================
LoneStar Batch Import - BatchID: 1
============================================================================

Step 1: Parsing location strings from team names...
  Found 15234 games with location strings
  ✓ Fixed 7892 Home teams
  ✓ Fixed 7342 Visitor teams

Step 2: Checking team names...
⚠️  WARNING: Found 181 teams not in HS_Team_Names table:
[List of teams]
These teams will still be imported, but you may want to add them to HS_Team_Names.

Step 3: Verifying margin calculations...
✓ All margins are correct

Step 4: Importing data to HS_Scores...
✓ Imported 24042 games to HS_Scores

Step 5: Checking for duplicates...
✓ No duplicates found

============================================================================
IMPORT COMPLETE
============================================================================
Total games imported: 24042
Duplicates removed: 0
Net new games: 24042

Games by season:
[Season breakdown table]

✓ Transaction committed successfully
============================================================================

STEP 2.5: Verify Production Data
--------------------------------------------------------------------------------
Run in SSMS:

-- Check total LoneStar games in production
SELECT 
    COUNT(*) as TotalGames,
    MIN(Season) as FirstSeason,
    MAX(Season) as LastSeason
FROM HS_Scores
WHERE Source LIKE '%lonestar%';

-- Check neutral site games
SELECT 
    COUNT(*) as NeutralSiteGames
FROM HS_Scores
WHERE Source LIKE '%lonestar%' 
  AND Neutral = 1;

-- Sample recent imports
SELECT TOP 20
    Date, Season, Home, Visitor, Home_Score, Visitor_Score, 
    Location, Neutral, Source
FROM HS_Scores
WHERE BatchID = 1  -- Use your actual BatchID
ORDER BY Date DESC;

-- Check for any remaining @Location strings (should be 0)
SELECT COUNT(*) as RemainingLocationStrings
FROM HS_Scores
WHERE Source LIKE '%lonestar%'
  AND (Home LIKE '%@%' OR Visitor LIKE '%@%');

STEP 2.6: Add Missing Teams to HS_Team_Names (Optional)
--------------------------------------------------------------------------------
The import will warn you about teams not in HS_Team_Names. These games are
still imported, but you may want to add the teams for future features
(logos, colors, etc.)

To get the list:
-- This query was run during import, but you can run it again:
SELECT DISTINCT TeamName
FROM (
    SELECT Home AS TeamName FROM HS_Scores WHERE BatchID = 1
    UNION
    SELECT Visitor AS TeamName FROM HS_Scores WHERE BatchID = 1
) AS AllTeams
WHERE TeamName NOT IN (SELECT Team_Name FROM HS_Team_Names)
ORDER BY TeamName;

To add teams:
INSERT INTO HS_Team_Names (Team_Name, State, City)
VALUES 
    ('New Team Name (TX)', 'TX', 'City Name'),
    ('Another Team (TX)', 'TX', 'Another City');

================================================================================
PART 3: BATCH 2 AND BEYOND
================================================================================

For subsequent batches (Batch 2, 3, 4, etc.):

1. Update Excel with new data (or use existing data)
2. Run: python import_lonestar_excel.py
   - Script automatically increments BatchID
3. Run: EXEC dbo.sp_Import_LoneStar_Batch @BatchID = 2;
4. Verify production data

The process is identical for each batch!

================================================================================
TROUBLESHOOTING
================================================================================

ISSUE: Python script fails with "Parameter 10 TDS error"
FIX: This was an OT column timestamp issue - already fixed in current script

ISSUE: "Cannot insert NULL into column 'ID'"
FIX: Updated stored procedure now generates NEWID() for each game

ISSUE: Team names still have "@Location" after import
FIX: Make sure you're using the updated stored procedure that includes
     location parsing in Step 1

ISSUE: "BatchID not found in staging table"
FIX: Make sure the Python import completed successfully before running
     the stored procedure

ISSUE: Duplicate games after import
FIX: The stored procedure automatically removes duplicates in Step 5.
     If you still see duplicates, you can manually run:
     EXEC dbo.RemoveDuplicateGames;

================================================================================
DATA QUALITY NOTES
================================================================================

FORFEIT DETECTION:
- Games with 1-0 or 0-1 scores are automatically marked as forfeits
- Explicit Forfeit = 1 in Excel is also respected

NEUTRAL SITE DETECTION:
- Games with "@Location" in team names are marked Neutral = 1
- Location is extracted and stored in Location field
- Original neutral site data from Excel is preserved

MARGIN CALCULATION:
- Margin is preserved from Excel (your formulas)
- Verified during import: Margin = Home_Score - Visitor_Score
- Automatically corrected if incorrect

SOURCE TRACKING:
- Source field contains LoneStar URL with Team ID
- Format: "http://lonestarfootball.net Team XXX"
- Preserves provenance for all games

================================================================================
FILES REFERENCE
================================================================================

Python Scripts:
- import_lonestar_excel.py - Main import script

SQL Scripts:
- Create_sp_Import_LoneStar_Batch.sql - Stored procedure creation
- Verify_LoneStar_Import.sql - Data verification queries
- Fix_LoneStar_Locations.sql - Standalone location parser (not needed if using SP)

Excel Files:
- HSF Texas 2025.xlsx - Source data

Database Tables:
- HS_Scores_LoneStar_Staging - Temporary staging table
- HS_Scores - Production table
- HS_Team_Names - Master team list

================================================================================
SUCCESS CRITERIA
================================================================================

✅ All games imported to HS_Scores
✅ No @Location strings remaining in team names
✅ Neutral = 1 for all games with locations
✅ Location field populated for neutral site games
✅ Forfeits detected and marked
✅ Margins calculated correctly
✅ No duplicate games
✅ Source URLs preserved
✅ Team names properly formatted with (TX) suffix

================================================================================
READY FOR BATCH 2!
================================================================================

When ready for your next batch:
1. Prepare data in Excel (if different from current)
2. python import_lonestar_excel.py
3. EXEC dbo.sp_Import_LoneStar_Batch @BatchID = 2;
4. Verify and celebrate! 🎯

================================================================================