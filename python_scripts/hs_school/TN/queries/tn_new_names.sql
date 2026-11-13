-- opponents of 2023+ TN names that need identification, and of possible old names
SELECT n.Name, s.Season, Opp = CASE WHEN s.Home = n.Name THEN s.Visitor ELSE s.Home END, s.Source
FROM (VALUES ('Nashville Tennessee (TN)'),('Nashville Tn Tigers (TN)'),('Knoxville Tennessee School (TN)'),('Chattanooga Csthea (TN)'),
 ('Knoxville Christian Academy (TN)'),('Christian Academy of Knoxville (TN)'),('Hopkinsville Christian County (TN)'),('Knoxville Fulton County (TN)'),
 ('Johnson City Providence (TN)'),('Springfield Innovation Academy (TN)'),('Memphis University (TN)'),('Morristown Hamblen West (TN)'),
 ('Tennessee School for the Deaf (TN)'),('Nashville Tennessee School for the Blind (TN)')) n(Name)
JOIN dbo.HS_Scores s ON (s.Home = n.Name OR s.Visitor = n.Name) AND s.Season >= 2022
ORDER BY n.Name, s.Season, s.[Date];
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name LIKE '%(TN)' AND (Team_Name LIKE '%Blind%' OR Team_Name LIKE '%Deaf%' OR Team_Name LIKE '%Providence%' OR Team_Name LIKE '%Tennessee State%' OR Team_Name LIKE 'Chattanooga C%' OR Team_Name LIKE '%Innovation%' OR Team_Name LIKE '%Christian Academy%Knox%' OR Team_Name LIKE 'Knoxville Christian%');
SELECT u.URL, u.ProperName FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName IN ('Nashville Tennessee (TN)','Nashville Tn Tigers (TN)','Knoxville Tennessee School (TN)','Chattanooga Csthea (TN)','Knoxville Christian Academy (TN)','Johnson City Providence (TN)','Christian Academy of Knoxville (TN)');
