# NEWSPAPER SCORES IMPORT WORKFLOW - CURRENT VERSION
# McKnight's American Football Rankings - Updated January 31, 2026

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\
python ks_8man_classifier.py


#Quick Guide:
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
python custom_extractor_prepper.py
python master_scores_importer.py
python apply_corrections.py
python master_scores_importer.py
after completing:
python batch_queue_manager.py
## Overview
This workflow allows you to process newspaper images, extract game scores, and import them 
into the HS_Scores database WITHOUT interrupting long-running rating calculations.

## Key Features
✅ **Non-blocking**: Queue batches while rating calculations run
✅ **NULL validation**: Prevents empty team names from reaching the database
✅ **Batch processing**: Handle multiple batches at once
✅ **Simple 2-stage process**: STAGED → IMPORTED
✅ **Integration**: Works with your existing duplicate removal procedure

## File Structure
```
custom_extractor_prepper.py     # Processes images → CSV files
master_scores_importer.py       # CSV → RawScores_Staging + queue
apply_corrections.py            # Applies alias corrections
batch_queue_manager.py          # Import batches to HS_Scores
```

## Complete Workflow

### PHASE 1: Image Processing
```bash
python custom_extractor_prepper.py
```

**What it does:**
1. Prompts you to select format (Comma or Bar separated)
2. Processes images from appropriate folder:
   - Bar: `J:\...\Next_Images_Bar_Format`
   - Comma: `J:\...\Next_Images_Comma_Format`
3. Uses Google Document AI custom extractors to extract game data
4. Creates CSV files in: `J:\...\Staged\`
5. Moves processed images to: `C:\...\Processed_IMAGES_[Format]\`

**CSV Output Format:**
```
home_team,home_score,visitor_team,visitor_score,overtime,quality_status,notes
Lincoln,21,Jefferson,14,,good,
Central,28,Roosevelt,27,OT,good,
Washington,1,Adams,0,,needs_review,Forfeit game detected
```

### PHASE 2: Import to Staging (Can Run While Rating Calc Runs!)
```bash
python master_scores_importer.py
```

**What it does:**
1. Reads all CSV files from `J:\...\Staged\`
2. Extracts date, season, and newspaper region from filenames
3. Sanitizes team names and scores
4. **NEW: Validates no NULL/empty team names**
5. Checks aliases and abbreviations against database
6. If unrecognized teams found → generates `New_Alias_Suggestions.csv`
7. If all teams recognized → loads to `RawScores_Staging` and queues batch

**Filename Pattern Required:**
```
NewspaperName_YYYY_MM_DD.csv
Example: Valley_News_1977_10_31_11.csv
```

**Batch States:**
- 📋 **STAGED** = In RawScores_Staging, ready to import to HS_Scores
- ✅ **IMPORTED** = In HS_Scores table, complete

### PHASE 2A: Handle Unrecognized Teams (If Needed)
If you see: `New_Alias_Suggestions.csv has been generated`

1. **Open the file**: `J:\...\Staged\New_Alias_Suggestions.csv`

2. **Review suggestions**: Three AI-suggested names provided for each unrecognized team

3. **Fill in Final_Proper_Name column**: 
   - Use one of the suggestions, OR
   - Type the correct standardized name

4. **Set Alias_Scope**:
   - `Regional` = Only for this newspaper region
   - `Global` = Apply everywhere

5. **Set Rule_Type**:
   - `Alias` = Full team name variation
   - `Abbreviation` = Short form (e.g., "Cen" → "Central")

**Example:**
```csv
Unrecognized_Alias,Newspaper_Region,Final_Proper_Name,Alias_Scope,Rule_Type
Cen HS,Valley News,Central (WA),Regional,Alias
Jeff,Valley News,Jefferson (WA),Regional,Abbreviation
```

6. **Apply corrections**:
```bash
python apply_corrections.py
```

7. **Re-run importer**:
```bash
python master_scores_importer.py
```

### PHASE 3: Import to HS_Scores (When Rating Calc is Done)
```bash
python batch_queue_manager.py
```

**Menu Options:**
```
1. Show queue status          # View all batches and their states
2. Import all staged batches  # Move batches to HS_Scores
3. Mark batch as imported     # Manual override (rarely needed)
4. Exit
```

**Typical usage:**
1. Select option `1` to view queued batches
2. Select option `2` to import all batches
3. Exit (option `4`)

**What option 2 does:**
```sql
-- For each batch, runs:
INSERT INTO HS_Scores (ID, Season, Date, Home, Visitor, Home_Score, Visitor_Score, OT, Forfeit)
SELECT NEWID(), Season, GameDate, HomeTeamRaw, VisitorTeamRaw, HomeScore, VisitorScore, 
       CASE WHEN Overtime IS NOT NULL AND Overtime <> '' THEN 1 ELSE 0 END,
       CASE WHEN (HomeScore + VisitorScore) = 1 THEN 1 ELSE 0 END
FROM RawScores_Staging
WHERE BatchID = '{batch_id}'
```

### PHASE 4: Remove Duplicates
```sql
EXEC [dbo].[RemoveDuplicateGamesParameterized] 
    @SeasonStart = 1877, 
    @SeasonEnd = 2025;
```

**Or target specific seasons:**
```sql
-- Just process the years you imported
EXEC [dbo].[RemoveDuplicateGamesParameterized] 
    @SeasonStart = 1970, 
    @SeasonEnd = 1985;
```

**What this does:**
1. Marks forfeit games (1-0 scores)
2. Finds and removes exact duplicates
3. Finds and removes team-swapped duplicates
4. Prints what was found and deleted

## Real-World Example

### Scenario: 5-Day Rating Calculation + Data Collection

**Day 1 (10:00 AM)**: Start rating calculation (will run until Day 5)
```bash
# Meanwhile, process newspapers:
python custom_extractor_prepper.py  # Process 50 images
python master_scores_importer_v4.py # Batch #1 → STAGED (3,996 games)
```

**Day 2 (2:00 PM)**: Continue collecting data
```bash
python custom_extractor_prepper.py  # Process 30 images
python master_scores_importer_v4.py # Batch #2 → STAGED (2,147 games)
```

**Day 3 (11:00 AM)**: More data
```bash
python custom_extractor_prepper.py  # Process 45 images
python master_scores_importer_v4.py # Batch #3 → STAGED (4,523 games)
```

**Day 4**: Check status
```bash
python batch_queue_manager.py
# Option 1: Shows 3 batches staged, 10,666 total games queued
```

**Day 5 (3:00 PM)**: Rating calc completes!
```bash
python batch_queue_manager.py
# Option 2: Import all 3 batches (takes ~2 minutes)
```

**Day 5 (3:05 PM)**: Clean up
```sql
EXEC [dbo].[RemoveDuplicateGamesParameterized] 
    @SeasonStart = 1877, @SeasonEnd = 2025;
-- Removes duplicates, takes ~5 minutes
```

**Day 5 (3:10 PM)**: Start new rating calculation with fresh data!

## Data Validation & Quality Control

### NULL Team Name Prevention
The importer now catches NULL/empty team names BEFORE importing:

**If found, you'll see:**
```
Unrecognized_Alias: [EMPTY/NULL HOME TEAM]
Source_Files: Valley_News_1977_10_31.csv
Opponents_Played: Lincoln High
```

**How to fix:**
1. Open the source CSV file
2. Find the game with empty team name
3. Re-extract image OR manually add team name
4. Re-run `master_scores_importer_v4.py`

### Score Sanitization
Automatically removes non-digit characters from scores:
- `"30,"` → `30`
- `"21"` → `21`
- `28.` → `28`

### Overtime Detection
Converts text overtime markers to numeric:
- Any non-empty overtime field → `OT = 1`
- Empty overtime field → `OT = 0`

### Forfeit Detection
Automatically marks forfeit games:
- Games with total score = 1 → `Forfeit = 1`
- All other games → `Forfeit = 0`

## Queue Storage

**Location**: `J:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged\batch_queue.json`

**Format:**
```json
{
  "batches": [
    {
      "batch_id": "057ec603-7764-4f13-ae54-ebb5a5d0fb73",
      "status": "staged",
      "created_at": "2026-01-28T17:44:29",
      "file_count": 291,
      "game_count": 3996,
      "source_files": ["Valley_News_1977_10_31_11.csv", "..."],
      "imported_at": null
    }
  ]
}
```

## Database Tables

### RawScores_Staging
**Purpose**: Temporary holding area for validated game data

**Columns:**
- BatchID (uniqueidentifier)
- SourceFile, SourceRegion
- GameDate, Season
- HomeTeamRaw, VisitorTeamRaw (standardized names)
- HomeScore, VisitorScore
- Overtime, quality_status, processing_notes
- LineNumber, RawLine

### HS_Scores
**Purpose**: Primary game results table

**Key Columns:**
- ID (uniqueidentifier, auto-generated)
- Season, Date
- Home, Visitor
- Home_Score, Visitor_Score
- OT (int: 0 or 1)
- Forfeit (bit)
- Margin (computed)

## Troubleshooting

### "Batch not found in queue"
The batch was imported before the queue system existed. Either:
- Manually add to queue, OR
- Just continue with new batches

### "Unrecognized teams found"
1. Check `New_Alias_Suggestions.csv`
2. Fill in proper names
3. Run `apply_corrections.py`
4. Re-run `master_scores_importer_v4.py`

### "Failed to import batch" - ID column error
Update `batch_queue_manager.py` - the INSERT needs `NEWID()` for the ID column.
(This should already be fixed in current version)

### "Found 37 NULL games in database"
These slipped through before validation was added:
```sql
DELETE FROM HS_Scores WHERE Home IS NULL OR Visitor IS NULL;
```

### Duplicate games still appearing
Make sure you run the duplicate removal procedure AFTER each import:
```sql
EXEC [dbo].[RemoveDuplicateGamesParameterized] 
    @SeasonStart = 1877, @SeasonEnd = 2025;
```

### Images not moving after processing
`custom_extractor_prepper.py` uses `shutil.move` for cross-disk moves.
Check that destination folders exist and are writable.

## Best Practices

### 1. Consistent Filename Format
Always use: `NewspaperName_YYYY_MM_DD_PageNumber.csv`
- Newspaper name determines region for alias lookup
- Date determines season (Aug-Dec = current year, Jan-Jul = previous year)

### 2. Batch Size
- Small batches (50-100 games): Easier to fix if errors found
- Large batches (1000+ games): More efficient processing
- Recommended: 200-500 games per batch

### 3. Alias Management
- Use **Regional** scope for newspaper-specific abbreviations
- Use **Global** scope for widely recognized teams
- Document unusual cases in team name notes

### 4. Timing Imports
- **Safe to import** if rating calc hasn't reached those seasons yet
- **Wait for calc to finish** if importing seasons already processed
- **Check current season** of rating calc before importing

### 5. Verify After Import
```sql
-- Check recent imports
SELECT TOP 100 * FROM HS_Scores 
ORDER BY Date_Added DESC;

-- Verify game counts by season
SELECT Season, COUNT(*) as Games
FROM HS_Scores
WHERE Season BETWEEN 1970 AND 1985
GROUP BY Season
ORDER BY Season;
```

## Quick Reference Commands

### Process everything from start to finish:
```bash
# 1. Extract from images
python custom_extractor_prepper.py

# 2. Import to staging (may need alias corrections)
python master_scores_importer_v4.py

# 3. Apply corrections if needed
python apply_corrections.py
python master_scores_importer_v4.py  # Re-run after corrections

# 4. Import to HS_Scores (when ready)
python batch_queue_manager.py  # Option 2

# 5. Clean up duplicates
# Run in SQL Server:
EXEC [dbo].[RemoveDuplicateGamesParameterized] @SeasonStart = 1877, @SeasonEnd = 2025;
```

### Check status:
```bash
python batch_queue_manager.py  # Option 1
```

### View queue file directly:
```bash
# Windows:
notepad "J:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged\batch_queue.json"
```

## Version History

### v4.0 (January 31, 2026)
- Added NULL team name validation
- Simplified to 2-stage process (removed STANDARDIZED stage)
- Fixed ID column auto-generation with NEWID()
- Integrated with batch queue system
- Score sanitization improvements

### v3.0 (January 28, 2026)
- Added batch queue system
- Non-blocking imports during rating calculations
- Automatic batch tracking

### v2.0 (Earlier)
- Added custom extractor integration
- Alias suggestion system
- Regional newspaper context

### v1.0 (Original)
- Basic CSV import
- Manual SQL execution required

---

**Questions or Issues?**
Document any new patterns or edge cases as you encounter them for future reference.