SELECT s.Season, Src = LEFT(s.Source,30), Games = COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = 'Memphis Academy of Health Sciences (TN)' OR s.Visitor = 'Memphis Academy of Health Sciences (TN)' GROUP BY s.Season, LEFT(s.Source,30) ORDER BY 1;
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name LIKE 'Memphis%Science%(TN)' OR Team_Name LIKE 'Memphis%MASE%' OR Team_Name LIKE 'Memphis%Health%';
SELECT URL, ProperName FROM dbo.URL_ProperName_Mapping WHERE URL LIKE '%maxpreps.com/tn/memphis/%academy%';
