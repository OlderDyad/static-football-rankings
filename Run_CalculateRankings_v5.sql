USE [hs_football_database]
GO

SET NOCOUNT ON;

-- =============================================
-- Execution Script for CalculateRankings_v5
-- =============================================

DECLARE @LeagueType     VARCHAR(50) = '1';  -- Default HS
DECLARE @BeginSeason    INT = 2023;         -- Test Season
DECLARE @EndSeason      INT = 2023;         -- Test Season
DECLARE @Week           INT = 52;           -- Final Week
DECLARE @MaxLoops       INT = 50;           -- Limit loops for testing (Convergence usually takes <100)
DECLARE @LogFrequency   INT = 1;            -- Log every loop to track progress
DECLARE @DebugMode      BIT = 1;            -- Enable debug prints

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
