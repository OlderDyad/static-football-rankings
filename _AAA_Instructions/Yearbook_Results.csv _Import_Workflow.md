# Yearbook_Results.csv Import Workflow

## Overview
This workflow imports game data from `Yearbook_Results.csv` into the `HS_Scores` table using a standardized Python import script.

## Prerequisites

### Software Requirements
- Python 3.x installed
- Required Python packages:
  ```bash
  pip install pyodbc pandas
  ```

### Database Requirements
- SQL Server Express running (`MCKNIGHTS-PC\SQLEXPRESS01`)
- Database: `hs_football_database`
- Table: `dbo.HS_Scores` (must already exist)

### File Requirements
- CSV file location: `C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Yearbook_Results.csv`

## CSV Format

### Supported Column Formats

The script auto-detects between two common formats:

**Format 1: OCR/Newspaper Style**
```
HomeTeamRaw, HomeScore, VisitorTeamRaw, VisitorScore, Date, Season, Overtime
```

**Format 2: Standard Style**
```
Date, Season, Home, Visitor, Home_Score, Visitor_Score, Margin, Location, OT
```

### Required Columns
At minimum, your CSV must have:
- `Home` or `HomeTeamRaw` - Home team name
- `Visitor` or `VisitorTeamRaw` - Visiting team name  
- `Home_Score` or `HomeScore` - Home team score
- `Visitor_Score` or `VisitorScore` - Visiting team score

### Optional Columns
- `Date` - Game date (YYYY-MM-DD format)
- `Season` - Year/season (will derive from Date if missing)
- `Neutral` - Neutral site indicator (0 or 1)
- `Location` - Game location
- `Location2` - Secondary location info
- `Line` - Point spread
- `Future_Game` - Future game indicator (0 or 1)
- `OT` or `Overtime` - Overtime periods (0, 1, 2, etc.)
- `Forfeit` - Forfeit indicator (0 or 1)

## Pre-Import Checklist

### 1. Verify CSV File
- [ ] File exists at the specified path
- [ ] File is not open in Excel (close it first!)
- [ ] Headers are in the first row
- [ ] No blank rows at the top

### 2. Data Quality Check
Open the CSV in Excel/Google Sheets and verify:
- [ ] No impossible scores (e.g., 3914)
- [ ] No combined scores in one column
- [ ] No text in score fields
- [ ] Team names are properly formatted
- [ ] Dates are valid (if present)

### 3. Team Name Standardization
If this is historical data, ensure team names match your database standards:
- [ ] Include state suffix: "Team Name (ST)"
- [ ] Use proper capitalization
- [ ] No typos or OCR errors
- [ ] Run alias checking if uncertain (see below)

## Running the Import

### Step 1: Configure the Script

Open `import_yearbook_results.py` and verify these settings:

```python
CSV_FILE = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Yearbook_Results.csv"
SERVER = r'MCKNIGHTS-PC\SQLEXPRESS01'
DATABASE = 'hs_football_database'
SOURCE_NAME = 'Yearbook'  # Change if needed
```

### Step 2: Run the Script

Open PowerShell or Command Prompt:

```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import

python import_yearbook_results.py
```

### Step 3: Review the Output

The script will show:
```
============================================================
Yearbook Results Import Script
============================================================

Step 1: Loading CSV file...
✓ Loaded 1,234 rows from CSV
  Columns found: Date, Home, Visitor, Home_Score, Visitor_Score

Step 2: Sample data preview:
[Shows first 3 rows]

Step 3: Connecting to database...
✓ Connected to database

Step 4: Generating BatchID...
✓ Generated BatchID: 42

Step 5: Standardizing data...
  Detected format: Standard style
  Standardized 1,234 rows

Step 6: Validating data...
✓ Data validation passed

Step 7: Inserting into database...
  Processed 1,000 / 1,234 rows
  Processed 1,234 / 1,234 rows
✓ Inserted 1,234 records

Step 8: Committing transaction...
✓ Transaction committed

============================================================
IMPORT COMPLETE
============================================================
  Records imported: 1,234
  BatchID: 42
  Source: Yearbook
  Date: 2026-01-10 14:30:45
```

### Step 4: Handle Validation Warnings

If validation issues are found:
```
⚠ Data validation warnings:
  ✗ Home has 3 NULL values
  ✗ Found negative scores
Continue with import? (y/n):
```

**Options:**
- Type `n` to cancel and fix the CSV
- Type `y` to proceed anyway (not recommended)

## Post-Import Steps

### 1. Remove Duplicates
```sql
EXEC dbo.RemoveDuplicateGames;
```

### 2. Verify Margin Calculations
```sql
SELECT * FROM dbo.HS_Scores 
WHERE Margin <> (Home_Score - Visitor_Score);
```

If rows are returned, fix them:
```sql
UPDATE dbo.HS_Scores
SET Margin = (Home_Score - Visitor_Score)
WHERE Margin <> (Home_Score - Visitor_Score);
```

### 3. Review Imported Data
Replace `{BatchID}` with the BatchID from the import output:
```sql
SELECT TOP 100 * 
FROM dbo.HS_Scores 
WHERE BatchID = {BatchID}
ORDER BY Date DESC;
```

### 4. Check for Unrecognized Team Names

```sql
-- Find teams in HS_Scores not in HS_Team_Names
SELECT DISTINCT Home AS Team_Name
FROM dbo.HS_Scores
WHERE Home NOT IN (SELECT Team_Name FROM dbo.HS_Team_Names)
  AND BatchID = {BatchID}
UNION
SELECT DISTINCT Visitor AS Team_Name
FROM dbo.HS_Scores
WHERE Visitor NOT IN (SELECT Team_Name FROM dbo.HS_Team_Names)
  AND BatchID = {BatchID}
ORDER BY Team_Name;
```

### 5. Run Alias Resolution (If Needed)

If unrecognized teams are found, use your existing alias workflow:

```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import

python master_scores_importer.py
# Follow the alias resolution workflow
```

## Troubleshooting

### Error: "CSV file not found"
- Verify the path in `CSV_FILE` variable
- Check that OneDrive has synced the file
- Try using the full path without `r""` prefix

### Error: "Database connection failed"
- Ensure SQL Server Express is running
- Verify server name: `MCKNIGHTS-PC\SQLEXPRESS01`
- Check Windows Authentication is enabled

### Error: "Column 'X' not found"
- The script auto-detects columns, but may need adjustment
- Edit the `standardize_data()` function to match your CSV
- Add print statements to see detected columns

### Error: "Excel file is in use"
- Close Excel completely
- Check Task Manager for hidden Excel processes
- Restart if necessary

### Validation Warning: NULL values
- Review the CSV for blank cells
- Decide if you want to:
  - Fix the CSV and re-import
  - Proceed with NULLs (may cause issues later)
  - Filter out incomplete rows

### Validation Warning: Negative scores
- Check for OCR errors (common in newspaper data)
- Verify Home/Visitor columns aren't swapped
- Fix in CSV before importing

## Rollback Procedure

If the import goes wrong:

### Option 1: Delete by BatchID
```sql
DELETE FROM dbo.HS_Scores
WHERE BatchID = {BatchID};
```

### Option 2: Delete by Date and Source
```sql
DELETE FROM dbo.HS_Scores
WHERE Source = 'Yearbook'
  AND Date_Added >= '2026-01-10'  -- Today's date
  AND Date_Added < '2026-01-11';  -- Tomorrow's date
```

### Option 3: Restore from Backup
If you have a recent backup:
```sql
-- Contact DBA or use your backup procedures
```

## Advanced Configuration

### Custom Column Mapping

If your CSV has different column names, edit the `standardize_data()` function:

```python
# Example: Your CSV has "Team1" and "Team2" instead of "Home" and "Visitor"
standardized['Home'] = df['Team1']
standardized['Visitor'] = df['Team2']
```

### Batch Size Adjustment

For very large imports (100K+ rows), increase batch size:

```python
def insert_data(cursor, df, batch_size=5000):  # Changed from 1000
```

### Custom Source Name

Change the source identifier:

```python
SOURCE_NAME = 'Yearbook_1950s'  # More specific
SOURCE_NAME = 'TexasYearbooks'  # State-specific
```

## Data Quality Best Practices

### Before Import
1. **Manual CSV review** - Always scan for obvious errors
2. **Test with small subset** - Import 10-20 rows first
3. **Backup database** - Take snapshot before large imports
4. **Document source** - Note where the data came from

### After Import
1. **Spot check games** - Verify 10-20 random games manually
2. **Run outlier analysis** - Look for statistical anomalies
3. **Check season totals** - Verify game counts per team
4. **Archive CSV** - Move to processed folder

## Related Workflows

- **Newspaper OCR Import**: `Newspaper_OCR_to_Import_to_HS_Scores_Table_Procedure.md`
- **MaxPreps Scraping**: `MaxPreps_Scraping_Workflow.md`
- **LoneStar Import**: `LoneStarFootball.net_Scraping_Workflow.md`
- **Alias Resolution**: `Ambiguous_Opponent_Names_Workflow.md`

## File Locations

- **Import Script**: `C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\import_yearbook_results.py`
- **CSV File**: `C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Yearbook_Results.csv`
- **Backup Location**: `C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Archive\`

## Change Log

- **2026-01-10**: Initial workflow created for Yearbook_Results.csv import
- Script supports auto-detection of CSV format (OCR vs Standard)
- Integrated validation checks and rollback procedures