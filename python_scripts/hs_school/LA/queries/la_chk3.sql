SELECT Now = SYSDATETIME(), StartTime = (SELECT sqlserver_start_time FROM sys.dm_os_sys_info);
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name IN ('Lafayette Teurlings Catholic (LA)','Metairie Archbishop Rummel (LA)','Shreveport Captain Shreve (LA)');
