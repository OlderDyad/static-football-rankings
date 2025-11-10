Master Workflow Document & Standard Operating Procedures
Primary Goal
To systematically import, clean, and enrich high school football data on a state-by-state basis, ensuring all data is properly aliased and classified by player level (e.g., 11-man, 8-man) and "Faux Conference" to support a robust rating system.

Part 1: The "New State Onboarding" Workflow
This is the primary workflow for processing a new state (like South Dakota) or running a new cleanup (like Florida).

Phase 1: Generate Alias "To-Do List"
Run the Script: From your PowerShell terminal, run the master Python script.

PowerShell

python consolidation_workflow.py
Enter State: Enter the 2-letter state code (e.g., SD).

Select Action: Choose Action #1: Generate or Update...

Result: The script calls dbo.sp_CreateStateCleanupList, finds all un-aliased teams for that state, and creates/updates the file: .../excel_files/State_Aliases_ProperNames/SD_Alias_Rules.csv

Phase 2: Manual Processing ("The 80/20 Rule")
Open the CSV: Open SD_Alias_Rules.csv in Excel.

Prioritize: Sort the list by the GameCount column, descending.

Process "Big Wins": Following our "big picture" strategy, fill in the Standardized_Name for the high-priority, high-count teams that you can easily identify.

"Peck Away Later": Leave the Standardized_Name blank for any low-count, out-of-state, or ambiguous teams that would require too much research. The script will safely ignore these.

Save and close the CSV file.

Phase 3: Consolidate Data
Run the Script: Run python consolidation_workflow.py again.

Enter State: Enter the same state code (e.g., SD).

Select Action: Choose Action #2: Run the consolidation...

Result: The script uploads the CSV to the ConsolidationRules_Staging table and executes our fully-optimized dbo.sp_ConsolidateNames_FromStaging procedure. This procedure:

Updates dbo.HS_Team_Names with any new teams.

Merges any conflicting team records.

Updates all child tables (dbo.games, dbo.HS_Team_Media, dbo.HS_Team_MaxPreps, etc.) to prevent foreign key errors.

Runs a single, fast, bulk update on dbo.HS_Scores to clean the historical data.

Phase 4: Initial Data Enrichment
Run SQL Script 1 (Populate History): Run a SQL script to populate our new history tables with default values for all the teams we just consolidated (found in dbo.ConsolidationRules_Staging).

dbo.HS_Team_Level_History: PlayerLevel = 11, Season_Begin = 1970, Season_End = 9999

dbo.HS_Team_Conference_History: Faux_Conference = 'SD - Statewide', Season_Begin = 1970, Season_End = 9999

Run SQL Script 2 (Refine Conferences): Run a follow-up SQL script to move obvious metro teams (e.g., "Sioux Falls...") from the "Statewide" bucket to their correct "Faux Conference" (e.g., SD - Sioux Falls Metro).

Part 2: The "Historical Level Correction" Workflow
This is our investigative "side project" for refining PlayerLevel (11-man vs. 8-man) for a state after its initial onboarding is complete.

Phase 1: Broad Analysis (The 10-Year Query)
Run the Query: Run our 10-year analysis query for a sample of teams (e.g., Algona Bishop Garrigan (IA), Audubon (IA)).

Identify Patterns:

Transition Years: Look for a clean "snap" where a team's opponents switch from IA - Statewide to IA - 8-Man (All) (e.g., Audubon (IA) in 2015/2016).

Pollution: Look for a team that should be 8-man but shows a schedule full of IA - Statewide opponents (e.g., our initial Algona Bishop Garrigan (IA) anomaly).

Real Anomalies: Look for a team that should be 8-man but played one or two real 11-man games (e.g., Lenox (IA) vs. Martensdale-Saint Mary's (IA) in 2021).

Phase 2: Targeted Investigation
For "Transition Years": We have our answer. Proceed to Phase 3.

For "Pollution": Run our targeted query (like the one from my previous message) to get a "to-do list" of all the 8-man teams that are incorrectly classified as IA - Statewide.

Phase 3: Surgical Correction (SQL)
Run SQL Scripts: Based on the findings from Phase 2, run targeted SQL scripts to:

Fix Transitions: UPDATE the 11-man history to set Season_End and INSERT a new 8-man record with the correct Season_Begin. (e.g., the fix for Audubon (IA)).

Fix Pollution: UPDATE the misclassified teams, changing their PlayerLevel to 8 and their Faux_Conference to IA - 8-Man (All).

Phase 4: Verification
Re-run the Phase 1 Query: Run the 10-year analysis query again to confirm the data is now clean and all transitions/classifications are correct.

Iterate: If new !! UNKNOWN !! teams are found, add them via the Part 1 workflow.

Immediate Next Steps (Our To-Do List)
Based on this plan, here are our outstanding tasks:

Run Florida (FL) Consolidation: Run Part 1, Phase 3 for Florida to finalize that state's data.

Start South Dakota (SD): Begin Part 1, Phase 1 for South Dakota to generate its SD_Alias_Rules.csv file.

Continue Iowa 8-Man Hunt: We are currently in Part 2, Phase 1 for Iowa. We fixed the major anomalies, so the next step would be to run the targeted query from Part 2, Phase 2 to find all the other teams polluting the IA - Statewide conference, or to identify the remaining !! UNKNOWN !! teams.