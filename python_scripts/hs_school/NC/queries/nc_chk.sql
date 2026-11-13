SELECT n.Nm, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = n.Nm OR s.Visitor = n.Nm)
FROM (VALUES ('Gastonia Mt. Zion (NC)'),('Gastonia Mount Zion (NC)'),('Kinston Grainger (NC)'),('Kinston Jesse W. Grainger (NC)'),('Marshall (NC)'),('Ahoskie (NC)'),('Sylva-Webster (NC)'),('Candler (NC)'),('Winston-Salem Mount Tabor (NC)'),('Winston-Salem Mt. Tabor (NC)')) n(Nm);
