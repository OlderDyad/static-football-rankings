📜 SOP: State Alias Consolidation Workflow
This document outlines the standard procedure for identifying, aliasing, and retroactively correcting team names using the consolidation_workflow.py script.

File Location: All alias files (e.g., IA_Alias_Rules.csv) will be created and read from this folder: C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\State_Aliases_ProperNames

This workflow is a two-step process, both handled by the same Python script.

Phase 1: Generate Alias Worksheet
Objective: To find all new, un-aliased team names for a state and create a CSV file (your "to-do list").

Open your terminal:

Navigate to your script directory: 



Activate your virtual environment (if needed): 

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts

..\venv\Scripts\Activate

Run the script:

**CD C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\**

**python consolidation_workflow.py**

for latin letters names
**python consolidation_workflow_latin.py**

===========================================
Workflow for finding Long & Lat or non conforming names

CD C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import

**python consolidation_workflow_w_geo.py**

To create new LL_alias file use option #3.

To update names in HS_Scores table
Use option #2, then use **LL** for state code.

**python geo_locator.py**

This will look for long-Lat for each team in the "LL" file.

============================================

python push_HS_Names_export_to_sheets.py

Enter the State Code:

When prompted, type IA and press Enter.

Select the Action:

The script will ask for your choice. Type 1 and press Enter.

Script action: 1: Generate or Update the correction file for this state.

What Happens Now:

The script runs the dbo.sp_CreateStateCleanupList procedure in SQL Server for Iowa (IA).

It finds all un-aliased names and their game counts.

It creates a new file named IA_Alias_Rules.csv in the ...excel_files\State_Aliases_ProperNames folder.

This file will have three columns: Alias_Name, GameCount, and Standardized_Name.

Phase 2: Manual Processing (The CSV)
Objective: To use your research to fill in the correct canonical name for each raw name.

Find the File:

Go to the ...excel_files\State_Aliases_ProperNames folder.

Open IA_Alias_Rules.csv with Excel.

Fill in the Blanks:

Go row by row and fill in the Standardized_Name column with the correct, full canonical name (e.g., Des Moines Roosevelt (IA), Cedar Rapids Washington (IA)).

Save and close the file.

Phase 3: Consolidate & Clean Up Data
Objective: To apply your corrections to the dbo.HS_Scores table, retroactively cleaning up all the data.

Run the script again:

From the same terminal, execute the script: 

**python consolidation_workflow.py**

Enter the State Code:

When prompted, type IA and press Enter.

Select the Action:

This time, type 2 and press Enter.

Script action: 2: Run the consolidation using the completed correction file for this state.

What Happens Now:

The script reads your completed IA_Alias_Rules.csv.

It uploads the Alias_Name and Standardized_Name columns to a temporary staging table in SQL Server.

It runs the dbo.sp_ConsolidateNames_FromStaging procedure.

This procedure automatically updates both dbo.HS_Team_Name_Alias (your master list) and dbo.HS_Scores (the historical game data), replacing all raw names with their proper canonical names.

This new workflow is a complete, self-contained loop. You can now start by running Phase 1 to create your IA_Alias_Rules.csv file.