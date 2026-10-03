MaxPreps Scraping Workflow

**Superseded 2026-09-19.** Everything below the old manual six-step process
(kept at the bottom for historical reference — it explains where some of
the current automation's design choices came from) describes how this
worked through December 2025. As of this season, the whole thing is
automated: a watcher script fires the scraper nightly, and the scraper
finalizes its own data every night. No manual `EXEC` or `SSMS` step is
required in normal operation anymore.

---

## Current workflow (2026 season onward)

**You do not run anything manually for the normal nightly cycle.**
`maxpreps_watcher.ps1` (in `python_scripts\data_import\`) runs continuously,
fires `run_maxpreps_scraper.ps1` every night at 9PM (capped at 8 hours), which
runs `maxpreps_scraper_db.py`. The scraper now calls
`EXEC dbo.FinalizeMaxPrepsData` itself after every night's chunk — games
land in `HS_Scores` within a day of being scraped, not just once at full
batch completion.

Full detail, incident history, and exactly what to do if something looks
wrong live in `STATE_ONBOARDING_AND_CLEANUP_GUIDE.md`, under
**"Tool: `maxpreps_scraper_db.py` overnight automation"** — that's the
authoritative reference now, not this file. Highlights:

- **Trigger mechanism**: `maxpreps_watcher.ps1`, not Windows Task Scheduler.
  Task Scheduler's unattended logon mode needs a stored password, and this
  machine's account is passwordless (Windows Hello PIN only) — confirmed
  dead end. The watcher runs as an ordinary interactive-session process
  instead. It does not survive reboot/logout yet (a Startup-folder shortcut
  is planned but not yet created) — if the PC restarts, the watcher needs
  to be relaunched by hand (see the guide for the launch command).
- **Checking it's alive**: `maxpreps_watcher_log.txt` (heartbeats + nightly
  fire confirmation), `maxpreps_wrapper_log.txt` (per-run start/stop),
  `maxpreps_scraper_log.txt` (the scraper's own detailed log) — all in
  `data_import/`.
- **Checking data actually landed** (not just "scraped" — these are now
  different questions since finalize runs automatically):
  ```sql
  SELECT COUNT(*) FROM HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = 2026;
  ```
- **If you ever need to finalize manually** (e.g. recovering from an error):
  ```sql
  EXEC dbo.FinalizeMaxPrepsData @BatchID = <B>;
  ```
  This is now safe to call repeatedly on the same batch — a
  `NOT EXISTS`-guarded `Unmatched_Opponents` insert was added 2026-09-19
  (see the guide) specifically so this no longer duplicates rows.
- **Unmatched opponents live in `dbo.Unmatched_Opponents`, not
  `dbo.Unmatched_Games`** (the table this doc used to reference — renamed/
  redesigned since December 2025). Columns: `UnmatchedID`, `BatchID`,
  `PrimaryTeamName`, `OpponentNameRaw`, `OpponentMaxPrepsURL`,
  `GameDateRaw`, `ResultText`, `LoggedAt`, `Resolved`, `ResolvedNote`,
  `RawGameID` — no `Status` column; use `Resolved` (bit) instead of the
  `Status = 'pending'` pattern the old steps below describe.
- **Opponent matching is now URL-based, not name/alias-based.** The old
  Step 2 below describes a `HS_Team_Name_Alias` lookup for opponent
  resolution — that's no longer how it works. `FinalizeMaxPrepsData` now
  matches each scraped opponent by their MaxPreps URL against
  `URL_ProperName_Mapping` (+ `URL_ProperName_Mapping_Aliases` for teams
  with a since-changed URL). If you're trying to resolve an unmatched
  opponent today, add a row to `URL_ProperName_Mapping` (new team) or
  `URL_ProperName_Mapping_Aliases` (existing team, URL changed) — not
  `HS_Team_Name_Alias`.
- **A large, permanently-`pending` chunk of `team_scraping_status` is
  expected, not a bug.** As of 2026-09-19, ~6,552 rows (973 distinct teams)
  sit `pending` forever because they lack a `URL_ProperName_Mapping` entry.
  This is documented, known behavior (see `_AAA_Instructions/
  Re-Importing_MaxPreps_Data.md`) — these rows are invisible to the
  scraper's "am I done" check, so they don't block anything. Investigation
  found every one of these 973 is a **duplicate `HS_Team_Names` record**
  for a team that already has a correctly-mapped sibling — not a real gap
  to backfill. See the guide for the full writeup; this is being handled as
  a team-record consolidation task, folded into the ongoing per-state alias
  cleanup work, not a URL-mapping fix.

---

## Task #52: MaxPreps name-drift / duplicate-team-record cleanup (started 2026-09-19)

**Root cause behind the 973-duplicate-team finding above**: comparing every
distinct team name appearing in `HS_Scores` for Season=2025 vs Season=2026
(`compare_2025_2026_team_names.py`, in `data_import/`) found 16,120 2025
names vs 6,829 2026 names, 6,218 in both (ignore), 9,902 2025-only (mostly
expected — season in progress, batch 33 still catching up), and 611
2026-only. Fuzzy-matching the 611 residual 2026-only names against the
2025-only residuals, same-state only, found **477 of the 611 (78%) are
near-perfect matches for an existing 2025 team name** — almost entirely one
systematic pattern: a hyphen replaced with a space (`Tuloso Midway` vs
`Tuloso-Midway`), plus a smaller cluster of apostrophes stripped (`O'Neill`
→ `Oneill`) and `St.`→`Saint` expansion. This points at whatever process
auto-generates a `ProperName` from a MaxPreps URL slug for a newly-added
team applying a naive `slug.replace('-',' ').title()`-style transform to
the *whole* slug — correct for city names (per the general "avoid
abbreviations in the city segment" convention), wrong for compound
school/district names where the hyphen is genuinely part of the name.
**The actual code responsible for this has not yet been located** — that's
open follow-up work, not done in this session.

**Decision (2026-09-19): route the fix through the existing state-aliasing
workflow rather than a bespoke merge script.** Treat each mangled 2026
scraped name as an `Alias_Name`, the correct existing 2025 name as its
`Standardized_Name`, and let `consolidation_workflow_latin.py` (Action 1 to
generate/update `<STATE>_Alias_Rules.csv`, Action 2 to consolidate via
`sp_ConsolidateNames_FromStaging`) handle it exactly like any other raw-name
cleanup — same tooling, same "edit an existing row in place, never append a
duplicate `Alias_Name`" convention documented in the main guide. **Known
tradeoff**: unlike a root-cause code fix, this doesn't stop the underlying
`URL_ProperName_Mapping.ProperName` from generating the same mangled name
again next time that team gets scraped — it's a recurring correction, not a
one-time elimination, same as how newspaper-OCR aliasing already works.
Acceptable given it reuses trusted tooling; revisit if the recurring
maintenance cost turns out to be heavier than expected.

**Handoff artifact**: `export_2025_2026_name_matches.py` (in `data_import/`)
writes `maxpreps_name_drift_candidates_2026.csv` — columns `State,
Alias_Name_2026_Scraped, Standardized_Name_2025_Existing, Similarity_Score,
Review_Status` (`auto-safe` if score ≥ 0.9, `REVIEW-NEEDED` below that).
**Do not bulk-apply `REVIEW-NEEDED` rows blindly** — the low-confidence tail
contains real false positives that need a human glance (e.g. `Midland
Legacy (TX)` vs `Midland Lee (TX)` looked like noise but is actually a
genuine institutional rename — same team switched back to its old name
after a few years — confirmed by the user, not the hyphen-bug pattern at
all).

**Correction (2026-09-19), supersedes the date-scoped guidance originally
written here**: `Midland Legacy` was a brief rename (Confederate-general
naming controversy — "Lee" refers to Robert E. Lee) that has since
reverted back to `Midland Lee`. Per the user's actual naming convention,
a rename like this is **not** date-scoped — all historical games
consolidate under the team's current/enduring name, and if the name
changes again in the future, all historical games get re-pointed to
whichever name is current at that time. Date-scoped treatment (keeping
the interim name for games played during that window, as in the Trafton
Academy → Chapel Trafton case in the main guide) only applies to a
*permanent* rename/split where the old and new identities are meant to
stay distinct going forward — not to a name that later reverted.
`TX_Alias_Rules.csv` already has this correctly set (`Midland Legacy (TX)
-> Midland Lee (TX)`, confirmed correct as of 2026-09-19, no action
needed).

**Suggested order for whoever picks this up**: (1) apply the `auto-safe`
rows via the normal Action 1/2 alias-consolidation flow, per state; (2)
manually review the `REVIEW-NEEDED` rows one by one, watching for genuine
renames vs. real false positives vs. genuine near-duplicates that just
scored lower; (3) separately, try to actually locate and fix the
name-generation code causing the hyphen/apostrophe stripping, so future
seasons don't regenerate this same problem — not done as of 2026-09-19.

**Status update (2026-09-19)**: steps (1) and (2) above are done. All 219
`auto-safe` rows and 236 of the 258 `REVIEW-NEEDED` rows (after a manual
triage pass — see `maxpreps_name_drift_review_triaged_2026.csv` next to the
candidates file for the full breakdown, including which rows were rejected
as false positives and why) have been applied to the per-state
`*_Alias_Rules.csv` files. States with a real change from this work, still
needing an Action 2 consolidation run: **FL, IA, LA, MO, SD, TN, TX, MN,
ND, OK**. Step (3), locating the actual name-generation code, is still open
— worth noting a *second*, separate corruption pattern was found during the
triage: something matches `St` without a word boundary and splits words
mid-stream (`Stroudsburg` → `St. roudsburg`, `Stevens` → `St. evens`,
`Stanton` → `St. anton`, etc.) — distinct from the hyphen-to-space bug,
and also still unlocated.

**Tooling note (2026-09-19): `consolidation_workflow_latin.py` is now the
only active script for this.** It gained a `US` option at the state
prompt (Action 1 refreshes every state's GameCounts, Action 2 consolidates
every state in sequence), reusing the same NaN-safety validation guard for
each state rather than skipping it the way the old batch mode did. The
predecessor scripts, `consolidation_workflow.py` and
`consolidation_workflow_v3.py`, had their own `US` option but **without**
that guard — they're archived as `consolidation_workflow_old.py` and
`consolidation_workflow_v3_old.py` in `data_import/` and should not be
used. `consolidation_workflow_w_geo.py` is unrelated (lat/long backfill)
and is still active.

---

## Historical reference: the old manual workflow (through December 2025)

Kept for context — explains the shape some of the current automation's
fixes were responding to (e.g. the "mark batch completed" SQL step below
is exactly the gap that caused last year's automation to silently stop
producing data; it's now automatic).

Summery Steps:
CD C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\

**python maxpreps_scraper_db.py**

sql
EXEC dbo.FinalizeMaxPrepsData @BatchID = [Your_Batch_ID];


This process uses a Python script for scraping and a SQL stored procedure for data processing.

1. Run the Scraper (Python)
Execute the maxpreps_scraper_db.py script from your terminal:

Bash

**python maxpreps_scraper_db.py**
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
[SUPERSEDED — this is now a URL-based lookup via URL_ProperName_Mapping, see above]

Sorts the processed games:

Completed Games (with scores and recognized teams) are inserted into dbo.HS_Scores.

Future Games (no scores, but recognized teams) are inserted into dbo.Future_Games.

Unmatched Games (where one or both teams weren't found in the alias tables) are inserted into dbo.Unmatched_Games.
[SUPERSEDED — table is now dbo.Unmatched_Opponents, see above]

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
[SUPERSEDED — add to URL_ProperName_Mapping / URL_ProperName_Mapping_Aliases instead, see above]

(Optional: You might want to update the Status in dbo.Unmatched_Games to 'resolved').

5. Re-Process the Batch (SQL)
Once you've added the necessary aliases, re-run the stored procedure for the same batch:

SQL

EXEC dbo.FinalizeMaxPrepsData @BatchID = [Your_Batch_ID];
The procedure will now recognize the previously unmatched teams and move those games into dbo.HS_Scores or dbo.Future_Games. Your "unmatched" query (Step 3) should now be empty for this batch.

6. Repeat
Run the Python scraper again to process the next set of URLs in the batch or to start a new batch if the current one is complete.

(.venv) PS C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import> python maxpreps_scraper_db.py
2025-12-22 14:35:51,924 - INFO - === Starting Simplified DB-Driven MaxPreps Scraper ===
2025-12-22 14:35:51,956 - INFO - Connected to database successfully.
2025-12-22 14:35:51,957 - INFO - Resuming existing 'running' batch with ID: 13
2025-12-22 14:35:51,957 - INFO - Fetching up to 2000 teams for batch 13.
2025-12-22 14:35:51,965 - INFO - No more teams to process for this batch.
2025-12-22 14:35:51,965 - INFO - No more teams to process for this batch. Marking as complete.
2025-12-22 14:35:51,965 - INFO - Database connection closed.

SQL
UPDATE scraping_batches 
SET status = 'completed'
WHERE batch_id = 13;
[SUPERSEDED 2026-09-13 — this UPDATE is now automatic, the moment a batch
finds zero pending/failed teams left. This exact log excerpt is the
documented root cause of last year's automation silently dying: without
this manual step (or the automatic fix), the next run just keeps
"resuming" the same finished-but-not-marked batch forever, doing nothing,
with no visible error.]

==============================================================================================================

Late December Playoff Games Workflow
Overview
At season's end, 99% of games are complete but a small number of teams (primarily GA, TX, LA, CA) have playoff games extending into late December. This two-phase approach captures all completed games immediately while efficiently handling remaining playoffs after Christmas.

**2026-09-19 note**: this two-phase manual approach predates nightly
auto-finalize. The current automation's weekly full Sunday sweep plus
nightly incremental finalize should naturally re-catch playoff completions
as the season progresses (each Sunday re-scrapes every team, including
playoff results completed since the prior week) — but this hasn't been
explicitly verified yet. Worth running Step 3's verification query in
late November/December this year to confirm the continuous automation
actually covers this need before assuming the manual two-phase process
below is no longer necessary.

Phase 1: Initial Season Scrape (Run Immediately - ~December 10)
Step 1: Run Full Season Scrape
bashcd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\
python maxpreps_scraper_db.py
What happens:

Scrapes all teams' complete schedule pages
Completed games (with scores) → staged for HS_Scores
Playoff games (no scores yet) → staged for Future_Games
Returns a batch ID (note this for next step)

Step 2: Process the Batch
sql-- Use the batch ID returned by the Python script
EXEC dbo.FinalizeMaxPrepsData @BatchID = [your_batch_id];
What happens:

Parses raw game data
Completed games → inserted into HS_Scores
Future playoff games → inserted into Future_Games
Unrecognized teams → inserted into Unmatched_Games
[SUPERSEDED — dbo.Unmatched_Opponents, see note above]

Step 3: Verify Playoff Games Were Captured
sql-- View playoff games awaiting completion
SELECT FG.*, T.State
FROM Future_Games FG
JOIN HS_Team_Names T ON (FG.Home = T.Team_Name OR FG.Visitor = T.Team_Name)
WHERE T.State IN ('GA', 'TX', 'LA', 'CA')
ORDER BY FG.Date;
Expected results: Should show ~40-60 games scheduled for December 12-20
Step 4: Handle Unmatched Games (If Any)
sql-- Check for teams needing alias mapping
SELECT * FROM dbo.Unmatched_Games 
WHERE BatchID = [your_batch_id] AND Status = 'pending';
[SUPERSEDED — query dbo.Unmatched_Opponents WHERE BatchID = ... AND Resolved = 0]
If results found:

Identify missing team names
Add aliases to HS_Team_Name_Alias table (see main workflow)
[SUPERSEDED — add to URL_ProperName_Mapping / URL_ProperName_Mapping_Aliases]
Re-run: EXEC dbo.FinalizeMaxPrepsData @BatchID = [your_batch_id];

Step 5: Generate Rankings
At this point, 99% of games are in the system. You can proceed with:

Running CalculateRankings stored procedure
Generating JSON files
Publishing updated rankings
