SELECT State,
       DoneSteps = SUM(CASE WHEN Status = 'done' THEN 1 ELSE 0 END),
       InProgSteps = SUM(CASE WHEN Status = 'in progress' THEN 1 ELSE 0 END),
       LastUpdated = MAX(Updated)
FROM dbo.HS_Cleanup_Status
GROUP BY State
ORDER BY MIN(Updated), State;
