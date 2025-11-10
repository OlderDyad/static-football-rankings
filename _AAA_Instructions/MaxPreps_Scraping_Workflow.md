MaxPreps Scraping Workflow

Summery Steps:
CD C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\

python maxpreps_scraper_db.py


This process uses a Python script for scraping and a SQL stored procedure for data processing.

1. Run the Scraper (Python)
Execute the maxpreps_scraper_db.py script from your terminal:

Bash

python maxpreps_scraper_db.py
What it does:

Connects to the hs_football_database.

Finds the current 'running' batch or creates a new one in dbo.scraping_batches and dbo.team_scraping_status.

Fetches the next chunk of team URLs and names to process from dbo.URL_ProperName_Mapping based on the batch status.

Uses Selenium to visit each MaxPreps schedule page.

Scrapes the raw game data (date, opponent string, result/time string, opponent URL).

Saves this raw data directly into the dbo.games_raw table, tagging it with the current batch_id.

Updates the status for each processed team in dbo.team_scraping_status.

Prints a completion message with the batch_id needed for the next step.

2. Process the Raw Data (SQL)
Connect to your hs_football_database using SQL Server Management Studio (SSMS) or another tool.

Execute the stored procedure, replacing [Your_Batch_ID] with the ID provided by the Python script:

SQL

EXEC dbo.FinalizeMaxPrepsData @BatchID = [Your_Batch_ID];
What it does:

Reads all rows from dbo.games_raw for the specified batch.

Cleans the raw data (extracts names, handles date formats, ignores invalid rows like 'LIVE' or 'Date TBA').

Determines the correct Home and Away teams.

Parses scores for completed games.

Generates a unique GameID (e.g., YYYYMMDD-TeamA-TeamB).

Performs a two-step lookup: uses dbo.HS_Team_Name_Alias to find the standardized name, then dbo.HS_Team_Names to get the final Team_ID.

Sorts the processed games:

Completed Games (with scores and recognized teams) are inserted into dbo.HS_Scores.

Future Games (no scores, but recognized teams) are inserted into dbo.Future_Games.

Unmatched Games (where one or both teams weren't found in the alias tables) are inserted into dbo.Unmatched_Games.

3. Review Unmatched Games (Manual SQL)
Query the dbo.Unmatched_Games table to see if any games require manual attention:

SQL

SELECT * FROM dbo.Unmatched_Games WHERE BatchID = [Your_Batch_ID] AND Status = 'pending'; -- Assuming a Status column exists
If the query returns rows: Proceed to Step 4.

If the query is empty: The batch is fully processed! ✅ You can run the Python scraper again to continue the batch or start a new one.

4. Fix Unmatched Games (Manual SQL)
For each row in the dbo.Unmatched_Games results:

Identify the RawHomeTeam or RawAwayTeam that wasn't recognized.

If it's a brand new school: Add it to your master dbo.HS_Team_Names table first.

Add the alias: Create a new entry in dbo.HS_Team_Name_Alias mapping the raw name to the correct standardized name (which links to the ID in HS_Team_Names).

(Optional: You might want to update the Status in dbo.Unmatched_Games to 'resolved').

5. Re-Process the Batch (SQL)
Once you've added the necessary aliases, re-run the stored procedure for the same batch:

SQL

EXEC dbo.FinalizeMaxPrepsData @BatchID = [Your_Batch_ID];
The procedure will now recognize the previously unmatched teams and move those games into dbo.HS_Scores or dbo.Future_Games. Your "unmatched" query (Step 3) should now be empty for this batch.

6. Repeat
Run the Python scraper again to process the next set of URLs in the batch or to start a new batch if the current one is complete.