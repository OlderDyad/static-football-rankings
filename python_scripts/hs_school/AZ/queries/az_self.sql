SELECT ID, Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source FROM dbo.HS_Scores WHERE Home = Visitor AND RIGHT(RTRIM(Home), 4) = '(AZ)';
