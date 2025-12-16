# Quick Start Guide: Ambiguous Opponent Names Workflow

## Overview

This workflow helps you identify and correct ambiguous opponent names in your HS_Scores table, such as:
- "Non-Varsity Opponent"
- "Varsity Opponent" 
- "TBD"
- "Unknown Opponent"

These placeholder names from MaxPreps need to be researched and replaced with actual team names.

---

## 🚀 Initial Setup (One-Time)

### Step 1: Run the SQL Setup Script

Open SQL Server Management Studio and run:

```sql
-- File: Setup_Ambiguous_Opponent_Workflow.sql
-- This creates all tables and stored procedures
```

Or from command line:
```cmd
sqlcmd -S MCKNIGHTS-PC\SQLEXPRESS01 -d hs_football_database -i "Setup_Ambiguous_Opponent_Workflow.sql"
```

**What this does:**
- Creates 3 new tables for tracking ambiguous games
- Creates 6 stored procedures for managing the workflow
- Loads default ambiguous name patterns (Non-Varsity Opponent, TBD, etc.)

### Step 2: Verify Setup

```sql
-- Check that tables were created
SELECT * FROM HS_Ambiguous_Name_Patterns;

-- Should show 8 patterns like:
-- Non-Varsity Opponent
-- Varsity Opponent
-- JV Opponent
-- TBD
-- etc.
```

---

## 📋 Regular Workflow

### Step 1: Identify Ambiguous Games

```sql
-- Find all ambiguous games in your database
EXEC sp_Identify_Ambiguous_Games;

-- Or filter by season
EXEC sp_Identify_Ambiguous_Games @Season = 2024;

-- Or filter by source
EXEC sp_Identify_Ambiguous_Games @Source = 'MaxPreps';
```

**Output example:**
```
45 ambiguous games identified and moved to review table.
```

### Step 2: View What Was Found

```sql
-- Get a summary report
EXEC sp_Report_Ambiguous_Games;
```

**Example output:**
```
Summary by Status:
Status      Game_Count  Seasons_Affected  Earliest_Game  Latest_Game
PENDING     45          3                 2022-09-02     2024-11-15

Summary by Ambiguous Name:
Ambiguous_Name          Occurrences  Pending  Researched  Reloaded
Non-Varsity Opponent    32          32       0           0
TBD                     8           8        0           0
Varsity Opponent        5           5        0           0
```

### Step 3: Research Games

#### Option A: Use Python Assistant (Recommended)

```cmd
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts
.\.venv\Scripts\Activate
python research_ambiguous_games.py
```

**Interactive workflow:**
1. Shows you pending games
2. Enter a Review_ID to research
3. Shows context clues (nearby games, locations, score patterns)
4. Enter proposed team name
5. Add research notes
6. Select confidence level
7. Submits to database

**Example session:**
```
🔍 AMBIGUOUS GAMES RESEARCH ASSISTANT
================================================================================

📋 Found 45 pending ambiguous games

Most recent 10:
--------------------------------------------------------------------------------
  [ 123] 2024-09-13 | Buffalo McKinley (NY)                vs Non-Varsity Opponent         | ⚠️ VISITOR
  [ 124] 2024-09-20 | Buffalo Riverside (NY)               vs Non-Varsity Opponent         | ⚠️ VISITOR
  ...

Enter command or Review_ID to research: 123

================================================================================
RESEARCHING: Review ID 123
================================================================================
Date: 2024-09-13
Known Team: Buffalo McKinley (NY)
Ambiguous Name: Non-Varsity Opponent (VISITOR)
Score: 42-14
Margin: 28 points (Known team won)
Location: Not specified
Source: MaxPreps
================================================================================

📅 CONTEXT GAMES (games within ±2 weeks):
--------------------------------------------------------------------------------
  2024-09-06: vs Buffalo Lafayette (NY) (28-21) [MaxPreps]
  2024-09-20: @ Buffalo East (NY) (35-7) [MaxPreps]
  2024-09-27: vs Buffalo South Park (NY) (42-0) [MaxPreps]

🎯 SCORE PATTERN MATCHES:
--------------------------------------------------------------------------------
  No games found with matching scores.

================================================================================

💡 Based on the context above, what is your proposed team name?

Proposed Team Name: Buffalo Kensington (NY)
Research Notes: Based on schedule pattern and score, likely JV team from Kensington
Confidence (HIGH/MEDIUM/LOW) [MEDIUM]: MEDIUM
Your Name (optional): David McKnight

✅ Research submitted for Review_ID 123
   Proposed: Buffalo Kensington (NY)
   Confidence: MEDIUM

📋 44 pending games remaining.
```

#### Option B: Manual SQL Research

```sql
-- View a specific game needing research
SELECT 
    Review_ID,
    Date,
    Home,
    Visitor,
    Home_Score,
    Visitor_Score,
    Ambiguous_Name,
    Ambiguous_Team
FROM HS_Scores_Ambiguous_Review
WHERE Review_ID = 123;

-- Look at nearby games for the known team
SELECT 
    Date,
    Home,
    Visitor,
    Home_Score,
    Visitor_Score
FROM HS_Scores
WHERE (Home = 'Buffalo McKinley (NY)' OR Visitor = 'Buffalo McKinley (NY)')
  AND Date BETWEEN '2024-09-01' AND '2024-09-30'
ORDER BY Date;

-- Submit your research
EXEC sp_Update_Ambiguous_Research
    @Review_ID = 123,
    @Proposed_Team_Name = 'Buffalo Kensington (NY)',
    @Research_Notes = 'Based on schedule pattern and score, likely JV team from Kensington',
    @Confidence_Level = 'MEDIUM',
    @Researched_By = 'David McKnight';
```

### Step 4: Review and Approve

```sql
-- View all researched games ready for approval
SELECT 
    Review_ID,
    Date,
    CASE 
        WHEN Ambiguous_Team = 'HOME' THEN Proposed_Team_Name + ' vs ' + Visitor
        ELSE Home + ' vs ' + Proposed_Team_Name
    END as Corrected_Game,
    Confidence_Level,
    Research_Notes,
    Researched_By
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'RESEARCHED'
ORDER BY Confidence_Level DESC;

-- Approve specific games
EXEC sp_Approve_And_Reload_Ambiguous_Games
    @Review_ID_List = '123,124,125',
    @Approved_By = 'David McKnight';

-- Or approve all HIGH confidence games
EXEC sp_Approve_And_Reload_Ambiguous_Games
    @MinConfidenceLevel = 'HIGH',
    @Approved_By = 'David McKnight';
```

**What this does:**
- Updates the original games in HS_Scores with correct team names
- Marks review records as 'RELOADED'
- Logs all changes in audit table

### Step 5: Verify Corrections

```sql
-- Check that corrections were applied
SELECT 
    s.Date,
    s.Home,
    s.Visitor,
    s.Home_Score,
    s.Visitor_Score,
    r.Ambiguous_Name as Was_Originally
FROM HS_Scores s
INNER JOIN HS_Scores_Ambiguous_Review r ON s.ID = r.Original_Game_ID
WHERE r.Status = 'RELOADED'
  AND r.Review_ID IN (123, 124, 125);
```

---

## 🔍 Research Tips

### Context Clues to Look For

1. **Schedule Patterns**
   - Look at games immediately before/after
   - Week-to-week patterns often reveal opponents

2. **Score Patterns**
   - Large margins might indicate JV games
   - Identical scores in different sources = same game

3. **Location Hints**
   - Neutral site games often indicate tournaments
   - Home field advantage patterns

4. **Source Cross-Reference**
   - Check local newspapers
   - School websites/yearbooks
   - Athletic association records

### Confidence Level Guidelines

- **HIGH**: Multiple confirming sources, no doubt
  - Example: Found in newspaper archives with full details
  
- **MEDIUM**: Strong context clues, one confirming source
  - Example: Schedule pattern strongly suggests opponent
  
- **LOW**: Educated guess based on limited context
  - Example: Only clue is location or score similarity

---

## 📊 Monitoring Progress

### Check Overall Progress

```sql
EXEC sp_Report_Ambiguous_Games;
```

### View Your Research History

```sql
SELECT 
    Researched_By,
    COUNT(*) as Games_Researched,
    COUNT(CASE WHEN Status = 'RELOADED' THEN 1 END) as Approved,
    AVG(CASE 
        WHEN Confidence_Level = 'HIGH' THEN 3
        WHEN Confidence_Level = 'MEDIUM' THEN 2
        ELSE 1
    END) as Avg_Confidence
FROM HS_Scores_Ambiguous_Review
WHERE Researched_By = 'David McKnight'
GROUP BY Researched_By;
```

### View Audit Trail

```sql
-- See all actions for a specific game
SELECT 
    Action,
    Action_By,
    Action_Date,
    Comments
FROM HS_Ambiguous_Resolution_Log
WHERE Review_ID = 123
ORDER BY Action_Date;
```

---

## 🚨 Common Scenarios

### Scenario 1: Can't Identify Opponent

**Solution**: Mark as LOW confidence with best guess
```sql
EXEC sp_Update_Ambiguous_Research
    @Review_ID = 123,
    @Proposed_Team_Name = 'Buffalo Unknown JV (NY)',
    @Research_Notes = 'Unable to identify specific opponent. Score and date suggest local JV team.',
    @Confidence_Level = 'LOW',
    @Researched_By = 'David McKnight';
```

### Scenario 2: Wrong Opponent Proposed

**Solution**: Reject and re-research
```sql
EXEC sp_Reject_Ambiguous_Research
    @Review_ID = 124,
    @Rejection_Reason = 'Proposed team did not exist in 2024. Need to research further.',
    @Rejected_By = 'David McKnight';

-- Game goes back to PENDING status
```

### Scenario 3: All Games Same Pattern

**Solution**: Use batch mode
```cmd
python research_ambiguous_games.py --batch "TBD" "Buffalo Kensington (NY)" "All TBD games this week were vs Kensington" HIGH "David McKnight"
```

### Scenario 4: Add New Ambiguous Pattern

```sql
-- Found a new ambiguous name that MaxPreps uses
INSERT INTO HS_Ambiguous_Name_Patterns (Pattern_Name, Pattern_Type, Source_System, Notes)
VALUES ('Sophomore Opponent', 'EXACT', 'MaxPreps', 'Placeholder for sophomore games');

-- Re-run identification to catch these games
EXEC sp_Identify_Ambiguous_Games;
```

---

## 🎯 Best Practices

1. **Start with HIGH confidence games first**
   - These are the most reliable corrections
   - Build momentum with easy wins

2. **Research in batches by date range**
   - Games from same week often related
   - Context from one game helps others

3. **Document your sources**
   - Add newspaper names, URLs, yearbook pages
   - Future researchers will thank you

4. **Use consistent naming**
   - Follow your existing team name format
   - Include state code: "Team Name (ST)"

5. **Review before bulk approval**
   - Check for duplicates
   - Verify team names exist in HS_Team_Names

---

## 📈 Expected Progress

For a typical MaxPreps import:

| Ambiguous Type | Typical Count | Research Time | Success Rate |
|----------------|---------------|---------------|--------------|
| Non-Varsity Opponent | 40-60% | 5 min/game | 80% HIGH confidence |
| TBD | 20-30% | 10 min/game | 50% MEDIUM confidence |
| Unknown Opponent | 10-20% | 15 min/game | 30% LOW confidence |

**Typical workflow**: 
- 50 ambiguous games identified
- Research session: 2-3 hours
- 30-40 games resolved with HIGH/MEDIUM confidence
- 10-15 games need follow-up research

---

## 🔗 Related Files

- **Workflow Documentation**: `Ambiguous_Opponent_Names_Workflow.md`
- **SQL Setup**: `Setup_Ambiguous_Opponent_Workflow.sql`
- **Python Script**: `research_ambiguous_games.py`

---

## 💡 Questions?

Check the main workflow documentation or review the stored procedure code for more details on how the system works.

**Common queries:**

```sql
-- How many pending games?
SELECT COUNT(*) FROM HS_Scores_Ambiguous_Review WHERE Status = 'PENDING';

-- What are the most common ambiguous names?
SELECT Ambiguous_Name, COUNT(*) as Count
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'PENDING'
GROUP BY Ambiguous_Name
ORDER BY Count DESC;

-- Show me games I can approve now
SELECT Review_ID, Date, Home, Visitor, Proposed_Team_Name, Confidence_Level
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'RESEARCHED'
  AND Confidence_Level = 'HIGH';
```
