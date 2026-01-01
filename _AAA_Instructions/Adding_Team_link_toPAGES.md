WORKFLOW: Adding Team/Program Pages to Rating Tables
Overview
This workflow covers how to add clickable links to individual team or program pages in any rating table (All-Time, State, Decade, Latest Season, National Champions, etc.).
Last Updated: December 31, 2025
Status: Active

Prerequisites
Required Components

Database Table: HS_Team_Names with team metadata
Database Fields:

Has_Program_Page (BIT) - Flag indicating page exists
Program_Page_URL (NVARCHAR) - Relative URL to page


FontAwesome CDN - Loaded in page template for link icons
Python/PowerShell Generators - Scripts that create JSON and HTML

Team Page Structure
Individual team pages live at:
/static-football-rankings/pages/teams/{state}/{state-city-school}/index.html

Example: /static-football-rankings/pages/teams/wa/wa-everett-everett/index.html

Phase 1: Database Setup
Step 1: Update HS_Team_Names Table
Add the team's program page information to the database:
sql-- Set program page flag and URL
UPDATE HS_Team_Names
SET 
    Has_Program_Page = 1,
    Program_Page_URL = '/static-football-rankings/pages/teams/{state}/{state-city-school}/index.html'
WHERE ID = {team_id};

-- Example: Everett (WA)
UPDATE HS_Team_Names
SET 
    Has_Program_Page = 1,
    Program_Page_URL = '/static-football-rankings/pages/teams/wa/wa-everett-everett/index.html'
WHERE ID = 40046;
Verification:
sqlSELECT ID, Team_Name, State, Has_Program_Page, Program_Page_URL
FROM HS_Team_Names
WHERE Has_Program_Page = 1;

Phase 2: JSON Generation (Python/PowerShell)
Current Implementation Pattern
All JSON generators follow this pattern:
python# In Python generator (e.g., generate_all_time_teams.py)

# 1. SQL procedure returns these fields:
#    - hasProgramPage (from Has_Program_Page)
#    - programPageUrl (from Program_Page_URL)

# 2. Python adds teamLinkHtml field:
if champion.get('hasProgramPage') and champion.get('programPageUrl'):
    # Team has a program page - show clickable link icon
    champion['teamLinkHtml'] = f'<a href="{champion["programPageUrl"]}" class="team-link" title="View {champion["team"]} program page"><i class="fas fa-external-link-alt"></i></a>'
else:
    # No program page yet - show placeholder square
    champion['teamLinkHtml'] = '<span class="no-page-icon" style="color:#ddd;" title="Page coming soon">&#9633;</span>'
Files That Need This Logic
Python Generators:

generate_all_time_teams.py ✅ (All-Time Teams)
generate_all_time_programs.py ✅ (All-Time Programs)
generate_decade_teams.py ✅ (Decade Teams)
generate_decade_programs.py ✅ (Decade Programs)
generate_state_teams.py ✅ (State Teams)
generate_state_programs.py ✅ (State Programs)
generate_latest_season.py ✅ (Latest Season)
generate_media_champions_json.py ✅ (Media NC)

PowerShell Generators:

Generate-McKnightNationalChampions.ps1 ✅ (McKnight NC)

Required SQL Procedure Updates
Each stored procedure needs to include:
sql-- Example from sp_GetAllTimeTeams
SELECT 
    -- ... other fields ...
    
    -- Page linking data
    tn.ID AS teamId,
    ISNULL(tn.Has_Program_Page, 0) AS hasProgramPage,
    tn.Program_Page_URL AS programPageUrl
    
FROM HS_Rankings R
LEFT JOIN HS_Team_Names tn ON R.Home = tn.Team_Name AND R.State = tn.State
Procedures to Update:

sp_GetAllTimeTeams ✅
sp_GetAllTimePrograms ✅
sp_GetDecadeTeams ✅
sp_GetDecadePrograms ✅
sp_GetStateTeams ✅
sp_GetStatePrograms ✅
sp_Get_Latest_Season_Teams ✅
sp_Get_Media_National_Champions ✅
sp_Get_McKnight_National_Champions ✅


Phase 3: HTML Template Updates
Step 1: Add FontAwesome CDN
Ensure template has FontAwesome loaded:
html<head>
    <!-- ... other head content ... -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
Step 2: Add Link Column to Table
html<thead>
    <tr>
        <!-- ... other columns ... -->
        <th class="text-center" style="min-width: 50px">Link</th>
    </tr>
</thead>
Templates to Update
All-Time:

all-time-teams-template.html ✅
all-time-programs-template.html ✅

Decades:

decade-teams-template.html ✅
decade-programs-template.html ✅

States:

state-teams-template.html ✅
state-programs-template.html ✅

Latest Season:

latest-season-template.html ✅

National Champions:

media-national-champions-template.html ✅
mcknight-national-champions-template.html ✅


Phase 4: PowerShell HTML Generation
Current Implementation (GenerateAllPages.ps1)
PowerShell functions that generate HTML tables need to output the Link column:
powershell# Example from Process-McKnightNationalChampions
$tableRows = $championsData.items | ForEach-Object {
    # ... format other columns ...
    
    @"
    <tr>
        <td>$($_.year)</td>
        <td>$($_.team)</td>
        <!-- ... other columns ... -->
        <td class="text-center">$($_.teamLinkHtml)</td>
    </tr>
"@
}
Functions to Update:

Process-MediaNationalChampions ✅
Process-McKnightNationalChampions ✅
Process-AllTimeData ✅ (uses Generate-TableRows helper)
Process-DecadeData ✅ (uses Generate-TableRows helper)
Process-StateData ✅ (uses Generate-TableRows helper)
Process-LatestSeasonData ✅ (uses Generate-TableRows helper)


Phase 5: Master Update Cycle
Standard Workflow
After adding a new team page, run the master update cycle:
powershellcd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts
.\run_update_cycle.ps1
This will:

Sync Google Sheets & Images to SQL
Generate State Data (JSON)
Generate Global Data (All-Time, Decades, Latest, NC JSONs)
Generate Statistics
Rebuild HTML Pages
Push to GitHub

Manual Regeneration (If Needed)
If you only updated the database and need to regenerate specific pages:
powershell# Regenerate All-Time Teams JSON
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
python generate_all_time_teams.py

# Regenerate HTML
cd ..\..\scripts
.\GenerateAllPages.ps1

# Push to GitHub
cd ..
git add docs/data docs/pages
git commit -m "Add program page link for [Team Name]"
git push origin main

Testing Checklist
After adding a new team page link:
JSON Validation
powershell# Check JSON contains correct fields
$json = Get-Content "docs\data\all-time\all-time-teams.json" -Raw | ConvertFrom-Json
$team = $json.items | Where-Object { $_.team -like "*Everett*" }
$team | Select-Object team, hasProgramPage, programPageUrl, teamLinkHtml
Expected Output:

hasProgramPage: True
programPageUrl: /static-football-rankings/pages/teams/wa/...
teamLinkHtml: <a href="..."><i class="fas fa-external-link-alt"></i></a>

HTML Validation
powershell# Check HTML contains link icon
Select-String -Path "docs\pages\public\all-time\teams.html" -Pattern "fa-external-link-alt"
Live Site Testing

Navigate to the rating page (e.g., All-Time Teams)
Find the team in the table
Verify link icon appears in Link column
Click link - should navigate to team page
No 404 errors


Troubleshooting
Link Icon Not Appearing
Issue: Square placeholder shows instead of link icon
Causes:

FontAwesome CDN not loaded in template
Has_Program_Page not set to 1 in database
JSON generator not creating teamLinkHtml field

Fix:
sql-- Verify database
SELECT Has_Program_Page, Program_Page_URL FROM HS_Team_Names WHERE ID = {team_id};

-- Check JSON
Get-Content {json_file} | Select-String -Pattern "teamLinkHtml"
Link Goes to 404
Issue: Clicking link shows "Page not found"
Causes:

Program_Page_URL incorrect in database
Team page doesn't actually exist yet
URL path mismatch

Fix:
sql-- Update URL
UPDATE HS_Team_Names
SET Program_Page_URL = '/static-football-rankings/pages/teams/{state}/{state-city-school}/index.html'
WHERE ID = {team_id};
TABLE_ROWS Not Replaced
Issue: HTML shows literal TABLE_ROWS text
Causes:

Template updated but HTML not regenerated
PowerShell function not outputting Link column
JSON missing teamLinkHtml field

Fix:
powershell# Regenerate HTML
.\GenerateAllPages.ps1

Future Enhancements
Planned Features

Bulk Import Script - Add multiple team pages at once from CSV
Auto-Detection - Scan /pages/teams/ directory and auto-update database
Page Status Dashboard - Visual report of which teams have pages
Link Validation - Automated testing of all program page URLs

Scale Considerations

Currently: 1 team with page (Everett 1920)
Phase 4A Target: 140 teams (Media National Champions)
Phase 4B Target: 16,000+ teams (All teams)

Performance Note: With 16,000 teams, consider:

Database indexing on Has_Program_Page
Lazy loading for rating tables
CDN caching for JSON files


Quick Reference
Add New Team Page Link (Complete Steps)
sql-- 1. Update database
UPDATE HS_Team_Names
SET Has_Program_Page = 1,
    Program_Page_URL = '/static-football-rankings/pages/teams/{state}/{state-city-school}/index.html'
WHERE ID = {team_id};
powershell# 2. Run master update cycle
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts
.\run_update_cycle.ps1

# 3. Wait for GitHub Pages to rebuild (~2-5 min)

# 4. Test on live site
Done! The team now has a clickable link in all rating tables.

Related Documentation

Master Update Cycle: ___MASTER_UPDATE_CYCLE__v6.md
Phase 4 Development: all-time_teams_generation.md
Database Schema: HS_Team_Names_Schema.md
GitHub Deployment: Github_static-football-rankings_repository_structure.md


Changelog
2025-12-31:

Initial workflow created
Documented Everett (WA) as first team with page
All core systems updated with link functionality
Media NC and McKnight NC pages completed

Next Steps:

Scale to 140 Media National Champions (Phase 4A)
Create bulk import workflow
Add validation testing suite