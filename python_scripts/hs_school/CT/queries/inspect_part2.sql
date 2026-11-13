-- 1. Sample New London Buckeley (CT) games 1951-2003
SELECT TOP 40 Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
FROM dbo.HS_Scores
WHERE (Home = 'New London Buckeley (CT)' OR Visitor = 'New London Buckeley (CT)')
  AND Season >= 1951
ORDER BY Season, Date;

-- 2. Bristol (CT), Fairfield (CT), Fairfield College Prep (CT), New Haven (CT), Meriden (CT) post-1957
SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE Home IN ('Bristol (CT)', 'Fairfield (CT)', 'Fairfield College Prep (CT)', 'New Haven (CT)')
   OR Visitor IN ('Bristol (CT)', 'Fairfield (CT)', 'Fairfield College Prep (CT)', 'New Haven (CT)')
   OR ((Home = 'Meriden (CT)' OR Visitor = 'Meriden (CT)') AND Season >= 1958)
ORDER BY Season, Date;

-- 3. Pawtucket (RI) 1940-1970 and Cranston (RI) 1959-1984 and Bristol Mt. Hope (RI) pre-1993
SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE ((Home = 'Pawtucket (RI)' OR Visitor = 'Pawtucket (RI)') AND Season >= 1940)
   OR ((Home = 'Cranston (RI)' OR Visitor = 'Cranston (RI)') AND Season >= 1959)
   OR ((Home = 'Bristol Mt. Hope (RI)' OR Visitor = 'Bristol Mt. Hope (RI)') AND Season < 1993)
ORDER BY Season, Date;

-- 4. Check what games Providence Hope St. Academy (RI) has in 2024
SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
FROM dbo.HS_Scores
WHERE Home = 'Providence Hope St. Academy (RI)' OR Visitor = 'Providence Hope St. Academy (RI)'
ORDER BY Date;

-- 5. Check what games Farmington River (CT) has in 2024-2026
SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source
FROM dbo.HS_Scores
WHERE Home = 'Farmington River (CT)' OR Visitor = 'Farmington River (CT)'
ORDER BY Date;
