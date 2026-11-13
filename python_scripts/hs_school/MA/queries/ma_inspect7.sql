-- 1. Inspect the games of the small mystery/typo names in MA
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE Home IN (
    'Acton-Foxboro (MA)', 'Boxborough (MA)', 'Carlisle (MA)', 'Lincoln (MA)', 'Sudbury (MA)',
    'Georgetown Perley (MA)', 'Holbrook Sumner (MA)', 'Ipswich Manning (MA)', 'Manchester Story (MA)', 'Story (MA)',
    'Brookline Rivers Country Day (MA)', 'Cushing-Wichendon (MA)', 'Pentomonet Regional (MA)',
    'Tahant (MA)', 'Tahanto (MA)', 'North Middleborough (MA)', 'Wrentham (MA)', 'Hatfield Smith Academy (MA)',
    'Great Barrington Searles (MA)', 'FIX_ME Boston (MA)', 'Dale (MA)', 'Brook (MA)', 'W. Brook (MA)',
    'Keith (MA)', 'King (MA)', 'Lester (MA)', 'Munson (MA)', 'Pilgrim (MA)', 'Wells (MA)',
    'West Middlesex (MA)', 'Western (MA)', 'Whalen (MA)', 'Topsfield (MA)', 'Yarmouth (MA)'
) OR Visitor IN (
    'Acton-Foxboro (MA)', 'Boxborough (MA)', 'Carlisle (MA)', 'Lincoln (MA)', 'Sudbury (MA)',
    'Georgetown Perley (MA)', 'Holbrook Sumner (MA)', 'Ipswich Manning (MA)', 'Manchester Story (MA)', 'Story (MA)',
    'Brookline Rivers Country Day (MA)', 'Cushing-Wichendon (MA)', 'Pentomonet Regional (MA)',
    'Tahant (MA)', 'Tahanto (MA)', 'North Middleborough (MA)', 'Wrentham (MA)', 'Hatfield Smith Academy (MA)',
    'Great Barrington Searles (MA)', 'FIX_ME Boston (MA)', 'Dale (MA)', 'Brook (MA)', 'W. Brook (MA)',
    'Keith (MA)', 'King (MA)', 'Lester (MA)', 'Munson (MA)', 'Pilgrim (MA)', 'Wells (MA)',
    'West Middlesex (MA)', 'Western (MA)', 'Whalen (MA)', 'Topsfield (MA)', 'Yarmouth (MA)'
)
ORDER BY Season, [Date];
