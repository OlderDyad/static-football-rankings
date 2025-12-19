# LoneStar Football Pre-2004 Data Import Workflow

## 📋 QUICK START GUIDE

### Prerequisites
- Python virtual environment activated (`.venv`)
- Excel file closed before running imports
- SSMS open for verification queries
- Working directory: `C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import`

### Standard Workflow (One Batch)

```powershell
# Step 1: Export raw data from database
python export_team_range_to_excel.py 1 720
# Output: HSF Texas 2025_teams_1-720.xlsx

# Step 2: Clean data in Excel
# - Open file in Excel
# - Create Lonestar_Import tab
# - Apply VLOOKUP formulas to columns C and E
# - Verify ~121K rows
# - SAVE AND CLOSE EXCEL

# Step 3: Import cleaned data
python import_lonestar_cleaned.py
# Output: ~121K games imported with new BatchID

# Step 4: Audit in SQL
# Run audit queries from section below
```

### Emergency: Delete Bad Import

```sql
-- If you imported junk names by mistake:
DELETE FROM HS_Scores 
WHERE Source LIKE 'LoneStar Team%' 
  AND Date_Added > '2025-12-17'
  AND (Visitor LIKE '[0-9]%' OR Home LIKE '[0-9]%');

-- Clear staging table
DELETE FROM HS_Scores_LoneStar_Staging 
WHERE BatchID = [bad_batch_id];
```

---

## 🎯 PROJECT OVERVIEW

**Goal:** Import historical Texas high school football data (1902-2003) from LoneStar Football website into HS_Scores table.

**Data Source:** http://lonestarfootball.net (pre-2004 historical data)

**Total Scope:** ~850K-1M games after deduplication across 4-5 batches

**Database:** `hs_football_database` on `McKnights-PC\SQLEXPRESS01`

**Key Tables:**
- `HS_Scores_LoneStar_Staging` - Raw scraped data
- `HS_Scores` - Final clean data
- `team_scraping_status` - Tracks scraping progress
- `scraping_batches` - Batch metadata

---

## 📊 BATCH PROGRESS

### Batch 1: COMPLETE ✅
- **Teams:** 1-720 (523 teams with data)
- **Games:** 121,403 games
- **Seasons:** 1902-2003
- **Status:** Imported to HS_Scores with clean names

### Batch 2: IN PROGRESS 🔄
- **Teams:** 721-1440
- **Started:** 12/17/2025 ~8 PM
- **Status:** Scraping overnight (team 725 at 10 PM)

### Future Batches:
- Batch 3: Teams 1441-2160
- Batch 4: Teams 2161-2880
- Batch 5: Teams 2881-3600

---

## 🔧 TECHNICAL SETUP

### File Locations

**Python Scripts:**
```
C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\
├── scrape_lonestar_batch.py          # Web scraper
├── export_team_range_to_excel.py     # Export raw data
├── import_lonestar_cleaned.py        # Import cleaned data
└── .venv\                             # Virtual environment
```

**Excel Files:**
```
C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\
├── HSF Texas 2025_teams_1-720.xlsx           # Raw export
└── HSF Texas 2025_teams_1-720_v1.xlsx        # Cleaned version
```

**SQL Objects:**
```sql
-- Tables
HS_Scores_LoneStar_Staging
HS_Scores
team_scraping_status
scraping_batches

-- Stored Procedures
sp_Import_LoneStar_Batch  -- NOT USED (requires @Location format)
```

### Database Connection
```python
Server: McKnights-PC\SQLEXPRESS01
Database: hs_football_database
Driver: ODBC Driver 17 for SQL Server
```

---

## 📝 DETAILED WORKFLOW

### Phase 1: Web Scraping (Overnight Process)

**Script:** `scrape_lonestar_batch.py`

**Purpose:** Download schedule HTML from LoneStar Football website

**Input:** Team ID range (e.g., 1-720)

**Output:** Raw HTML stored in `HS_Scores_LoneStar_Staging.Schedule_Text`

**Run Command:**
```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
.venv\Scripts\activate
python scrape_lonestar_batch.py
```

**Process:**
1. Creates batch in `scraping_batches` table
2. Processes teams in range (50 teams/batch)
3. Downloads schedule HTML for each team
4. Stores in staging table with:
   - team_id
   - team_name
   - Schedule_Text (raw HTML)
   - BatchID
5. Updates `team_scraping_status` for resume capability

**Anti-Detection:**
- Random delays (2-5 seconds between requests)
- Rotating user agents
- Session management

**Runtime:** ~8-12 hours for 720 teams

---

### Phase 2: Export Raw Data

**Script:** `export_team_range_to_excel.py`

**Purpose:** Parse HTML schedules and export to Excel

**Input:** Team ID range

**Output:** Excel file with raw game data (includes junk characters)

**Run Command:**
```powershell
python export_team_range_to_excel.py 1 720
```

**Parsing Logic:**

**Week Number Extraction:**
```python
# Regex: r'^(\d+/?[\d]*)\s+'
# Matches: "1", "9/19", "10/31", "0"
week_match = re.search(r'^(\d+/?[\d]*)\s+', line)
```

**Score Extraction:**
```python
# Regex: r'\s+(\d+)(?:\s+|$)'
# Key: (?:\s+|$) makes trailing space optional
# Handles end-of-line scores: "Fort Elliott 34"
parts = re.split(r'\s+(\d+)(?:\s+|$)', remaining)
```

**Output Format (Excel columns A-H):**

| Col | Name | Example | Description |
|-----|------|---------|-------------|
| A | team_id | 1 | LoneStar team ID |
| B | team_name | Fort Elliott | Team name from database |
| C | season | 2003 | Year |
| D | WK | 10/31 | Week number or date |
| E | Team1 | LFort Elliottv | Raw with junk (L=away, v=suffix) |
| F | SC1 | 39 | Team1 score |
| G | Team2 | PSamnorwoodv | Raw with junk (P=playoff, v=suffix) |
| H | SC2 | 26 | Team2 score |

**Junk Character Preservation:**

These characters are INTENTIONALLY kept for VLOOKUP matching:

**Prefixes:**
- `L` = Away game
- `P` = Playoff game
- `T` = Tournament
- `*` = Conference game
- `#` = District game
- Numbers (3, 7, etc.) = Unknown meaning
- `@`, `n`, `x`, `m` = Various indicators

**Suffixes:**
- `v` = Most common
- `y`, `f`, `d`, `s`, `p`, `a`, `t` = Various
- `$`, `)` = Special cases

**Why Keep Junk?**
- VLOOKUP formulas in Excel expect exact matches
- Alias table contains entries like "3Hedleyv" → "Hedley (TX)"
- Removing junk breaks the lookup chain

**Output Stats (Batch 1):**
- 121,403 games
- 523 teams
- 15,829 team-seasons

---

### Phase 3: Clean Data in Excel

**Input File:** `HSF Texas 2025_teams_1-720.xlsx`

**Output File:** `HSF Texas 2025_teams_1-720_v1.xlsx`

**Process:**

1. **Create New Sheet:** `Lonestar_Import`

2. **Set Up Columns (A-P):**
   - A: Date
   - B: Season
   - C: Visitor (CLEANED)
   - D: Visitor_Score
   - E: Home (CLEANED)
   - F: Home_Score
   - G: Margin
   - H: Neutral
   - I: Location
   - J: Location2
   - K: Line
   - L: Future_Game
   - M: Source
   - N: Date_Added
   - O: OT
   - P: Forfeit

3. **Apply VLOOKUP Formulas:**

```excel
# Column C (Visitor - Cleaned):
=IFERROR(VLOOKUP(E2,'Raw Data'!$A:$B,2,FALSE),E2)

# Column E (Home - Cleaned):
=IFERROR(VLOOKUP(G2,'Raw Data'!$A:$B,2,FALSE),G2)
```

Where `'Raw Data'!$A:$B` is your alias lookup table:
- Column A: Junk name (e.g., "3Hedleyv")
- Column B: Clean name (e.g., "Hedley (TX)")

4. **Populate Other Columns:**
   - Date: Parse from week + season
   - Margin: =ABS(D2-F2)
   - Source: ="http://lonestarfootball.net/team/[team_id]"
   - Date_Added: =TODAY()
   - Rest: Leave blank or default values

5. **Verify:**
   - Row count matches export (~121K)
   - No junk suffixes in columns C and E
   - All team names include state: "(TX)"
   - Scores are numeric

6. **SAVE AND CLOSE EXCEL** ⚠️

---

### Phase 4: Import to Database

**Script:** `import_lonestar_cleaned.py`

**Purpose:** Import cleaned data from Excel to HS_Scores table

**Input:** `Lonestar_Import` sheet from Excel file

**Output:** Games in HS_Scores with new BatchID

**Run Command:**
```powershell
python import_lonestar_cleaned.py
```

**Process:**

1. **Validation:**
   - Excel file must be closed
   - Checks for required columns
   - Verifies data types

2. **Safety Deletes (Optional):**
   - Can delete bad imports from today
   - Uses date + source filters for safety
   - Commented out if already cleaned manually

3. **BatchID Assignment:**
   - Queries: `SELECT ISNULL(MAX(BatchID), 0) + 1 FROM HS_Scores`
   - Assigns sequential batch number

4. **Data Mapping:**
   ```python
   Excel Column → Database Column
   ------------   ---------------
   Date         → Date
   Season       → Season
   Visitor      → Visitor (CLEANED)
   Visitor_Score → Visitor_Score
   Home         → Home (CLEANED)
   Home_Score   → Home_Score
   Margin       → Margin
   Neutral      → Neutral
   Location     → Location
   Location2    → Location2
   Source       → Source
   Forfeit      → Forfeit
   [Generated]  → BatchID (new)
   [Generated]  → Date_Added (TODAY)
   ```

5. **Bulk Insert:**
   - Uses cursor.executemany()
   - Batch size: 1000 rows
   - Progress updates every 10K rows

6. **Commit:**
   - Single transaction for all rows
   - Rollback on error

**Output:**
```
✓ Loaded 121377 rows
✓ Connected to database
✓ Generated BatchID: 5
✓ Processed 121,377 rows
✓ Import complete!

Final Stats:
  Rows Inserted: 121,377
  BatchID: 5
  Import Time: 45 seconds
```

---

### Phase 5: Audit & Verify

**Purpose:** Confirm data quality and completeness

**Run these SQL queries in SSMS:**

#### Query 1: Total Count & Range
```sql
SELECT 
    COUNT(*) as TotalGames,
    MIN(Season) as FirstSeason,
    MAX(Season) as LastSeason,
    MAX(BatchID) as LatestBatchID
FROM HS_Scores
WHERE Source LIKE 'http://lonestarfootball.net%';
```

**Expected:**
- TotalGames: 121,377
- FirstSeason: 1902
- LastSeason: 2003
- LatestBatchID: 5 (or your current batch)

#### Query 2: Check for Junk Names
```sql
SELECT 
    COUNT(*) as JunkNameCount,
    'FAIL - Junk names found!' as Status
FROM HS_Scores
WHERE Source LIKE 'http://lonestarfootball.net%'
  AND (
      Visitor LIKE '%v' OR Visitor LIKE '%y' OR Visitor LIKE '%f'
      OR Visitor LIKE '[0-9]%'
      OR Home LIKE '%v' OR Home LIKE '%y' OR Home LIKE '%f'
      OR Home LIKE '[0-9]%'
  )
UNION ALL
SELECT 
    0 as JunkNameCount,
    'PASS - All names clean!' as Status
WHERE NOT EXISTS (
    SELECT 1 FROM HS_Scores
    WHERE Source LIKE 'http://lonestarfootball.net%'
      AND (
          Visitor LIKE '%v' OR Visitor LIKE '%y' OR Visitor LIKE '%f'
          OR Visitor LIKE '[0-9]%'
          OR Home LIKE '%v' OR Home LIKE '%y' OR Home LIKE '%f'
          OR Home LIKE '[0-9]%'
      )
);
```

**Expected:** 0 junk names (PASS)

#### Query 3: Top Teams by Game Count
```sql
SELECT TOP 20
    Visitor as TeamName,
    COUNT(*) as GameCount
FROM HS_Scores
WHERE Source LIKE 'http://lonestarfootball.net%'
GROUP BY Visitor
ORDER BY COUNT(*) DESC;
```

**Expected:** Clean names like "Celina (TX)", "Mart (TX)"

#### Query 4: Games by Season
```sql
SELECT 
    Season,
    COUNT(*) as GameCount
FROM HS_Scores
WHERE Source LIKE 'http://lonestarfootball.net%'
GROUP BY Season
ORDER BY Season;
```

**Expected Pattern:**
- Early years (1902-1920): 1-80 games/year
- Growth (1920s-1930s): 80→530 games
- WWII dip (1942-1943): ~480-490 games
- Post-war (1945-1960s): 850→1,948 games
- Modern (2000-2003): 2,183→2,552 games

#### Query 5: Duplicate Detection
```sql
SELECT 
    Date, Home, Visitor, Home_Score, Visitor_Score,
    COUNT(*) as DuplicateCount
FROM HS_Scores
WHERE Source LIKE 'http://lonestarfootball.net%'
GROUP BY Date, Home, Visitor, Home_Score, Visitor_Score
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;
```

**Expected:** 0 duplicates (within single batch)

**Note:** Cross-batch duplicates (overlap with MaxPreps) handled separately

#### Query 6: Batch Verification
```sql
SELECT 
    BatchID,
    COUNT(*) as GameCount,
    MIN(Season) as FirstSeason,
    MAX(Season) as LastSeason,
    MIN(Date_Added) as ImportDate
FROM HS_Scores
WHERE Source LIKE 'http://lonestarfootball.net%'
GROUP BY BatchID
ORDER BY BatchID;
```

**Expected:** One row per batch with correct counts

---

## ⚠️ COMMON ISSUES & SOLUTIONS

### Issue 1: Excel File Locked

**Error:**
```
PermissionError: [Errno 13] Permission denied: 'HSF Texas 2025_teams_1-720_v1.xlsx'
```

**Solution:** Close Excel completely before running Python import

---

### Issue 2: Missing Column Error

**Error:**
```
KeyError: 'Forfeit'
```

**Solution:** Ensure Lonestar_Import sheet has all 16 columns (A-P)

---

### Issue 3: Imported Junk Names

**Symptoms:**
- Team names like "3Hedleyv", "LFort Elliottv" in HS_Scores
- VLOOKUP formulas not applied

**Solution:**
1. Delete bad import (use date filter for safety):
```sql
DELETE FROM HS_Scores 
WHERE Source LIKE 'http://lonestarfootball.net%' 
  AND Date_Added = CAST(GETDATE() AS DATE)
  AND (Visitor LIKE '[0-9]%' OR Home LIKE '[0-9]%');
```

2. Verify Excel file:
   - Check Lonestar_Import tab exists
   - Columns C and E should show clean names: "Team (TX)"
   - Not raw junk: "3Teamv"

3. Re-run import: `python import_lonestar_cleaned.py`

---

### Issue 4: Parsing Bug (Missing Games)

**Symptoms:**
- Export shows fewer games than expected
- Only capturing weeks 10+ (double-digit weeks)
- Missing weeks 1-9

**Cause:** Regex requires trailing space after scores

**Bad Regex:**
```python
r'\s+(\d+)\s+'  # Requires space BEFORE and AFTER
```

**Fixed Regex:**
```python
r'\s+(\d+)(?:\s+|$)'  # Space OR end-of-line
```

**Solution:** Update `export_team_range_to_excel.py` with fixed regex

---

### Issue 5: Stored Procedure Failure

**Error:**
```
Cannot parse location from: "3Hedleyv"
```

**Cause:** `sp_Import_LoneStar_Batch` expects `@Location` format like:
```
@Week=1 @Home=Fort Elliott @HomeScore=52 @Visitor=Hedley @VisitorScore=34
```

But we're sending raw junk names.

**Solution:** Don't use the stored procedure! Use `import_lonestar_cleaned.py` instead, which:
- Reads pre-cleaned data from Excel
- Inserts directly to HS_Scores
- Bypasses stored procedure entirely

---

### Issue 6: Database Connection Failed

**Error:**
```
pyodbc.Error: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]...')
```

**Solutions:**
1. Verify SQL Server is running
2. Check instance name: `McKnights-PC\SQLEXPRESS01`
3. Test connection in SSMS first
4. Ensure ODBC Driver 17 installed

---

## 🔄 BATCH COORDINATION

### Starting New Batch

1. **Wait for Previous Scrape:**
   - Check `team_scraping_status` for completion
   - Verify last team processed

2. **Export Previous Batch:**
   ```powershell
   python export_team_range_to_excel.py [start] [end]
   ```

3. **Start Next Scrape:**
   ```powershell
   python scrape_lonestar_batch.py
   # Enter next range: 721-1440
   ```

4. **Clean & Import Previous Batch:**
   - While new batch scrapes overnight
   - Excel cleaning + import
   - Audit results

### Batch Timing Strategy

- **Scraping:** Overnight (8-12 hours)
- **Export:** 5 minutes
- **Excel Cleaning:** 30-60 minutes
- **Import:** 1-2 minutes
- **Audit:** 5 minutes

**Total per batch:** ~1 day (scraping) + 1-2 hours (processing)

---

## 📈 DATA QUALITY METRICS

### Batch 1 Statistics

**Coverage:**
- Teams: 523 (out of 720 team IDs)
- Games: 121,403
- Seasons: 102 years (1902-2003)
- Team-Seasons: 15,829

**Historical Growth:**
```
1908-1920:  1→80 games/year (early adoption)
1920-1930:  80→530 games/year (10x growth)
1930-1942:  530→680 games/year (steady)
1942-1943:  480-490 games/year (WWII decline)
1945-1960:  850→1,948 games/year (post-war boom)
1960-2000:  1,948→2,183 games/year (slow growth)
2000-2003:  2,183→2,552 games/year (modern era)
```

**Data Quality Checks:**
- ✅ Zero junk names after cleaning
- ✅ All teams include state: "(TX)"
- ✅ No duplicates within batch
- ✅ Scores are numeric (0-999)
- ✅ Dates valid (1902-2003)

---

## 🎯 SUCCESS CRITERIA

### Per-Batch Success
- [ ] All teams in range scraped
- [ ] Export row count matches staging table
- [ ] Zero junk names after import
- [ ] Audit queries pass
- [ ] No duplicates within batch

### Project Success
- [ ] All 5 batches completed
- [ ] 850K-1M total games imported
- [ ] Cross-batch deduplication complete
- [ ] MaxPreps overlap resolved
- [ ] Website rankings updated

---

## 📚 KEY LEARNINGS

### 1. Raw Data ≠ Import-Ready Data
- Scraped HTML contains junk characters
- Excel VLOOKUP essential for cleaning
- Can't import raw data directly to HS_Scores

### 2. Regex Edge Cases Matter
- End-of-line scores need special handling
- `(?:\s+|$)` pattern for optional trailing space
- Test parsing with edge cases

### 3. Safety in Deletion
- BatchID alone insufficient (can be reused)
- Add date filters: `Date_Added = TODAY`
- Add name pattern filters for extra safety

### 4. Excel File Locking
- Python can't read open Excel files
- Always close Excel before import
- Use try-except for clear error messages

### 5. Stored Procedures vs. Direct Insert
- Stored procedures need specific input formats
- Direct insert more flexible for cleaned data
- Choose based on data source format

---

## 🔮 FUTURE ENHANCEMENTS

### Potential Improvements

1. **Automated VLOOKUP in Python:**
   - Load alias table from Excel/SQL
   - Apply cleaning in export script
   - Skip manual Excel step

2. **Parallel Scraping:**
   - Multiple threads for faster scraping
   - Rate limiting to avoid detection
   - Current: 1 team every 2-5 seconds

3. **Cross-Batch Deduplication:**
   - Identify MaxPreps overlaps (2004+)
   - Merge duplicate games
   - Prefer MaxPreps for recent data

4. **Data Validation:**
   - Score reasonability checks (0-999)
   - Date validation (season year)
   - Team name format validation

5. **Resume Capability:**
   - Export script can resume mid-batch
   - Track export progress in database
   - Handle partial Excel files

---

## 📞 TROUBLESHOOTING CONTACTS

### Key Files to Check
1. **Scraping Progress:** `team_scraping_status` table
2. **Batch Metadata:** `scraping_batches` table
3. **Staging Data:** `HS_Scores_LoneStar_Staging` table
4. **Final Data:** `HS_Scores` WHERE Source LIKE 'lonestar%'

### Debug Queries
```sql
-- Check scraping progress
SELECT * FROM team_scraping_status 
WHERE batch_id = [current_batch]
ORDER BY team_id DESC;

-- Check staging data
SELECT TOP 100 * FROM HS_Scores_LoneStar_Staging
WHERE BatchID = [current_batch]
ORDER BY team_id;

-- Find last import
SELECT TOP 1 * FROM HS_Scores
WHERE Source LIKE 'http://lonestarfootball.net%'
ORDER BY Date_Added DESC;
```

---

## ✅ WORKFLOW CHECKLIST

### Before Starting New Batch
- [ ] Previous batch scraping complete
- [ ] Previous batch exported to Excel
- [ ] Previous batch cleaned in Excel
- [ ] Previous batch imported to SQL
- [ ] Previous batch audit queries passed
- [ ] Excel file closed
- [ ] Virtual environment activated

### During Scraping
- [ ] Monitor progress in team_scraping_status
- [ ] Check for scraping errors in logs
- [ ] Verify Schedule_Text populated

### During Export
- [ ] Verify row count matches staging
- [ ] Check for parsing errors
- [ ] Confirm junk characters preserved

### During Cleaning
- [ ] VLOOKUP formulas applied
- [ ] All names show "(TX)" state
- [ ] No junk suffixes remain
- [ ] Row count unchanged

### During Import
- [ ] Excel file closed
- [ ] Verify BatchID increments
- [ ] Check row count matches Excel
- [ ] Monitor for errors

### After Import
- [ ] Run all 6 audit queries
- [ ] Verify zero junk names
- [ ] Check season distribution
- [ ] Confirm no duplicates
- [ ] Document results

---

## 📝 VERSION HISTORY

**v1.0 - 2025-12-17**
- Initial workflow documentation
- Batch 1 complete (121,403 games)
- Fixed parsing bug for end-of-line scores
- Established Excel cleaning process

**v1.1 - 2025-12-18**
- Added quick start guide
- Enhanced safety deletion logic
- Documented common issues
- Added comprehensive audit queries

---

## 🎓 APPENDIX

### A. File Naming Convention
```
HSF Texas 2025_teams_[start]-[end].xlsx       # Raw export
HSF Texas 2025_teams_[start]-[end]_v1.xlsx    # Cleaned version
```

### B. Team ID Ranges
- Batch 1: 1-720
- Batch 2: 721-1440
- Batch 3: 1441-2160
- Batch 4: 2161-2880
- Batch 5: 2881-3600

### C. Source URL Pattern
```
http://lonestarfootball.net/team/[team_id]
```

### D. Python Dependencies
```
pandas
openpyxl
pyodbc
requests
beautifulsoup4
```

### E. SQL Server Configuration
```
Instance: SQLEXPRESS01
Database: hs_football_database
Authentication: Windows Authentication
```

---

## 📧 SUPPORT

For issues or questions:
1. Check Common Issues section
2. Review audit queries
3. Verify file paths and permissions
4. Check database connection
5. Review error logs in terminal

---

**Document Status:** Active  
**Last Updated:** December 18, 2025  
**Next Review:** After Batch 5 completion  

---
