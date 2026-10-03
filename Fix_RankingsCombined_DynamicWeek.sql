-- Fix_RankingsCombined_DynamicWeek.sql
-- 2026-09-19: Rankings_Combined previously hardcoded `WHERE r.Week = 52`,
-- meaning any rankings calculated under a different @Week value (e.g. an
-- in-progress-season checkpoint like Week=37) were computed and stored in
-- HS_Rankings but never surfaced anywhere downstream, since every JSON/HTML
-- generation step reads from this view. This confirmed the user's
-- suspicion that non-52 weeks "never worked" -- they were invisible, not
-- broken.
--
-- Fix: pick the LATEST week actually stored for each season, instead of a
-- hardcoded 52. A fully-completed historical season that only ever had a
-- Week=52 run behaves identically to before (MAX(Week) = 52). A season
-- with fresher in-progress data under a different (real, current) week now
-- surfaces it.
--
-- CORRECTION 2026-09-19: Week is NOT a generic "include everything"
-- sentinel that 52 always safely stands in for -- it tracks the actual
-- current week of the season, and 52 is only correct once the season
-- (including playoffs) is genuinely over. Running CalculateRankings_v5
-- with Week=52 mid-season (as happened once here before this was caught)
-- creates a stale row that MAX(Week) will wrongly prefer over the real,
-- lower, current-week number -- clean up any such mistaken run
-- (DELETE FROM HS_Rankings WHERE Season = ... AND Week = 52) before
-- trusting this view for that season.
--
-- CAUTION before running this against a live season: if HS_Rankings has
-- BOTH an old Week=52 run AND a newer partial-week run for the SAME
-- season (e.g. from earlier testing), MAX(Week) will pick 52 -- the
-- OLDER one -- not the most recent. Check for this first:
--
--   SELECT Season, Week, COUNT(*) AS Teams, MAX(Date_Added) AS LastRun
--   FROM HS_Rankings
--   WHERE Season = 2026
--   GROUP BY Season, Week
--   ORDER BY Week;
--
-- If more than one Week value shows up for a season you care about,
-- decide (and clean up) before relying on this view for that season.
--
-- ALSO WORTH CHECKING FIRST: this view's fix assumes CalculateRankings_v4_
-- Optimized's in-progress-week filtering (Loop_Query_Step_6v2's
-- `swd.Week <= @Week` against dbo.ScoresWinLossResults) actually produces
-- correct partial-season data. That view/table's own definition isn't in
-- this repo, so it hasn't been verified here -- run this first to sanity
-- check what "Week" means for this season's games before trusting a
-- Week=37-style run's output:
--
--   SELECT Week, COUNT(*) AS Games, MIN([Date]) AS Earliest, MAX([Date]) AS Latest
--   FROM dbo.ScoresWinLossResults
--   WHERE Season = 2026
--   GROUP BY Week
--   ORDER BY Week;
--
-- If that shows real, small, date-correlated week numbers (1, 2, 3...),
-- the fix below is solid. If Week is NULL/constant/nonsensical there,
-- the partial-week filter needs its own fix before this view change
-- will show anything useful for an in-progress week.

ALTER VIEW Rankings_Combined AS
SELECT
    r.Season,
    r.Home AS Team,
    -- CORRECTED: These were swapped
    r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS Margin,        -- This is Margin (100+)
    r.Avg_Of_Avg_Of_Home_Modified_Score AS Win_Loss,               -- This is Win/Loss (single digits)
    r.Avg_Of_Avg_Of_Home_Modified_Log_Score AS Log_Score,
    r.Max_Min_Margin,
    r.Max_Performance,
    r.Min_Performance,
    r.Offense,
    r.Defense,
    r.Best_Worst_Win_Loss,
    -- Combined Rating calculation (using correct coefficient column names)
    (r.Avg_Of_Avg_Of_Home_Modified_Score * c.Win_Loss_Coef +           -- Win/Loss
     r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * c.Margin_Coef +   -- Margin
     r.Avg_Of_Avg_Of_Home_Modified_Log_Score * c.Log_Score_Coef) AS Combined_Rating,
    -- Game count for filtering
    CASE
        WHEN r.Season < 1950 THEN
            (SELECT COUNT(*) FROM HS_Scores s
             WHERE (s.Home = r.Home OR s.Visitor = r.Home)
             AND s.Season = r.Season)
        ELSE
            (SELECT COUNT(*) FROM HS_Scores s
             WHERE (s.Home = r.Home OR s.Visitor = r.Home)
             AND s.Season = r.Season)
    END AS Games_Played
FROM HS_Rankings r
CROSS JOIN (
    SELECT TOP 1
        Win_Loss_Coef,
        Margin_Coef,
        Log_Score_Coef
    FROM Coefficients
    ORDER BY ID DESC
) c
WHERE r.Week = (
    -- Was: r.Week = 52  -- End of season
    -- Now: the latest week actually calculated for this season, so an
    -- in-progress-season run surfaces instead of only ever Week=52.
    SELECT MAX(r2.Week) FROM HS_Rankings r2 WHERE r2.Season = r.Season
)
  AND r.Home NOT LIKE '%Freshman%'
  AND r.Home NOT LIKE '%JV%'
  AND (
    (r.Season < 1950 AND
     (SELECT COUNT(*) FROM HS_Scores s
      WHERE (s.Home = r.Home OR s.Visitor = r.Home)
      AND s.Season = r.Season) >= 5)
    OR
    (r.Season >= 1950 AND
     (SELECT COUNT(*) FROM HS_Scores s
      WHERE (s.Home = r.Home OR s.Visitor = r.Home)
      AND s.Season = r.Season) >= 8)
  );
GO
