SET NOCOUNT ON;
SELECT Team = CASE WHEN s.Home IN ('Kansas City Washington (KS)','Washington (KS)','Washington County (KS)') THEN s.Home ELSE s.Visitor END,
       s.Season, s.[Date],
       Opp = CASE WHEN s.Home IN ('Kansas City Washington (KS)','Washington (KS)','Washington County (KS)') THEN s.Visitor ELSE s.Home END,
       TS = CASE WHEN s.Home IN ('Kansas City Washington (KS)','Washington (KS)','Washington County (KS)') THEN s.Home_Score ELSE s.Visitor_Score END,
       OS = CASE WHEN s.Home IN ('Kansas City Washington (KS)','Washington (KS)','Washington County (KS)') THEN s.Visitor_Score ELSE s.Home_Score END,
       s.Source, s.ID
FROM dbo.HS_Scores s
WHERE s.Home IN ('Kansas City Washington (KS)','Washington (KS)','Washington County (KS)') OR s.Visitor IN ('Kansas City Washington (KS)','Washington (KS)','Washington County (KS)')
ORDER BY 1, 2, 3;
