SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID FROM dbo.HS_Scores WHERE Source LIKE '%indchd%' ORDER BY Season, [Date];
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, KeptID FROM dbo.HS_Scores_Duplicate_Archive WHERE Source LIKE '%indchd%' ORDER BY Season;
