-- 1. All URL mappings for CT, NH, RI
SELECT URL, ProperName, Team_ID
FROM dbo.URL_ProperName_Mapping
WHERE ProperName LIKE '%(CT)'
   OR ProperName LIKE '%(NH)'
   OR ProperName LIKE '%(RI)'
   OR URL LIKE '%/ct/%'
   OR URL LIKE '%/nh/%'
   OR URL LIKE '%/ri/%'
ORDER BY ProperName;

-- 2. HS_Team_Names check for key CT, NH, RI names
SELECT ID, Team_Name, City, State
FROM dbo.HS_Team_Names
WHERE State IN ('CT', 'NH', 'RI')
  AND (
    Team_Name LIKE '%O''Brien%' OR Team_Name LIKE '%Obrien%' OR
    Team_Name LIKE '%Avon%' OR
    Team_Name LIKE '%Bullard%' OR
    Team_Name LIKE '%Coventry%' OR
    Team_Name LIKE '%Killingly%' OR
    Team_Name LIKE '%Farmington%' OR
    Team_Name LIKE '%Prince%' OR
    Team_Name LIKE '%Sport%' OR
    Team_Name LIKE '%Capital Prep%' OR
    Team_Name LIKE '%Bulkeley%' OR Team_Name LIKE '%Buckeley%' OR
    Team_Name LIKE '%Hotchkiss%' OR
    Team_Name LIKE '%Wilcox%' OR
    Team_Name LIKE '%Thames River%' OR Team_Name LIKE '%Bernard%' OR
    Team_Name LIKE '%Thomas More%' OR Team_Name LIKE '%St.Thomas%' OR
    Team_Name LIKE '%Stonington%' OR
    Team_Name LIKE '%Pomfret%' OR
    Team_Name LIKE '%Quinebaug%' OR Team_Name LIKE '%Putnam%' OR
    Team_Name LIKE '%Westminster%' OR
    Team_Name LIKE '%Stafford%' OR
    Team_Name LIKE '%King%' OR
    Team_Name LIKE '%Gunn%' OR
    Team_Name LIKE '%Waterbury%' OR
    Team_Name LIKE '%West Haven%' OR
    Team_Name LIKE '%Gilbert%' OR
    Team_Name LIKE '%Housatonic%' OR
    Team_Name LIKE '%Creed%' OR Team_Name LIKE '%Hyde%' OR
    Team_Name LIKE '%Vinal%' OR Team_Name LIKE '%Coginchaug%' OR
    Team_Name LIKE '%Fall Mountain%' OR
    Team_Name LIKE '%Belmont%' OR Team_Name LIKE '%Gilford%' OR
    Team_Name LIKE '%Exeter%' OR
    Team_Name LIKE '%Hillsboro%' OR
    Team_Name LIKE '%Inter-Lakes%' OR Team_Name LIKE '%Inter Lakes%' OR
    Team_Name LIKE '%Peterborough%' OR Team_Name LIKE '%Contoocook%' OR
    Team_Name LIKE '%Spaulding%' OR
    Team_Name LIKE '%Tilton%' OR
    Team_Name LIKE '%Pinkerton%' OR
    Team_Name LIKE '%Central Falls%' OR
    Team_Name LIKE '%Country Day%' OR Team_Name LIKE '%Wheeler%' OR
    Team_Name LIKE '%Smithfield%' OR
    Team_Name LIKE '%Exeter%Greenwich%' OR
    Team_Name LIKE '%Davies%' OR
    Team_Name LIKE '%Pawtucket%' OR
    Team_Name LIKE '%Hope%' OR
    Team_Name LIKE '%Lasalle%' OR Team_Name LIKE '%La Salle%' OR
    Team_Name LIKE '%Scituate%' OR
    Team_Name LIKE '%South Kingstown%' OR
    Team_Name LIKE '%Woonsocket%' OR Team_Name LIKE '%Mount%Charles%' OR Team_Name LIKE '%Mt.%Charles%'
  )
ORDER BY State, Team_Name;

-- 3. Check Derry Pinkerton (MA) and other wrong-state names
SELECT Home AS Team, COUNT(*) AS Games, MIN(Season) AS FirstS, MAX(Season) AS LastS
FROM (
    SELECT Home, Season FROM dbo.HS_Scores WHERE Home LIKE '%Pinkerton%' OR Home LIKE '%Williston%' OR Home LIKE '%Tilton%'
    UNION ALL
    SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor LIKE '%Pinkerton%' OR Visitor LIKE '%Williston%' OR Visitor LIKE '%Tilton%'
) x
GROUP BY Home
ORDER BY Home;

-- 4. Inspect CT mystery / small / Opp names and Waterbury Career Academy pre-2013
SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (
    Home IN (
        'All-Hartfords (CT)', 'Bridgeport Sacred Heart (CT)', 'Bridgeport Samuel Johnson (CT)',
        'Bolton (CT)', 'Cheshire Roxbury (CT)', 'Collinsville Canton (CT)', 'Columbia Horace W. Porter (CT)',
        'Farmington-Ambiguous (CT)', 'Garfield (CT)', 'Greensboro (CT)', 'Handham (CT)', 'Harrison (CT)',
        'Hertford (CT)', 'Johnson Academy (CT)', 'K.L.Haywood (CT)', 'KLHT (CT)', 'Litchfield (CT)',
        'Mansfield (CT)', 'Meriden St. Joseph (CT)', 'Middletown Connecticut Juvenile Training School (CT)',
        'Mount Vernon (CT)', 'NCI (CT)', 'New Britain E. C. Goodwin Tech (CT)', 'Norwalk St. Jerome (CT)',
        'Notre Dame (CT)', 'Old Lyme (CT)', 'Poan Frosh (CT)', 'Prov. County (CT)', 'Ridgefield Prep (CT)',
        'Robinson (CT)', 'Roxbury (CT)', 'Smity (CT)', 'South Manchester (CT)', 'St. Anthony (CT)',
        'St. Paul''s School (CT)', 'Stamford Prep (CT)', 'Stamford Roosevelt (CT)', 'Stamford Roxbury School (CT)',
        'Stoningham (CT)', 'Suffield (CT)', 'Thompson (CT)', 'Thompsonville Enfield (CT)', 'Wallingford (CT)',
        'Washington Romford (CT)', 'Waterbury (CT)', 'Werde (CT)', 'Westbrook Kingsley Hall (CT)',
        'Williams (CT)', 'Woodbury (CT)', 'Wooster-Denby School (CT)', 'Hartford Watkinson (CT)',
        'Simsbury The Abbey School (CT)', 'New London Burkely (CT)'
    )
    OR Visitor IN (
        'All-Hartfords (CT)', 'Bridgeport Sacred Heart (CT)', 'Bridgeport Samuel Johnson (CT)',
        'Bolton (CT)', 'Cheshire Roxbury (CT)', 'Collinsville Canton (CT)', 'Columbia Horace W. Porter (CT)',
        'Farmington-Ambiguous (CT)', 'Garfield (CT)', 'Greensboro (CT)', 'Handham (CT)', 'Harrison (CT)',
        'Hertford (CT)', 'Johnson Academy (CT)', 'K.L.Haywood (CT)', 'KLHT (CT)', 'Litchfield (CT)',
        'Mansfield (CT)', 'Meriden St. Joseph (CT)', 'Middletown Connecticut Juvenile Training School (CT)',
        'Mount Vernon (CT)', 'NCI (CT)', 'New Britain E. C. Goodwin Tech (CT)', 'Norwalk St. Jerome (CT)',
        'Notre Dame (CT)', 'Old Lyme (CT)', 'Poan Frosh (CT)', 'Prov. County (CT)', 'Ridgefield Prep (CT)',
        'Robinson (CT)', 'Roxbury (CT)', 'Smity (CT)', 'South Manchester (CT)', 'St. Anthony (CT)',
        'St. Paul''s School (CT)', 'Stamford Prep (CT)', 'Stamford Roosevelt (CT)', 'Stamford Roxbury School (CT)',
        'Stoningham (CT)', 'Suffield (CT)', 'Thompson (CT)', 'Thompsonville Enfield (CT)', 'Wallingford (CT)',
        'Washington Romford (CT)', 'Waterbury (CT)', 'Werde (CT)', 'Westbrook Kingsley Hall (CT)',
        'Williams (CT)', 'Woodbury (CT)', 'Wooster-Denby School (CT)', 'Hartford Watkinson (CT)',
        'Simsbury The Abbey School (CT)', 'New London Burkely (CT)'
    )
    OR Home LIKE '%Opp "%(CT)' OR Visitor LIKE '%Opp "%(CT)' OR Home LIKE '%"Black Tie"%(CT)' OR Visitor LIKE '%"Black Tie"%(CT)'
    OR ((Home = 'Waterbury Career Academy (CT)' OR Visitor = 'Waterbury Career Academy (CT)') AND Season < 2013)
)
ORDER BY Season, Date;

-- 5. Inspect NH & RI mystery / small / Opp names
SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (
    Home IN (
        'Canaan (NH)', 'Colby Academy (NH)', 'Franconia Dow Academy (NH)', 'Franklin Golden Rule Farm (NH)',
        'Groveton (NH)', 'Hampton (NH)', 'Haverhill (NH)', 'Laconia St. Joseph''s (NH)', 'Manchester St. Marie (NH)',
        'Manchester West Side Catholic Regional (NH)', 'Newmarket (NH)', 'North Hampton St. Thomas More Catholic (NH)',
        'Rochester (NH)', 'Rye Beach Atlantic Air Academy (NH)', 'Strafford Austin-Cate Academy (NH)', 'Tilton Academy (NH)',
        'Barrington Vocational (RI)', 'Cranston Sockanosset School for Boys (RI)', 'East Providence Gordon (RI)',
        'East Providence Sacred Heart (RI)', 'Holt (RI)', 'HopeProvidence, RI (RI)', 'Injury Fund (RI)',
        'Johnston Prep (RI)', 'Kingston (RI)', 'Medford (RI)', 'Middletown Rivers School (RI)',
        'Newport Training School (RI)', 'Providence Our Lady of Providence Seminary (RI)',
        'Rhode Island School for the Deaf (RI)', 'Rogers (RI)', 'Seek"" (RI)', 'Smithfield American International Academy (RI)',
        'South Kingstown (RI)', 'Warwick (RI)', 'West Smithfield (RI)', 'Woonsocket Mount Saint Charles Academy (RI)'
    )
    OR Visitor IN (
        'Canaan (NH)', 'Colby Academy (NH)', 'Franconia Dow Academy (NH)', 'Franklin Golden Rule Farm (NH)',
        'Groveton (NH)', 'Hampton (NH)', 'Haverhill (NH)', 'Laconia St. Joseph''s (NH)', 'Manchester St. Marie (NH)',
        'Manchester West Side Catholic Regional (NH)', 'Newmarket (NH)', 'North Hampton St. Thomas More Catholic (NH)',
        'Rochester (NH)', 'Rye Beach Atlantic Air Academy (NH)', 'Strafford Austin-Cate Academy (NH)', 'Tilton Academy (NH)',
        'Barrington Vocational (RI)', 'Cranston Sockanosset School for Boys (RI)', 'East Providence Gordon (RI)',
        'East Providence Sacred Heart (RI)', 'Holt (RI)', 'HopeProvidence, RI (RI)', 'Injury Fund (RI)',
        'Johnston Prep (RI)', 'Kingston (RI)', 'Medford (RI)', 'Middletown Rivers School (RI)',
        'Newport Training School (RI)', 'Providence Our Lady of Providence Seminary (RI)',
        'Rhode Island School for the Deaf (RI)', 'Rogers (RI)', 'Seek"" (RI)', 'Smithfield American International Academy (RI)',
        'South Kingstown (RI)', 'Warwick (RI)', 'West Smithfield (RI)', 'Woonsocket Mount Saint Charles Academy (RI)'
    )
    OR Home LIKE '%Opp "%(NH)' OR Visitor LIKE '%Opp "%(NH)'
    OR Home LIKE '%Opp "%(RI)' OR Visitor LIKE '%Opp "%(RI)'
)
ORDER BY Season, Date;

-- 6. Check New London Buckeley (CT) games after 1951 (Bulkeley School in New London closed in 1951!)
SELECT Season, COUNT(*) AS Games, MIN(Date) AS FirstD, MAX(Date) AS LastD
FROM dbo.HS_Scores
WHERE (Home = 'New London Buckeley (CT)' OR Visitor = 'New London Buckeley (CT)')
  AND Season >= 1951
GROUP BY Season
ORDER BY Season;
