SELECT n.Nm, InNames = CASE WHEN t.ID IS NULL THEN 0 ELSE 1 END, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = n.Nm OR s.Visitor = n.Nm)
FROM (VALUES ('Nashville Peabody (TN)'),('Trezevant (TN)'),('Nashville Tennessee Youth Center (TN)'),('Tennessee Youth Center (TN)'),('Memphis Academy of Science and Engineering (TN)'),('Nashville Peabody Demonstration (TN)')) n(Nm)
LEFT JOIN dbo.HS_Team_Names t ON t.Team_Name = n.Nm;
