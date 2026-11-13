SELECT n.Nm, InNames = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names t WHERE t.Team_Name = n.Nm) THEN 1 ELSE 0 END,
 Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = n.Nm OR s.Visitor = n.Nm)
FROM (VALUES ('Winston-Salem Mount Tabor (NC)'),('Gastonia Mount Zion (NC)'),('Wadesboro Bowman (NC)'),('Kinston Grainger (NC)'),('Marshall (NC)'),('Ahoskie (NC)'),('Sylva-Webster (NC)'),('Sylva Sylva-Webster (NC)'),
 ('Candler (NC)'),('Wilson Fike (NC)'),('Wilson Coon (NC)'),('Greenville J.H. Rose (NC)'),('Greenville Rose (NC)'),('Greenville (SC)'),('Nashville (NC)'),('Warrenton (NC)'),('Warrenton John Graham (NC)')) n(Nm);
