SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#n') IS NOT NULL DROP TABLE #n;
CREATE TABLE #n (Name varchar(150));
INSERT INTO #n VALUES ('Suffield (CT)'),('Suffield Academy (CT)'),('West Hartford (CT)'),('West Hartford Hall (CT)'),('Providence Wheeler (RI)'),
('Woonsocket Mount Saint Charles Academy (RI)'),('North Smithfield-Mount St. Charles Academy (RI)'),('Windsor Locks-Suffield (CT)'),('Windsor Locks-Suffield-East Granby (CT)'),
('Ellington-Somers (CT)'),('Ellington-Somers-East Windsor (CT)'),('Stafford Springs Stafford (CT)'),('Stafford Springs Stafford-Somers-East Windsor (CT)'),
('Griswold-Wheeler (CT)'),('Griswold (CT)'),('Winsted Gilbert-Northwestern-Housatonic (CT)'),('Hillsboro-Deering (NH)'),('Hillsboro-Deering-Hopkinton (NH)'),
('Central Falls-Blackstone Valley Prep (RI)'),('Central Falls-Blackstone Valley Prep-Achievement First (RI)'),('East Providence Providence Country (RI)'),
('Providence Country Day-Highlander Charter-Sanchez Complex (RI)'),('East Providence Providence Country Day (RI)'),('Hartford Bulkeley-Weaver (CT)'),
('Durham Coginchaug Regional-Hale Ray (CT)'),('Durham Coginchaug Regional-East Hampton-Hale Ray (CT)'),('Hartford Capital Prep-Achievement First (CT)'),('Hartford (CT)');
SELECT n.Name, Games = COUNT(s.ID), MinS = MIN(s.Season), MaxS = MAX(s.Season)
FROM #n n LEFT JOIN dbo.HS_Scores s ON s.Home = n.Name OR s.Visitor = n.Name GROUP BY n.Name ORDER BY n.Name;
SELECT n.Name, Opp = CASE WHEN s.Home = n.Name THEN s.Visitor ELSE s.Home END, Games = COUNT(*), MinS = MIN(s.Season), MaxS = MAX(s.Season)
FROM #n n JOIN dbo.HS_Scores s ON s.Home = n.Name OR s.Visitor = n.Name
WHERE n.Name IN ('Suffield (CT)','West Hartford (CT)','Providence Wheeler (RI)','Woonsocket Mount Saint Charles Academy (RI)')
GROUP BY n.Name, CASE WHEN s.Home = n.Name THEN s.Visitor ELSE s.Home END ORDER BY n.Name, Games DESC;
