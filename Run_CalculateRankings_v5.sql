USE [hs_football_database]
GO

SET NOCOUNT ON;

-- =============================================
-- Execution Script for CalculateRankings_v5
-- Updated 2026-09-19: switched from the Jan-2026 test config (season 2023,
-- MaxLoops=50) to production defaults for the live 2026 season.
--
-- IMPORTANT: @Week must be the ACTUAL current week of the season, and it
-- changes every week during the season (e.g. 37 this week, 38 next week,
-- etc.) -- update it before each run. It is NOT a fixed "include everything"
-- sentinel. Use 52 only once the season (including all playoffs) is
-- genuinely complete -- that's what makes Rankings_Combined's
-- MAX(Week)-per-season logic (Fix_RankingsCombined_DynamicWeek.sql) resolve
-- correctly. Running an old/wrong week here after a more current week is
-- already stored will leave stale rows behind -- clean up HS_Rankings for
-- that Season/Week before re-running if that happens
-- (DELETE FROM HS_Rankings WHERE Season = ... AND Week = ...).
--
-- Keeping @DebugMode = 1 so the sample-check/duplicate-detection output is
-- visible; drop it to 0 once you've confirmed a clean run.
-- =============================================

DECLARE @LeagueType     VARCHAR(50) = '1';  -- HS
DECLARE @BeginSeason    INT = 2026;
DECLARE @EndSeason      INT = 2026;
DECLARE @Week           INT = 37;           -- <-- UPDATE THIS EVERY WEEK
DECLARE @MaxLoops       INT = 2048;         -- production value, not the 50-loop test cap
DECLARE @LogFrequency   INT = 100;
DECLARE @DebugMode      BIT = 1;            -- keep validation prints on until confirmed stable

PRINT 'Executing CalculateRankings_v5...';

EXEC [dbo].[CalculateRankings_v5]
    @LeagueType     = @LeagueType,
    @BeginSeason    = @BeginSeason,
    @EndSeason      = @EndSeason,
    @Week           = @Week,
    @MaxLoops       = @MaxLoops,
    @LogFrequency   = @LogFrequency,
    @DebugMode      = @DebugMode;

PRINT 'Execution Complete.';
GO

-- After this completes, run UpdateCombinedRating for the SAME @Week value
-- used above:
--   EXEC UpdateCombinedRating @Season = 2026, @Week = 37;
