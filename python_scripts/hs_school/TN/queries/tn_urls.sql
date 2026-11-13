SELECT u.ProperName, u.URL FROM dbo.URL_ProperName_Mapping u
WHERE u.ProperName IN ('Coalfield Yellow (TN)','Coalfield (TN)','Greeneville Greene (TN)','Greeneville (TN)','Jackson Central (TN)','Jackson Central-Merry (TN)','Jackson North (TN)','Jackson North Side (TN)',
'Jackson South (TN)','Jackson South Side (TN)','Jackson University School (TN)','Jackson University School of Jackson (TN)','Knoxville Austin East (TN)','Knoxville Austin-East (TN)',
'Murfreesboro Middle Tennessee (TN)','Murfreesboro Middle Tennessee Christian (TN)','Nashville Overton (TN)','Nashville John Overton (TN)','East Nashville Magnet (TN)','Nashville East Nashville Magnet (TN)',
'Seymour Kings Academy (TN)','Seymour King''s Academy (TN)','Unionville Community Vikings (TN)','Unionville Community (TN)','Watertown Purple (TN)','Watertown (TN)','Decaturville Riverside (TN)','Decatur County-Riverside (TN)',
'Soddy Daisy (TN)','Soddy-Daisy (TN)','Christian Academy of Knoxville (TN)','Mount Juliet Middle Tennessee Heat (TN)','Tennessee School for the Deaf (TN)','Nashville Hillwood (TN)','Nashville Lawson (TN)')
ORDER BY u.ProperName;
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name IN ('Hopkinsville Christian County (KY)','Hickman Fulton County (KY)','Fulton County (KY)','Hickman County (KY)') OR Team_Name LIKE '%Fulton County (KY)';
