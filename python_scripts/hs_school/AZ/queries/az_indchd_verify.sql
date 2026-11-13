SET NOCOUNT ON;
SELECT Remaining = COUNT(*) FROM dbo.HS_Scores
WHERE Source = 'http://www.azfootballarchives.com/indchd6.html'
  AND ((YEAR([Date]) = Season - 1 AND MONTH([Date]) = 12) OR (YEAR([Date]) = Season AND MONTH([Date]) = 1));
SELECT Fixed = COUNT(*) FROM dbo.HS_Scores
WHERE Source = 'http://www.azfootballarchives.com/indchd6.html'
  AND ((YEAR([Date]) = Season AND MONTH([Date]) = 12) OR (YEAR([Date]) = Season + 1 AND MONTH([Date]) = 1));
SELECT LogRows = COUNT(*), FirstAt = MIN(ChangedAt), LastAt = MAX(ChangedAt) FROM dbo.HS_Scores_Change_Log
WHERE Reason LIKE 'azfootballarchives indchd6%';
SELECT OpenTran = COUNT(*) FROM sys.dm_tran_session_transactions;
