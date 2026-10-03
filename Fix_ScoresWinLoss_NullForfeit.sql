-- Fix_ScoresWinLoss_NullForfeit.sql
-- 2026-09-19: dbo.ScoresWinLoss's WHERE clause used `s.Forfeit <> 1`, which
-- in SQL Server excludes any row where Forfeit IS NULL (NULL never
-- satisfies a comparison -- it's neither "= 1" nor "<> 1", it's unknown).
-- All 6433 HS_Scores rows for season 2026 have Forfeit = NULL (confirmed
-- via `SELECT Forfeit, COUNT(*) FROM HS_Scores WHERE Season=2026 GROUP BY
-- Forfeit`), so this line silently zeroed out the ENTIRE 2026 season every
-- time ScoresWinLoss ran -- which is why CalculateRankings_v5_Fixed logged
-- "Loaded 0 game records" for @Season=2026, @Week=37 despite HS_Scores
-- having all the games. This is almost certainly why 2026 rankings have
-- never worked for any @Week value, going back to v4_Optimized too.
--
-- 2026-09-20 REVISION: an initial fix simply treated NULL the same as 0
-- (include it unconditionally). That's wrong on its own: David's forfeit
-- convention (pre-2025, explicitly applied by the old Excel scraper/MaxPreps
-- ID'ing) is that any 1-0, 0-1, 2-0, or 0-2 final score for a season after
-- 1949 IS a forfeit and must be excluded from ratings. Starting with the
-- 2025 season, MaxPreps changed its page format (as it does most seasons)
-- and the current scraper was never re-tuned to auto-detect forfeits, so
-- essentially the entire 2025 (82,627/82,932) and 2026 (6,433/6,433) seasons
-- sit at Forfeit = NULL -- meaning "never evaluated", not "confirmed not a
-- forfeit". David's explicit design (2026-09-20): leave every already-marked
-- Forfeit value (0 or 1, any era) untouched; for the NULL/ambiguous case,
-- compute the decision from the actual score instead of guessing either
-- direction:
--   Forfeit = 0            -> always included, no matter the score
--   Forfeit = 1             -> always excluded (implicit: falls through)
--   Forfeit IS NULL         -> included UNLESS Season > 1949 AND the score
--                              is 1-0, 0-1, 2-0, or 0-2, in which case
--                              excluded (same rule the old scraper/MaxPreps
--                              applied explicitly for pre-2025 data).
-- This self-scopes correctly across every season without hardcoding a year
-- range -- seasons 2020-2024 have almost no NULL rows left to affect, and
-- 2025/2026 get the real fix.
--
-- Scripted from the live database via SSMS Object Explorer 2026-09-19
-- ("Script Stored Procedure as -> CREATE To"); not previously present in
-- either source folder.

USE [hs_football_database]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER PROCEDURE [dbo].[ScoresWinLoss]
    @Season INT,
    @Week INT,
    @LeagueType INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ScoresTable VARCHAR(50);
    DECLARE @SQL NVARCHAR(MAX);
    DECLARE @HFA_Margin FLOAT;
    DECLARE @HFA_WinLoss FLOAT;

    -- Get the ScoresTable from LeagueConfig based on LeagueType
    SELECT @ScoresTable = ScoresTable
    FROM dbo.LeagueConfig  -- Correct schema reference
    WHERE LeagueType = @LeagueType;

    -- Fetch the HFA values from the Coefficients table
    SELECT @HFA_Margin = Home_Field_Adv_Margin,
           @HFA_WinLoss = Home_Field_Adv_Win_Loss
    FROM dbo.Coefficients;

    -- Insert the results into the ScoresWinLossResults table
    SET @SQL = N'
    INSERT INTO dbo.ScoresWinLossResults (
        ID, Date, Season, Season_1, Visitor, Visitor_Score,
        Home, Home_Score, Margin, Neutral, Location, Location2,
        Line, Win_Loss, Percent_Margin, Adj_Log_Margin,
        Adjusted_Margin, Adjusted_Margin_Win_Loss, Game,
        Week_1, Week, SeasonHome, SeasonVisitor, Forfeit
    )
    SELECT
        CAST(s.ID AS VARCHAR(36)) AS ID,  -- Convert uniqueidentifier to varchar
        s.Date,
        s.Season,
        s.Season + 1 AS [Season-1],
        s.Visitor,
        s.Visitor_Score,
        s.Home,
        s.Home_Score,
        s.Margin,
        s.Neutral,
        s.Location,
        s.Location2,
        s.Line,
        CASE WHEN s.Margin = 0 THEN 0 ELSE s.Margin / ABS(s.Margin) END AS [Win_Loss],
        1 + ((s.Home_Score + 10) / (s.Home_Score + s.Visitor_Score + 20)) AS [Percent_Margin],
        CASE WHEN ABS(s.Margin) = 0 THEN 0 ELSE LOG(ABS(s.Margin)) * (s.Margin / ABS(s.Margin)) END AS [Adj_Log_Margin],
        CASE WHEN s.Neutral = 0 THEN s.Margin - ' + CAST(@HFA_Margin AS NVARCHAR(10)) + ' ELSE s.Margin END AS [Adjusted_Margin],
        CASE WHEN s.Neutral = 0 THEN
            CASE WHEN s.Margin = 0 THEN 0 ELSE s.Margin / ABS(s.Margin) END - ' + CAST(@HFA_WinLoss AS NVARCHAR(10)) + '
            ELSE CASE WHEN s.Margin = 0 THEN 0 ELSE s.Margin / ABS(s.Margin) END
        END AS [Adjusted_Margin_Win_Loss],
        CONCAT(s.Date, CASE WHEN RTRIM(s.Home) < RTRIM(s.Visitor) THEN RTRIM(s.Home) + RTRIM(s.Visitor) ELSE RTRIM(s.Visitor) + RTRIM(s.Home) END) AS Game,
        CASE WHEN ' + CAST(@Week AS NVARCHAR(10)) + ' >= 50 THEN 49 WHEN ' + CAST(@Week AS NVARCHAR(10)) + ' <= 10 THEN 49 ELSE ' + CAST(@Week AS NVARCHAR(10)) + ' - 1 END AS [Week_1],
        DATEPART(WEEK, s.Date) AS Week,
        CONCAT(s.Season, s.Home) AS SeasonHome,
        CONCAT(s.Season, s.Visitor) AS SeasonVisitor,
        s.Forfeit
    FROM ' + @ScoresTable + ' s
    WHERE s.Season = ' + CAST(@Season AS NVARCHAR(10)) + '
    AND DATEPART(WEEK, s.Date) <= ' + CAST(@Week AS NVARCHAR(10)) + '
    AND (
        s.Forfeit = 0
        OR (
            s.Forfeit IS NULL
            AND NOT (
                s.Season > 1949
                AND (
                    (s.Home_Score = 1 AND s.Visitor_Score = 0) OR
                    (s.Home_Score = 0 AND s.Visitor_Score = 1) OR
                    (s.Home_Score = 2 AND s.Visitor_Score = 0) OR
                    (s.Home_Score = 0 AND s.Visitor_Score = 2)
                )
            )
        )
    );';  -- FIXED 2026-09-20 (revised from the 2026-09-19 fix): was
          -- `AND s.Forfeit <> 1`, then briefly `AND (s.Forfeit <> 1 OR
          -- s.Forfeit IS NULL)`. Now: explicit 0/1 marks are respected as-is,
          -- and NULL (ambiguous/never-evaluated) is resolved by checking the
          -- actual score against the historical 1-0/0-1/2-0/0-2 forfeit
          -- pattern for seasons after 1949 -- see header comment.

    EXEC sp_executesql @SQL;
END;
GO
