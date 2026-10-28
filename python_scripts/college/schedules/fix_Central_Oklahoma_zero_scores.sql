-- Central Oklahoma conflicts where our row lost a team's points (0, or 0-0): take the site's score
-- run AFTER import_schedule_csv.py --commit --flag-conflicts
BEGIN TRAN;
UPDATE dbo.College_Scores SET Home_Score = CASE WHEN Home='Central Oklahoma' THEN 27 ELSE 7 END, Visitor_Score = CASE WHEN Home='Central Oklahoma' THEN 7 ELSE 27 END, Score_Disputed = 0 WHERE Access_ID = 302312;  -- 1953 vs Central Arkansas: ours 0-7, site 27-7
UPDATE dbo.College_Scores SET Home_Score = CASE WHEN Home='Central Oklahoma' THEN 21 ELSE 20 END, Visitor_Score = CASE WHEN Home='Central Oklahoma' THEN 20 ELSE 21 END, Score_Disputed = 0 WHERE Access_ID = 302322;  -- 1954 vs Central Arkansas: ours 0-0, site 21-20
UPDATE dbo.College_Scores SET Home_Score = CASE WHEN Home='Central Oklahoma' THEN 66 ELSE 12 END, Visitor_Score = CASE WHEN Home='Central Oklahoma' THEN 12 ELSE 66 END, Score_Disputed = 0 WHERE Access_ID = 302331;  -- 1955 vs Central Arkansas: ours 0-12, site 66-12
UPDATE dbo.College_Scores SET Home_Score = CASE WHEN Home='Central Oklahoma' THEN 7 ELSE 21 END, Visitor_Score = CASE WHEN Home='Central Oklahoma' THEN 21 ELSE 7 END, Score_Disputed = 0 WHERE Access_ID = 265274;  -- 1977 vs Northern Colorado: ours 0-21, site 7-21
UPDATE dbo.College_Scores SET Home_Score = CASE WHEN Home='Central Oklahoma' THEN 20 ELSE 48 END, Visitor_Score = CASE WHEN Home='Central Oklahoma' THEN 48 ELSE 20 END, Score_Disputed = 0 WHERE Access_ID = 265293;  -- 1978 vs Northern Colorado: ours 0-48, site 20-48
UPDATE dbo.College_Scores SET Margin = Home_Score - Visitor_Score WHERE Access_ID IN (302312,302322,302331,265274,265293);
-- expect 1 row each, 5 on the Margin update
COMMIT;
SELECT @@TRANCOUNT;
