# Ambiguous Opponent Names Workflow
## Identifying and Resolving Non-Specific Team Names in HS_Scores

---

## 🎯 Problem Statement

Some data sources (primarily MaxPreps) use generic placeholder names that can refer to multiple different teams:
- "Non-Varsity Opponent"
- "Varsity Opponent"
- "JV Opponent"
- "Unknown Opponent"
- "TBD"

These ambiguous names need to be:
1. **Identified** - Found in the HS_Scores table
2. **Isolated** - Moved to a review table
3. **Researched** - Actual opponent determined through investigation
4. **Corrected** - Proper name assigned
5. **Reloaded** - Moved back to HS_Scores with correct information

---

## 📊 Database Schema

### New Tables Required

```sql
-- Main staging table for ambiguous games
CREATE TABLE HS_Scores_Ambiguous_Review (
    Review_ID INT IDENTITY(1,1) PRIMARY KEY,
    Original_Game_ID UNIQUEIDENTIFIER NOT NULL,  -- Reference to HS_Scores.ID
    Date DATE,
    Season INT,
    Home VARCHAR(111),
    Visitor VARCHAR(111),
    Home_Score INT,
    Visitor_Score INT,
    Margin INT,
    Location VARCHAR(111),
    Location2 VARCHAR(255),
    Source VARCHAR(255),
    
    -- Ambiguity tracking
    Ambiguous_Team VARCHAR(10),              -- 'HOME' or 'VISITOR'
    Ambiguous_Name VARCHAR(111),             -- The placeholder name used
    
    -- Research fields
    Research_Notes VARCHAR(MAX),             -- Investigation notes
    Proposed_Team_Name VARCHAR(111),         -- Proposed correct name
    Confidence_Level VARCHAR(20),            -- 'HIGH', 'MEDIUM', 'LOW'
    Researched_By VARCHAR(100),              -- Who investigated
    Research_Date DATETIME,
    
    -- Resolution tracking
    Status VARCHAR(20) DEFAULT 'PENDING',    -- 'PENDING', 'RESEARCHED', 'APPROVED', 'REJECTED', 'RELOADED'
    Approved_By VARCHAR(100),
    Approval_Date DATETIME,
    Reload_Date DATETIME,
    
    Date_Added DATETIME DEFAULT GETDATE(),
    Last_Modified DATETIME DEFAULT GETDATE()
);

-- Lookup table for known ambiguous names
CREATE TABLE HS_Ambiguous_Name_Patterns (
    Pattern_ID INT IDENTITY(1,1) PRIMARY KEY,
    Pattern_Name VARCHAR(111),               -- The ambiguous name to look for
    Pattern_Type VARCHAR(50),                -- 'EXACT', 'CONTAINS', 'STARTS_WITH', 'ENDS_WITH'
    Source_System VARCHAR(100),              -- 'MaxPreps', 'LoneStarFootball', etc.
    Is_Active BIT DEFAULT 1,
    Date_Added DATETIME DEFAULT GETDATE(),
    Notes VARCHAR(500)
);

-- Audit log for tracking all changes
CREATE TABLE HS_Ambiguous_Resolution_Log (
    Log_ID INT IDENTITY(1,1) PRIMARY KEY,
    Review_ID INT,
    Action VARCHAR(50),                      -- 'IDENTIFIED', 'RESEARCHED', 'APPROVED', 'REJECTED', 'RELOADED'
    Action_By VARCHAR(100),
    Action_Date DATETIME DEFAULT GETDATE(),
    Old_Value VARCHAR(MAX),
    New_Value VARCHAR(MAX),
    Comments VARCHAR(MAX)
);

-- Index for performance
CREATE INDEX IX_Ambiguous_Review_Status ON HS_Scores_Ambiguous_Review(Status);
CREATE INDEX IX_Ambiguous_Review_OriginalID ON HS_Scores_Ambiguous_Review(Original_Game_ID);
```

---

## 🔧 Stored Procedures

### 1. Initialize Ambiguous Name Patterns

```sql
CREATE PROCEDURE sp_Initialize_Ambiguous_Patterns
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Clear existing patterns if reinitializing
    TRUNCATE TABLE HS_Ambiguous_Name_Patterns;
    
    -- Insert known ambiguous patterns from MaxPreps
    INSERT INTO HS_Ambiguous_Name_Patterns (Pattern_Name, Pattern_Type, Source_System, Notes)
    VALUES 
        ('Non-Varsity Opponent', 'EXACT', 'MaxPreps', 'Generic placeholder for non-varsity teams'),
        ('Varsity Opponent', 'EXACT', 'MaxPreps', 'Generic placeholder for varsity teams'),
        ('JV Opponent', 'EXACT', 'MaxPreps', 'Generic placeholder for JV teams'),
        ('Unknown Opponent', 'EXACT', 'MaxPreps', 'Placeholder when opponent unknown'),
        ('TBD', 'EXACT', 'MaxPreps', 'To Be Determined - future game'),
        ('To Be Determined', 'EXACT', 'MaxPreps', 'Future game not yet scheduled'),
        ('%Opponent', 'ENDS_WITH', 'MaxPreps', 'Catches variants like "Sophomore Opponent"'),
        ('Unknown%', 'STARTS_WITH', 'MaxPreps', 'Catches variants like "Unknown Team"');
    
    PRINT 'Ambiguous name patterns initialized.';
END;
GO
```

### 2. Identify and Extract Ambiguous Games

```sql
CREATE PROCEDURE sp_Identify_Ambiguous_Games
    @Season INT = NULL,  -- Optional: filter by season
    @Source VARCHAR(255) = NULL  -- Optional: filter by source
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @GamesIdentified INT = 0;
    
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Find games with ambiguous HOME team
        INSERT INTO HS_Scores_Ambiguous_Review (
            Original_Game_ID, Date, Season, Home, Visitor,
            Home_Score, Visitor_Score, Margin, Location, Location2, Source,
            Ambiguous_Team, Ambiguous_Name, Status
        )
        SELECT 
            s.ID,
            s.Date,
            s.Season,
            s.Home,
            s.Visitor,
            s.Home_Score,
            s.Visitor_Score,
            s.Margin,
            s.Location,
            s.Location2,
            s.Source,
            'HOME' as Ambiguous_Team,
            s.Home as Ambiguous_Name,
            'PENDING' as Status
        FROM HS_Scores s
        INNER JOIN HS_Ambiguous_Name_Patterns p ON p.Is_Active = 1
        WHERE 
            -- Match pattern based on type
            (p.Pattern_Type = 'EXACT' AND s.Home = p.Pattern_Name)
            OR (p.Pattern_Type = 'CONTAINS' AND s.Home LIKE '%' + p.Pattern_Name + '%')
            OR (p.Pattern_Type = 'STARTS_WITH' AND s.Home LIKE p.Pattern_Name + '%')
            OR (p.Pattern_Type = 'ENDS_WITH' AND s.Home LIKE '%' + p.Pattern_Name)
            -- Optional filters
            AND (@Season IS NULL OR s.Season = @Season)
            AND (@Source IS NULL OR s.Source LIKE '%' + @Source + '%')
            -- Don't re-identify already reviewed games
            AND s.ID NOT IN (SELECT Original_Game_ID FROM HS_Scores_Ambiguous_Review);
        
        SET @GamesIdentified = @GamesIdentified + @@ROWCOUNT;
        
        -- Find games with ambiguous VISITOR team
        INSERT INTO HS_Scores_Ambiguous_Review (
            Original_Game_ID, Date, Season, Home, Visitor,
            Home_Score, Visitor_Score, Margin, Location, Location2, Source,
            Ambiguous_Team, Ambiguous_Name, Status
        )
        SELECT 
            s.ID,
            s.Date,
            s.Season,
            s.Home,
            s.Visitor,
            s.Home_Score,
            s.Visitor_Score,
            s.Margin,
            s.Location,
            s.Location2,
            s.Source,
            'VISITOR' as Ambiguous_Team,
            s.Visitor as Ambiguous_Name,
            'PENDING' as Status
        FROM HS_Scores s
        INNER JOIN HS_Ambiguous_Name_Patterns p ON p.Is_Active = 1
        WHERE 
            -- Match pattern based on type
            (p.Pattern_Type = 'EXACT' AND s.Visitor = p.Pattern_Name)
            OR (p.Pattern_Type = 'CONTAINS' AND s.Visitor LIKE '%' + p.Pattern_Name + '%')
            OR (p.Pattern_Type = 'STARTS_WITH' AND s.Visitor LIKE p.Pattern_Name + '%')
            OR (p.Pattern_Type = 'ENDS_WITH' AND s.Visitor LIKE '%' + p.Pattern_Name)
            -- Optional filters
            AND (@Season IS NULL OR s.Season = @Season)
            AND (@Source IS NULL OR s.Source LIKE '%' + @Source + '%')
            -- Don't re-identify already reviewed games
            AND s.ID NOT IN (SELECT Original_Game_ID FROM HS_Scores_Ambiguous_Review);
        
        SET @GamesIdentified = @GamesIdentified + @@ROWCOUNT;
        
        -- Log the identification action
        INSERT INTO HS_Ambiguous_Resolution_Log (Review_ID, Action, Action_By, Comments)
        SELECT 
            Review_ID,
            'IDENTIFIED',
            SYSTEM_USER,
            'Automated identification run for Season: ' + ISNULL(CAST(@Season AS VARCHAR), 'ALL') + 
            ', Source: ' + ISNULL(@Source, 'ALL')
        FROM HS_Scores_Ambiguous_Review
        WHERE Review_ID NOT IN (SELECT Review_ID FROM HS_Ambiguous_Resolution_Log WHERE Action = 'IDENTIFIED');
        
        COMMIT TRANSACTION;
        
        PRINT CAST(@GamesIdentified AS VARCHAR) + ' ambiguous games identified and moved to review table.';
        
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO
```

### 3. Update Research Findings

```sql
CREATE PROCEDURE sp_Update_Ambiguous_Research
    @Review_ID INT,
    @Proposed_Team_Name VARCHAR(111),
    @Research_Notes VARCHAR(MAX),
    @Confidence_Level VARCHAR(20) = 'MEDIUM',
    @Researched_By VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Validate inputs
    IF @Review_ID IS NULL OR @Proposed_Team_Name IS NULL
    BEGIN
        RAISERROR('Review_ID and Proposed_Team_Name are required.', 16, 1);
        RETURN;
    END
    
    IF @Confidence_Level NOT IN ('HIGH', 'MEDIUM', 'LOW')
    BEGIN
        RAISERROR('Confidence_Level must be HIGH, MEDIUM, or LOW.', 16, 1);
        RETURN;
    END
    
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Get old values for logging
        DECLARE @OldProposedName VARCHAR(111);
        DECLARE @OldNotes VARCHAR(MAX);
        
        SELECT 
            @OldProposedName = Proposed_Team_Name,
            @OldNotes = Research_Notes
        FROM HS_Scores_Ambiguous_Review
        WHERE Review_ID = @Review_ID;
        
        -- Update the review record
        UPDATE HS_Scores_Ambiguous_Review
        SET 
            Proposed_Team_Name = @Proposed_Team_Name,
            Research_Notes = @Research_Notes,
            Confidence_Level = @Confidence_Level,
            Researched_By = ISNULL(@Researched_By, SYSTEM_USER),
            Research_Date = GETDATE(),
            Status = 'RESEARCHED',
            Last_Modified = GETDATE()
        WHERE Review_ID = @Review_ID;
        
        -- Log the research action
        INSERT INTO HS_Ambiguous_Resolution_Log (Review_ID, Action, Action_By, Old_Value, New_Value, Comments)
        VALUES (
            @Review_ID,
            'RESEARCHED',
            ISNULL(@Researched_By, SYSTEM_USER),
            'Proposed: ' + ISNULL(@OldProposedName, 'NULL') + ' | Notes: ' + ISNULL(@OldNotes, 'NULL'),
            'Proposed: ' + @Proposed_Team_Name + ' | Notes: ' + @Research_Notes,
            'Confidence: ' + @Confidence_Level
        );
        
        COMMIT TRANSACTION;
        
        PRINT 'Research findings updated for Review_ID: ' + CAST(@Review_ID AS VARCHAR);
        
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@ErrorMessage, 16, 1);
    END CATCH
END;
GO
```

### 4. Approve and Reload Corrected Games

```sql
CREATE PROCEDURE sp_Approve_And_Reload_Ambiguous_Games
    @Review_ID_List VARCHAR(MAX) = NULL,  -- Comma-separated list of Review_IDs, or NULL for all RESEARCHED
    @Approved_By VARCHAR(100) = NULL,
    @MinConfidenceLevel VARCHAR(20) = 'MEDIUM'  -- Only reload HIGH or MEDIUM confidence
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @GamesReloaded INT = 0;
    
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Create temp table for IDs to process
        CREATE TABLE #IDs_To_Process (Review_ID INT);
        
        IF @Review_ID_List IS NOT NULL
        BEGIN
            -- Parse comma-separated list
            INSERT INTO #IDs_To_Process (Review_ID)
            SELECT CAST(value AS INT)
            FROM STRING_SPLIT(@Review_ID_List, ',');
        END
        ELSE
        BEGIN
            -- Process all RESEARCHED records that meet confidence criteria
            INSERT INTO #IDs_To_Process (Review_ID)
            SELECT Review_ID
            FROM HS_Scores_Ambiguous_Review
            WHERE Status = 'RESEARCHED'
              AND Proposed_Team_Name IS NOT NULL
              AND (
                  (@MinConfidenceLevel = 'LOW') OR
                  (@MinConfidenceLevel = 'MEDIUM' AND Confidence_Level IN ('MEDIUM', 'HIGH')) OR
                  (@MinConfidenceLevel = 'HIGH' AND Confidence_Level = 'HIGH')
              );
        END
        
        -- Update original games in HS_Scores
        UPDATE s
        SET 
            Home = CASE WHEN r.Ambiguous_Team = 'HOME' THEN r.Proposed_Team_Name ELSE s.Home END,
            Visitor = CASE WHEN r.Ambiguous_Team = 'VISITOR' THEN r.Proposed_Team_Name ELSE s.Visitor END
        FROM HS_Scores s
        INNER JOIN HS_Scores_Ambiguous_Review r ON s.ID = r.Original_Game_ID
        INNER JOIN #IDs_To_Process i ON r.Review_ID = i.Review_ID
        WHERE r.Status = 'RESEARCHED';
        
        SET @GamesReloaded = @@ROWCOUNT;
        
        -- Update review table status
        UPDATE r
        SET 
            Status = 'RELOADED',
            Approved_By = ISNULL(@Approved_By, SYSTEM_USER),
            Approval_Date = GETDATE(),
            Reload_Date = GETDATE(),
            Last_Modified = GETDATE()
        FROM HS_Scores_Ambiguous_Review r
        INNER JOIN #IDs_To_Process i ON r.Review_ID = i.Review_ID;
        
        -- Log the reload action
        INSERT INTO HS_Ambiguous_Resolution_Log (Review_ID, Action, Action_By, New_Value, Comments)
        SELECT 
            r.Review_ID,
            'RELOADED',
            ISNULL(@Approved_By, SYSTEM_USER),
            r.Ambiguous_Team + ' changed to: ' + r.Proposed_Team_Name,
            'Original game ID: ' + CAST(r.Original_Game_ID AS VARCHAR)
        FROM HS_Scores_Ambiguous_Review r
        INNER JOIN #IDs_To_Process i ON r.Review_ID = i.Review_ID;
        
        DROP TABLE #IDs_To_Process;
        
        COMMIT TRANSACTION;
        
        PRINT CAST(@GamesReloaded AS VARCHAR) + ' games reloaded with corrected team names.';
        
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@ErrorMessage, 16, 1);
    END CATCH
END;
GO
```

### 5. Reject Incorrect Research

```sql
CREATE PROCEDURE sp_Reject_Ambiguous_Research
    @Review_ID INT,
    @Rejection_Reason VARCHAR(MAX),
    @Rejected_By VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Update review record
        UPDATE HS_Scores_Ambiguous_Review
        SET 
            Status = 'REJECTED',
            Research_Notes = ISNULL(Research_Notes, '') + CHAR(13) + CHAR(10) + 
                           '--- REJECTED ---' + CHAR(13) + CHAR(10) + @Rejection_Reason,
            Last_Modified = GETDATE()
        WHERE Review_ID = @Review_ID;
        
        -- Log the rejection
        INSERT INTO HS_Ambiguous_Resolution_Log (Review_ID, Action, Action_By, Comments)
        VALUES (
            @Review_ID,
            'REJECTED',
            ISNULL(@Rejected_By, SYSTEM_USER),
            @Rejection_Reason
        );
        
        COMMIT TRANSACTION;
        
        PRINT 'Research rejected for Review_ID: ' + CAST(@Review_ID AS VARCHAR);
        
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@ErrorMessage, 16, 1);
    END CATCH
END;
GO
```

### 6. View Summary Report

```sql
CREATE PROCEDURE sp_Report_Ambiguous_Games
    @Status VARCHAR(20) = NULL  -- Optional: filter by status
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Summary by status
    SELECT 
        Status,
        COUNT(*) as Game_Count,
        COUNT(DISTINCT Season) as Seasons_Affected,
        MIN(Date) as Earliest_Game,
        MAX(Date) as Latest_Game
    FROM HS_Scores_Ambiguous_Review
    WHERE @Status IS NULL OR Status = @Status
    GROUP BY Status
    ORDER BY Status;
    
    -- Summary by ambiguous name pattern
    SELECT 
        Ambiguous_Name,
        COUNT(*) as Occurrences,
        COUNT(CASE WHEN Status = 'PENDING' THEN 1 END) as Pending,
        COUNT(CASE WHEN Status = 'RESEARCHED' THEN 1 END) as Researched,
        COUNT(CASE WHEN Status = 'APPROVED' THEN 1 END) as Approved,
        COUNT(CASE WHEN Status = 'RELOADED' THEN 1 END) as Reloaded
    FROM HS_Scores_Ambiguous_Review
    WHERE @Status IS NULL OR Status = @Status
    GROUP BY Ambiguous_Name
    ORDER BY Occurrences DESC;
    
    -- Summary by season
    SELECT 
        Season,
        COUNT(*) as Game_Count,
        COUNT(CASE WHEN Status = 'PENDING' THEN 1 END) as Pending,
        COUNT(CASE WHEN Status = 'RESEARCHED' THEN 1 END) as Researched,
        COUNT(CASE WHEN Status = 'RELOADED' THEN 1 END) as Reloaded
    FROM HS_Scores_Ambiguous_Review
    WHERE @Status IS NULL OR Status = @Status
    GROUP BY Season
    ORDER BY Season DESC;
END;
GO
```

---

## 🐍 Python Research Assistant

This script helps investigate ambiguous games by looking at context clues.

```python
import pyodbc
import pandas as pd
from datetime import datetime, timedelta

# Database connection
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)

def get_pending_ambiguous_games(limit=10):
    """Retrieve pending ambiguous games for research."""
    query = """
        SELECT TOP {limit}
            Review_ID,
            Date,
            Season,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Location,
            Location2,
            Source,
            Ambiguous_Team,
            Ambiguous_Name
        FROM HS_Scores_Ambiguous_Review
        WHERE Status = 'PENDING'
        ORDER BY Date DESC
    """.format(limit=limit)
    
    conn = pyodbc.connect(conn_str)
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

def get_context_games(known_team, game_date, days_window=14):
    """
    Find other games involving the known team around the same date.
    This helps identify the likely opponent based on schedule patterns.
    """
    query = """
        SELECT 
            Date,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Source
        FROM HS_Scores
        WHERE 
            (Home = ? OR Visitor = ?)
            AND Date BETWEEN DATEADD(DAY, -{days}, ?) AND DATEADD(DAY, {days}, ?)
            AND Date != ?
        ORDER BY Date
    """.format(days=days_window)
    
    conn = pyodbc.connect(conn_str)
    df = pd.read_sql(query, conn, params=[known_team, known_team, game_date, game_date, game_date])
    conn.close()
    
    return df

def get_location_hints(location, location2, season):
    """
    Find teams that commonly play at a given location.
    Useful for neutral site games or when location is specified.
    """
    if not location and not location2:
        return pd.DataFrame()
    
    location_pattern = location or location2
    
    query = """
        SELECT 
            Home,
            Visitor,
            COUNT(*) as Times_At_Location
        FROM HS_Scores
        WHERE 
            (Location LIKE ? OR Location2 LIKE ?)
            AND Season BETWEEN ? - 2 AND ? + 2
        GROUP BY Home, Visitor
        HAVING COUNT(*) > 1
        ORDER BY Times_At_Location DESC
    """
    
    conn = pyodbc.connect(conn_str)
    df = pd.read_sql(query, conn, params=[
        f'%{location_pattern}%', 
        f'%{location_pattern}%',
        season,
        season
    ])
    conn.close()
    
    return df

def get_score_pattern_matches(score, opponent_score, season, known_team):
    """
    Find games with identical scores involving similar teams.
    Helps identify opponent when multiple sources report same game.
    """
    query = """
        SELECT 
            Date,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Source
        FROM HS_Scores
        WHERE 
            ((Home_Score = ? AND Visitor_Score = ?) OR (Home_Score = ? AND Visitor_Score = ?))
            AND Season = ?
            AND (Home = ? OR Visitor = ?)
        ORDER BY Date
    """
    
    conn = pyodbc.connect(conn_str)
    df = pd.read_sql(query, conn, params=[
        score, opponent_score,
        opponent_score, score,
        season,
        known_team, known_team
    ])
    conn.close()
    
    return df

def research_ambiguous_game(review_id):
    """
    Main research function that gathers all context for an ambiguous game.
    """
    # Get the ambiguous game details
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            Review_ID,
            Date,
            Season,
            Home,
            Visitor,
            Home_Score,
            Visitor_Score,
            Location,
            Location2,
            Source,
            Ambiguous_Team,
            Ambiguous_Name
        FROM HS_Scores_Ambiguous_Review
        WHERE Review_ID = ?
    """, (review_id,))
    
    game = cursor.fetchone()
    conn.close()
    
    if not game:
        print(f"No game found with Review_ID: {review_id}")
        return None
    
    # Extract game details
    review_id, date, season, home, visitor, home_score, visitor_score, \
        location, location2, source, ambiguous_team, ambiguous_name = game
    
    # Determine which team is known
    known_team = visitor if ambiguous_team == 'HOME' else home
    ambiguous_score = home_score if ambiguous_team == 'HOME' else visitor_score
    known_score = visitor_score if ambiguous_team == 'HOME' else home_score
    
    print("\n" + "="*80)
    print(f"RESEARCHING: Review ID {review_id}")
    print("="*80)
    print(f"Date: {date}")
    print(f"Known Team: {known_team}")
    print(f"Ambiguous Name: {ambiguous_name} ({ambiguous_team})")
    print(f"Score: {home_score}-{visitor_score}")
    print(f"Location: {location or location2 or 'Not specified'}")
    print(f"Source: {source}")
    print("="*80)
    
    # Gather context
    print("\n📅 CONTEXT GAMES (nearby dates):")
    context_games = get_context_games(known_team, date)
    if not context_games.empty:
        print(context_games.to_string())
    else:
        print("  No other games found for this team in the date window.")
    
    print("\n📍 LOCATION HINTS:")
    location_hints = get_location_hints(location, location2, season)
    if not location_hints.empty:
        print(location_hints.head(10).to_string())
    else:
        print("  No location patterns found.")
    
    print("\n🎯 SCORE PATTERN MATCHES:")
    score_matches = get_score_pattern_matches(home_score, visitor_score, season, known_team)
    if not score_matches.empty:
        print(score_matches.to_string())
    else:
        print("  No games found with matching scores.")
    
    print("\n" + "="*80)
    
    return {
        'review_id': review_id,
        'date': date,
        'season': season,
        'known_team': known_team,
        'ambiguous_name': ambiguous_name,
        'context_games': context_games,
        'location_hints': location_hints,
        'score_matches': score_matches
    }

def submit_research(review_id, proposed_name, notes, confidence='MEDIUM', researcher=None):
    """
    Submit research findings to the database.
    """
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            EXEC sp_Update_Ambiguous_Research 
                @Review_ID = ?,
                @Proposed_Team_Name = ?,
                @Research_Notes = ?,
                @Confidence_Level = ?,
                @Researched_By = ?
        """, (review_id, proposed_name, notes, confidence, researcher))
        
        conn.commit()
        print(f"✅ Research submitted for Review_ID {review_id}")
        print(f"   Proposed: {proposed_name}")
        print(f"   Confidence: {confidence}")
        
    except Exception as e:
        print(f"❌ Error submitting research: {e}")
        conn.rollback()
    finally:
        conn.close()

# Interactive research workflow
def interactive_research_session():
    """
    Run an interactive session to research pending ambiguous games.
    """
    print("\n🔍 AMBIGUOUS GAMES RESEARCH ASSISTANT")
    print("="*80)
    
    # Get pending games
    pending = get_pending_ambiguous_games(limit=50)
    
    if pending.empty:
        print("✅ No pending ambiguous games to research!")
        return
    
    print(f"\n📊 Found {len(pending)} pending ambiguous games")
    print("\nFirst 10:")
    print(pending.head(10)[['Review_ID', 'Date', 'Home', 'Visitor', 'Ambiguous_Name']].to_string())
    
    while True:
        print("\n" + "="*80)
        choice = input("\nEnter Review_ID to research (or 'quit' to exit): ").strip()
        
        if choice.lower() in ['quit', 'q', 'exit']:
            break
        
        try:
            review_id = int(choice)
            research_data = research_ambiguous_game(review_id)
            
            if research_data:
                print("\n💡 Based on the context above, what is your proposed team name?")
                proposed = input("Proposed Team Name (or 'skip'): ").strip()
                
                if proposed.lower() not in ['skip', 's', '']:
                    notes = input("Research Notes: ").strip()
                    confidence = input("Confidence (HIGH/MEDIUM/LOW) [MEDIUM]: ").strip().upper() or 'MEDIUM'
                    
                    if confidence not in ['HIGH', 'MEDIUM', 'LOW']:
                        confidence = 'MEDIUM'
                    
                    researcher = input("Your Name (optional): ").strip() or None
                    
                    submit_research(review_id, proposed, notes, confidence, researcher)
                    
        except ValueError:
            print("❌ Invalid Review_ID. Please enter a number.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    interactive_research_session()
```

---

## 📋 Workflow Steps

### Initial Setup (One-time)

```sql
-- 1. Create all tables
-- Run the CREATE TABLE statements from the Database Schema section above

-- 2. Initialize ambiguous name patterns
EXEC sp_Initialize_Ambiguous_Patterns;

-- 3. Verify patterns were loaded
SELECT * FROM HS_Ambiguous_Name_Patterns;
```

### Regular Workflow

#### Step 1: Identify Ambiguous Games

```sql
-- Run identification for all games
EXEC sp_Identify_Ambiguous_Games;

-- Or filter by season
EXEC sp_Identify_Ambiguous_Games @Season = 2024;

-- Or filter by source
EXEC sp_Identify_Ambiguous_Games @Source = 'MaxPreps';

-- Check what was found
EXEC sp_Report_Ambiguous_Games;
```

#### Step 2: Research and Correct

```python
# Run the Python research assistant
python research_ambiguous_games.py

# This will launch an interactive session where you can:
# 1. View pending games
# 2. Select a game to research
# 3. See context clues (nearby games, locations, scores)
# 4. Submit your findings
```

**Manual SQL Alternative:**

```sql
-- View games needing research
SELECT 
    Review_ID,
    Date,
    CASE 
        WHEN Ambiguous_Team = 'HOME' THEN Visitor + ' vs ' + Ambiguous_Name
        ELSE Ambiguous_Name + ' @ ' + Home
    END as Game_Description,
    Home_Score,
    Visitor_Score,
    Location,
    Source
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'PENDING'
ORDER BY Date DESC;

-- Submit research findings manually
EXEC sp_Update_Ambiguous_Research
    @Review_ID = 123,
    @Proposed_Team_Name = 'Buffalo Kensington (NY)',
    @Research_Notes = 'Found in Buffalo News archives - game was actually against Kensington JV team',
    @Confidence_Level = 'HIGH',
    @Researched_By = 'David McKnight';
```

#### Step 3: Review and Approve

```sql
-- View researched games ready for approval
SELECT 
    Review_ID,
    Date,
    CASE 
        WHEN Ambiguous_Team = 'HOME' THEN Proposed_Team_Name + ' vs ' + Visitor
        ELSE Home + ' vs ' + Proposed_Team_Name
    END as Corrected_Game,
    Ambiguous_Name as Old_Name,
    Confidence_Level,
    Research_Notes,
    Researched_By
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'RESEARCHED'
ORDER BY Confidence_Level DESC, Date DESC;

-- Approve specific games
EXEC sp_Approve_And_Reload_Ambiguous_Games
    @Review_ID_List = '123,124,125',
    @Approved_By = 'David McKnight';

-- Or approve all HIGH confidence games
EXEC sp_Approve_And_Reload_Ambiguous_Games
    @MinConfidenceLevel = 'HIGH',
    @Approved_By = 'David McKnight';
```

#### Step 4: Handle Rejections

```sql
-- Reject incorrect research
EXEC sp_Reject_Ambiguous_Research
    @Review_ID = 126,
    @Rejection_Reason = 'Proposed team does not exist in that state during that season',
    @Rejected_By = 'David McKnight';

-- Rejected games return to PENDING and can be re-researched
```

#### Step 5: Monitor Progress

```sql
-- Overall summary
EXEC sp_Report_Ambiguous_Games;

-- Detailed status report
SELECT 
    Status,
    COUNT(*) as Count,
    AVG(CASE 
        WHEN Confidence_Level = 'HIGH' THEN 3
        WHEN Confidence_Level = 'MEDIUM' THEN 2
        WHEN Confidence_Level = 'LOW' THEN 1
    END) as Avg_Confidence_Score
FROM HS_Scores_Ambiguous_Review
GROUP BY Status;

-- View audit trail for a specific game
SELECT 
    Log_ID,
    Action,
    Action_By,
    Action_Date,
    Comments
FROM HS_Ambiguous_Resolution_Log
WHERE Review_ID = 123
ORDER BY Action_Date;
```

---

## 🎯 Quality Control Queries

### Find Potential Issues

```sql
-- Games that might have been missed (check for common patterns)
SELECT 
    ID,
    Date,
    Season,
    Home,
    Visitor,
    Source
FROM HS_Scores
WHERE 
    (Home LIKE '%opponent%' OR Visitor LIKE '%opponent%')
    OR (Home LIKE '%TBD%' OR Visitor LIKE '%TBD%')
    OR (Home LIKE '%unknown%' OR Visitor LIKE '%unknown%')
    AND ID NOT IN (SELECT Original_Game_ID FROM HS_Scores_Ambiguous_Review);

-- Games with suspiciously generic names
SELECT 
    ID,
    Date,
    Home,
    Visitor,
    Source
FROM HS_Scores
WHERE 
    (LEN(Home) < 5 OR LEN(Visitor) < 5)
    AND Source LIKE '%MaxPreps%'
    AND ID NOT IN (SELECT Original_Game_ID FROM HS_Scores_Ambiguous_Review);
```

### Validate Corrections

```sql
-- Check that proposed names exist in HS_Team_Names
SELECT 
    r.Review_ID,
    r.Proposed_Team_Name,
    r.Status
FROM HS_Scores_Ambiguous_Review r
WHERE 
    r.Status = 'RESEARCHED'
    AND r.Proposed_Team_Name NOT IN (SELECT Team_Name FROM HS_Team_Names);

-- Find duplicates that might be created by corrections
SELECT 
    Date,
    Home,
    Visitor,
    Home_Score,
    Visitor_Score,
    COUNT(*) as Duplicate_Count
FROM (
    SELECT 
        s.Date,
        CASE WHEN r.Ambiguous_Team = 'HOME' THEN r.Proposed_Team_Name ELSE s.Home END as Home,
        CASE WHEN r.Ambiguous_Team = 'VISITOR' THEN r.Proposed_Team_Name ELSE s.Visitor END as Visitor,
        s.Home_Score,
        s.Visitor_Score
    FROM HS_Scores s
    INNER JOIN HS_Scores_Ambiguous_Review r ON s.ID = r.Original_Game_ID
    WHERE r.Status = 'RESEARCHED'
) corrected
GROUP BY Date, Home, Visitor, Home_Score, Visitor_Score
HAVING COUNT(*) > 1;
```

---

## 📊 Reporting Queries

### Progress Dashboard

```sql
-- Overall progress metrics
SELECT 
    'Total Identified' as Metric,
    COUNT(*) as Value
FROM HS_Scores_Ambiguous_Review

UNION ALL

SELECT 
    'Pending Research',
    COUNT(*)
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'PENDING'

UNION ALL

SELECT 
    'Researched',
    COUNT(*)
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'RESEARCHED'

UNION ALL

SELECT 
    'Reloaded to HS_Scores',
    COUNT(*)
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'RELOADED'

UNION ALL

SELECT 
    'Rejected',
    COUNT(*)
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'REJECTED';

-- Completion percentage
SELECT 
    CAST(COUNT(CASE WHEN Status = 'RELOADED' THEN 1 END) * 100.0 / COUNT(*) AS DECIMAL(5,2)) as Completion_Percentage
FROM HS_Scores_Ambiguous_Review;
```

### Export for Review

```sql
-- Export pending games to CSV for external research
SELECT 
    Review_ID,
    Date,
    Season,
    Home,
    Visitor,
    Home_Score,
    Visitor_Score,
    Location,
    Location2,
    Source,
    Ambiguous_Team,
    Ambiguous_Name
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'PENDING'
ORDER BY Date DESC;
```

---

## 🔧 Maintenance

### Add New Ambiguous Patterns

```sql
-- Add a new pattern you discovered
INSERT INTO HS_Ambiguous_Name_Patterns (Pattern_Name, Pattern_Type, Source_System, Notes)
VALUES ('Sophomore Opponent', 'EXACT', 'MaxPreps', 'Placeholder for sophomore team games');

-- Re-run identification to catch games with the new pattern
EXEC sp_Identify_Ambiguous_Games;
```

### Clean Up Completed Work

```sql
-- Archive reloaded games (optional - keep for audit trail)
-- Only run this if you want to clean up the review table
/*
DELETE FROM HS_Scores_Ambiguous_Review
WHERE Status = 'RELOADED'
  AND Reload_Date < DATEADD(MONTH, -6, GETDATE());
*/

-- Better approach: Create an archive table
SELECT *
INTO HS_Scores_Ambiguous_Review_Archive
FROM HS_Scores_Ambiguous_Review
WHERE Status = 'RELOADED'
  AND Reload_Date < DATEADD(MONTH, -6, GETDATE());
```

---

## 💡 Research Tips

### Context Clues to Look For

1. **Schedule Patterns**: Look at games before/after to identify opponent
2. **Location**: Neutral site games often indicate specific opponents
3. **Score Patterns**: Same score in multiple sources likely same game
4. **Source Cross-Reference**: Check newspapers, team websites, local archives
5. **Historical Context**: Tournament games, rivalry weeks, playoff matchups

### External Research Resources

- **MaxPreps archives**: Often has corrected names in later updates
- **Local newspapers**: Via Newspapers.com or Google News Archive
- **Team websites**: Historical schedules and records
- **Athletic associations**: State/regional athletic association records
- **School yearbooks**: Often list complete schedules

### Confidence Level Guidelines

- **HIGH**: Multiple confirming sources, no ambiguity
- **MEDIUM**: Strong context clues, one confirming source
- **LOW**: Educated guess based on limited context

---

## 🚨 Common Issues

### Issue: Too Many False Positives

**Solution**: Refine your ambiguous name patterns

```sql
-- Disable overly broad patterns
UPDATE HS_Ambiguous_Name_Patterns
SET Is_Active = 0
WHERE Pattern_Name = '%Opponent%';  -- Too broad

-- Add more specific patterns instead
INSERT INTO HS_Ambiguous_Name_Patterns (Pattern_Name, Pattern_Type, Source_System)
VALUES 
    ('Non-Varsity Opponent', 'EXACT', 'MaxPreps'),
    ('Varsity Opponent', 'EXACT', 'MaxPreps'),
    ('JV Opponent', 'EXACT', 'MaxPreps');
```

### Issue: Can't Find Correct Opponent

**Strategy**:
1. Mark as LOW confidence with best guess
2. Add detailed research notes explaining uncertainty
3. Continue with other games
4. Come back later with fresh perspective or new sources

### Issue: Duplicate Games After Correction

**Prevention**:
```sql
-- Before approving, check for potential duplicates
SELECT 
    Date,
    Home,
    Visitor,
    COUNT(*) as Occurrences
FROM (
    -- Simulated corrected state
    SELECT 
        s.Date,
        CASE WHEN r.Ambiguous_Team = 'HOME' AND r.Review_ID = @YourReviewID 
             THEN r.Proposed_Team_Name ELSE s.Home END as Home,
        CASE WHEN r.Ambiguous_Team = 'VISITOR' AND r.Review_ID = @YourReviewID 
             THEN r.Proposed_Team_Name ELSE s.Visitor END as Visitor
    FROM HS_Scores s
    LEFT JOIN HS_Scores_Ambiguous_Review r ON s.ID = r.Original_Game_ID
) simulated
GROUP BY Date, Home, Visitor
HAVING COUNT(*) > 1;
```

---

## 📈 Success Metrics

Track your progress:

```sql
-- Weekly progress report
SELECT 
    DATEPART(WEEK, Research_Date) as Week_Number,
    COUNT(*) as Games_Researched,
    AVG(CASE 
        WHEN Confidence_Level = 'HIGH' THEN 3
        WHEN Confidence_Level = 'MEDIUM' THEN 2
        ELSE 1
    END) as Avg_Confidence
FROM HS_Scores_Ambiguous_Review
WHERE Research_Date >= DATEADD(WEEK, -8, GETDATE())
GROUP BY DATEPART(WEEK, Research_Date)
ORDER BY Week_Number DESC;

-- Researcher performance
SELECT 
    Researched_By,
    COUNT(*) as Games_Researched,
    COUNT(CASE WHEN Status = 'RELOADED' THEN 1 END) as Approved,
    COUNT(CASE WHEN Status = 'REJECTED' THEN 1 END) as Rejected,
    AVG(CASE 
        WHEN Confidence_Level = 'HIGH' THEN 3
        WHEN Confidence_Level = 'MEDIUM' THEN 2
        ELSE 1
    END) as Avg_Confidence
FROM HS_Scores_Ambiguous_Review
WHERE Researched_By IS NOT NULL
GROUP BY Researched_By
ORDER BY Games_Researched DESC;
```

---

## 🎓 Example Workflow

Here's a complete example of processing ambiguous games from start to finish:

```sql
-- 1. Initialize (first time only)
EXEC sp_Initialize_Ambiguous_Patterns;

-- 2. Identify ambiguous games from 2024 season
EXEC sp_Identify_Ambiguous_Games @Season = 2024;

-- 3. Check what was found
EXEC sp_Report_Ambiguous_Games @Status = 'PENDING';

-- 4. Research (use Python script or manual investigation)
-- python research_ambiguous_games.py

-- 5. Submit research findings
EXEC sp_Update_Ambiguous_Research
    @Review_ID = 1,
    @Proposed_Team_Name = 'Buffalo Kensington (NY)',
    @Research_Notes = 'Cross-referenced with Buffalo News archives. Kensington was the opponent based on schedule and location match.',
    @Confidence_Level = 'HIGH',
    @Researched_By = 'David McKnight';

-- 6. Review and approve
EXEC sp_Approve_And_Reload_Ambiguous_Games
    @Review_ID_List = '1,2,3',
    @MinConfidenceLevel = 'HIGH',
    @Approved_By = 'David McKnight';

-- 7. Verify the correction
SELECT 
    s.Date,
    s.Home,
    s.Visitor,
    s.Home_Score,
    s.Visitor_Score
FROM HS_Scores s
WHERE ID IN (
    SELECT Original_Game_ID 
    FROM HS_Scores_Ambiguous_Review 
    WHERE Review_ID IN (1,2,3)
);
```

---

This workflow provides a complete system for managing ambiguous opponent names while maintaining full audit trails and quality control.
