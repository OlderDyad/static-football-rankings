-- ============================================================================
-- Fix_CO_Aliases_LaPorte_Sheridan.sql  (2026-10-12)
-- Run BEFORE the Colorado dedup, so the duplicates line up under the right names.
-- Section 1 is read-only. Run Section 2 only after checking Section 1.
-- ============================================================================

-- ---------------- SECTION 1: preview ----------------
-- games already imported under the wrong team
SELECT 'La Porte (IN) in a western game' AS Issue, Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home = 'La Porte (IN)' AND RIGHT(RTRIM(Visitor), 4) IN ('(CO)','(WY)','(NE)','(NM)'))
   OR (Visitor = 'La Porte (IN)' AND RIGHT(RTRIM(Home), 4) IN ('(CO)','(WY)','(NE)','(NM)'))
UNION ALL
SELECT 'Denver Sheridan (CO) vs Wyoming team', Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home = 'Denver Sheridan (CO)' AND RTRIM(Visitor) LIKE '%(WY)')
   OR (Visitor = 'Denver Sheridan (CO)' AND RTRIM(Home) LIKE '%(WY)')
ORDER BY Issue, Season, [Date];
-- (a real Indiana La Porte game would not have a CO/WY/NE/NM opponent; check the list anyway)

-- ---------------- SECTION 2: fix ----------------
/*
BEGIN TRAN;

IF NOT EXISTS (SELECT 1 FROM dbo.HS_Team_Names WHERE Team_Name = 'Laporte (CO)')
    INSERT INTO dbo.HS_Team_Names (Team_Name, State, City) VALUES ('Laporte (CO)', 'CO', 'Laporte');

UPDATE dbo.HS_Team_Name_Alias SET Standardized_Name = 'Laporte (CO)'
WHERE Standardized_Name = 'La Porte (IN)'
  AND Newspaper_Region IN ('Fort Collins Coloradoan', 'Pueblo Chieftain', 'The Daily Sentinel');

UPDATE dbo.HS_Team_Name_Alias SET Standardized_Name = 'Sheridan (WY)'
WHERE Alias_Name = 'Sheridan' AND Newspaper_Region = 'Fort Collins Coloradoan'
  AND Standardized_Name = 'Denver Sheridan (CO)';

UPDATE dbo.HS_Scores SET Home = 'Laporte (CO)'
WHERE Home = 'La Porte (IN)' AND RIGHT(RTRIM(Visitor), 4) IN ('(CO)','(WY)','(NE)','(NM)');
UPDATE dbo.HS_Scores SET Visitor = 'Laporte (CO)'
WHERE Visitor = 'La Porte (IN)' AND RIGHT(RTRIM(Home), 4) IN ('(CO)','(WY)','(NE)','(NM)');

UPDATE dbo.HS_Scores SET Home = 'Sheridan (WY)'
WHERE Home = 'Denver Sheridan (CO)' AND RTRIM(Visitor) LIKE '%(WY)';
UPDATE dbo.HS_Scores SET Visitor = 'Sheridan (WY)'
WHERE Visitor = 'Denver Sheridan (CO)' AND RTRIM(Home) LIKE '%(WY)';

-- check, then COMMIT; (or ROLLBACK;)
*/
