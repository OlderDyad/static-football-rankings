-- Fix_GetLatestSeasonTeams_CombinedRating_MinGames.sql
-- 2026-09-25. Two changes to dbo.GetLatestSeasonTeams (the source for the
-- current-season page, via generate_latest_season.py):
--
-- 1. Combined score now comes from the stored HS_Rankings.Combined_Rating
--    (populated by UpdateCombinedRating: 0.958 x Margin + 2.791), falling
--    back to dbo.CalculateCombinedRating() if a row's stored value is NULL.
--    Previously it rebuilt the score from Avg_Adjusted_Margin_Coef /
--    Power_Ranking_Coef_Win_Loss / Power_Ranking_Coef (0.958 / 0 / 0), which
--    ranked teams in the same order but left out the 2.791 intercept, so this
--    page showed Combined values 2.79 lower than the rest of the site.
--
-- 2. Minimum games: 3 until mid-October, 5 after (and for any completed
--    season, where the latest week is 52). Keyed off the week being
--    displayed: weeks before 42 (~Oct 11-17) use 3. Games are now counted
--    only through that week, so a team's eligibility matches the ratings
--    shown rather than whenever the page happens to be generated.
--    @MinGames (optional, new) overrides the rule; existing callers that
--    pass only @PageNumber/@PageSize/@SearchTerm are unaffected.
--
-- Unchanged: season/week selection (latest season, highest stored week),
-- Margin/Win_Loss/Offense/Defense column mapping, Frosh/Freshman filters,
-- team-page link fields, pagination.

USE [hs_football_database]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

ALTER PROCEDURE [dbo].[GetLatestSeasonTeams]
    @PageNumber INT = 1,
    @PageSize INT = 100,
    @SearchTerm NVARCHAR(100) = NULL,
    @MinGames INT = NULL          -- NULL = 3 before week 42, 5 from week 42 on
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @LatestSeason INT, @LatestWeek INT, @CurrentYear INT;

    SET @CurrentYear = YEAR(GETDATE());

    -- Latest season and week for current year or most recent past year
    SELECT TOP 1
        @LatestSeason = Season,
        @LatestWeek = Week
    FROM HS_Rankings
    WHERE Season <= @CurrentYear
    ORDER BY Season DESC, Week DESC;

    IF @MinGames IS NULL
        SET @MinGames = CASE WHEN @LatestWeek < 42 THEN 3 ELSE 5 END;

    DECLARE @Offset INT = (@PageNumber - 1) * @PageSize;

    -- Games played through the displayed week (home and away)
    WITH AllGames AS (
        SELECT Home AS Team, Season
        FROM HS_Scores
        WHERE Season = @LatestSeason AND DATEPART(WEEK, Date) <= @LatestWeek
        UNION ALL
        SELECT Visitor AS Team, Season
        FROM HS_Scores
        WHERE Season = @LatestSeason AND DATEPART(WEEK, Date) <= @LatestWeek
    ),
    GameStats AS (
        SELECT Team, Season, COUNT(*) AS GamesPlayed
        FROM AllGames
        GROUP BY Team, Season
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY C.CombinedVal DESC) AS Rank,
        R.Home AS Team,
        R.Season,
        CAST(C.CombinedVal AS DECIMAL(18, 3)) AS Combined,

        -- Margin and Win_Loss mapping (matches CalculateRankings_v4_Optimized output)
        CAST(R.Avg_Of_Avg_Of_Home_Modified_Score AS DECIMAL(18, 3)) AS Margin,
        CAST(R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS DECIMAL(18, 3)) AS Win_Loss,

        CAST(R.Offense AS DECIMAL(18, 3)) AS Offense,
        CAST(R.Defense AS DECIMAL(18, 3)) AS Defense,

        G.GamesPlayed AS Games_Played,
        CASE
            WHEN RIGHT(R.Home, 6) = '(Ont)' THEN 'Ontario'
            ELSE RIGHT(R.Home, 4)
        END AS State,

        -- Team page link fields
        tn.ID AS TeamId,
        CASE
            WHEN tn.Team_Page_URL IS NOT NULL THEN 1
            ELSE ISNULL(tn.Has_Team_Page, 0)
        END AS HasTeamPage,
        tn.Team_Page_URL AS TeamPageUrl

    FROM HS_Rankings R
    CROSS APPLY (
        SELECT ISNULL(R.Combined_Rating,
                      dbo.CalculateCombinedRating(
                          R.Avg_Of_Avg_Of_Home_Modified_Score,
                          R.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                          R.Avg_Of_Avg_Of_Home_Modified_Log_Score)) AS CombinedVal
    ) C
    INNER JOIN GameStats G ON R.Home = G.Team AND R.Season = G.Season
    LEFT JOIN HS_Team_Names tn ON R.Home = tn.Team_Name
    WHERE R.Season = @LatestSeason
        AND R.Week = @LatestWeek
        AND (@SearchTerm IS NULL OR R.Home LIKE '%' + @SearchTerm + '%')
        AND G.GamesPlayed >= @MinGames
        AND R.Home NOT LIKE '%Frosh%'
        AND R.Home NOT LIKE '%frosh%'
        AND R.Home NOT LIKE '%Freshman%'
    ORDER BY Rank
    OFFSET @Offset ROWS
    FETCH NEXT @PageSize ROWS ONLY;
END
GO
