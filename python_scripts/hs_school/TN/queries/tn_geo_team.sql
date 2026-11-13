-- games of a team with the opponent's coordinates
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, Src = LEFT(s.Source, 60),
       Opp = CASE WHEN s.Home = 'Knoxville Halls (TN)' THEN s.Visitor ELSE s.Home END, t.Latitude, t.Longitude
FROM dbo.HS_Scores s
LEFT JOIN dbo.HS_Team_Names t ON t.Team_Name = CASE WHEN s.Home = 'Knoxville Halls (TN)' THEN s.Visitor ELSE s.Home END
WHERE s.Home = 'Knoxville Halls (TN)' OR s.Visitor = 'Knoxville Halls (TN)';
SELECT s.ID, s.Season, Opp = CASE WHEN s.Home = 'Halls (TN)' THEN s.Visitor ELSE s.Home END, t.Longitude, Src = LEFT(s.Source,40)
FROM dbo.HS_Scores s LEFT JOIN dbo.HS_Team_Names t ON t.Team_Name = CASE WHEN s.Home = 'Halls (TN)' THEN s.Visitor ELSE s.Home END
WHERE s.Home = 'Halls (TN)' OR s.Visitor = 'Halls (TN)';
