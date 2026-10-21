# MaxPreps Scraping, Season Import & Publishing Workflow

Last updated: 2026-10-21. This is the working reference for the in-season
MaxPreps import (scrape -> finalize -> clean -> rate -> publish) and the
end-of-season wrap-up (playoffs, Michigan MHSAA, Canadian provinces, other
scrapers). Older notes are kept, unchanged, in the **Archive** at the bottom.

Related docs:
- Project doc `claude/2026_weekly_pipeline_status.md`: pipeline internals,
  fixes log, home-field notes.
- `EndofSeason_Workflow_md`: playoff two-phase scrape and the recognition
  campaign.
- `State_Alias_Standardization.md`: the alias consolidation loop.
- `College_Football_Workflow.md`: the college database and site.

---

## 0. How Claude should work on this (read first in a new chat)

**Where things run**
- The repo is on David's PC at
  `C:\Users\demck\OneDrive\Football_2024\static-football-rankings`.
- Claude reaches it through the linked-computer shell, where it is mounted at
  `$HOME/mnt/static-football-rankings`. Claude reads, edits and creates
  scripts and docs there directly.
- SQL Server (`MCKNIGHTS-PC\SQLEXPRESS01`, database `hs_football_database`)
  can't be reached from Claude's shells. David runs SQL in SSMS and Python in
  the repo's `.venv`, then pastes the output back.

**SQL Claude gives David**
- Give it in two parts: a read-only preview, then a commit script.
- Commit scripts use this exact pattern. The whole script must be run, never
  a highlighted part. Running only part of it caused "COMMIT has no BEGIN"
  on 2026-10-21.
  ```sql
  SET XACT_ABORT ON;
  DECLARE @Commit bit = 0, @expected int = <preview count>, @n int;
  BEGIN TRAN;
  <one UPDATE / DELETE>;
  SET @n = @@ROWCOUNT;            -- capture immediately
  IF @Commit = 1 AND @n = @expected BEGIN COMMIT; PRINT CONCAT('Committed ', @n); END
  ELSE BEGIN ROLLBACK; PRINT CONCAT('Rolled back: ', @n, ' vs ', @expected); END
  ```
- SQL Server gotchas:
  - No subquery inside `SUM()` (Msg 130); use a CTE plus `GROUP BY`.
  - Start a CTE with `;WITH`.
  - Escape apostrophes as `''`.
  - Never leave a `BEGIN TRAN` open in an SSMS tab. It blocks the scraper,
    the importer and the ratings.
- Keep using the existing tools:
  - `consolidation_workflow_latin.py` for name merges
  - `run_full_rankings_recalc.py` for ratings
  - `run_update_cycle.ps1` for publishing
- Before writing a new name rule, check it against the school's real history
  (renames, mergers, co-ops).
- Update this doc when a step changes, after backing it up to `backups/`.

**Naming rules (HS_Team_Names / HS_Scores)**
- Format is `City School (ST)`.
- City names are spelled out (`Saint Louis`); school names use abbreviations
  (`St.`, `Mt.`). Example: `Saint Louis St. Louis (MO)`.
- Keep real hyphens and apostrophes: `Scurry-Rosser`, `King's Academy`.
- A rename that later reverted is merged across all seasons under the current
  name. A permanent merger or split is date-scoped.
- Co-ops are written in `[brackets]`.

---

## 1. The weekly cycle (2026 season)

| When | What | Who |
|---|---|---|
| Sun 06:00 | `weekly_pipeline.py --loop` starts a new batch covering every mapped team (~15,900) | automatic |
| Sun–Wed | scraper runs back-to-back, 2,000 teams per run, until the batch is done (~3 days) | automatic |
| after scrape | `EXEC FinalizeMaxPrepsData @BatchID`, then the ratings recalc for that week, then sanity checks; status file shows `READY_TO_PUBLISH` | automatic (`AUTO_PUBLISH = False`) |
| Thu–Fri | weekly review (section 3), then publish (section 5) | David + Claude |
| Thu–Sat idle window | historical or college recalcs, which must not overlap a pipeline ratings run | David |

**Week numbers** come from SQL `DATEPART(week, date)`, with weeks starting on
Sunday. Friday 2026-10-16 = week 42; Sun 10/18 to Sat 10/24 = week 43. The
pipeline rates the week of the Saturday before the batch started. When
rerunning by hand, use the week of the Friday whose games you just imported.

---

## 2. Checking and restarting the pipeline

```powershell
# Is it running? Two rows with the SAME start time = one pipeline (.venv launcher + real python)
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
  Where-Object CommandLine -like '*weekly_pipeline*' |
  Select-Object ProcessId, CreationDate, CommandLine

# Status / logs (python_scripts\data_import)
Get-Content weekly_pipeline_status.txt
Get-Content weekly_pipeline_log.txt -Tail 30
python check_last_night_run.py      # latest batches, per-status counts, rows added in last 24h
```

- **It stops when** the PC reboots (often Windows Update), you sign out, or
  its window is closed. A failed week does not stop the loop.
- **Restart after a reboot.** Always use this working directory; starting it
  from the repo root fails silently:
  ```powershell
  Start-Process python -ArgumentList "weekly_pipeline.py --loop" `
    -WorkingDirectory "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"
  ```
  If it is past Sunday 06:00 and the week's batch hasn't finished, use
  `--now --loop` instead.
- **Ratings and checks only** for a week already scraped:
  `python weekly_pipeline.py --skip-scrape --now --week <W>`.

---

## 3. Weekly review checklist (before publishing)

Run these in order. Each one is a preview first.

**3.1 Batch health.** Show the latest batches and their status counts:

```sql
SELECT TOP 6 b.batch_id, b.status, b.created_date, b.total_teams,
       SUM(CASE WHEN s.status='completed' THEN 1 ELSE 0 END) AS done,
       SUM(CASE WHEN s.status='failed'    THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN s.status='pending'   THEN 1 ELSE 0 END) AS pending
FROM dbo.scraping_batches b
LEFT JOIN dbo.team_scraping_status s ON s.batch_id = b.batch_id
GROUP BY b.batch_id, b.status, b.created_date, b.total_teams
ORDER BY b.batch_id DESC;
```

A batch whose teams are all completed or failed but which still shows
`running` was never closed. Set it to `completed`; use `stopped` if it is
abandoned and incomplete.

**3.2 Failed teams.** List them with their URLs:

```sql
DECLARE @b int = (SELECT MAX(batch_id) FROM dbo.team_scraping_status);
SELECT s.team_id, t.Team_Name, s.attempts, m.URL
FROM dbo.team_scraping_status s
JOIN dbo.HS_Team_Names t ON t.ID = s.team_id
LEFT JOIN dbo.URL_ProperName_Mapping m ON m.Team_ID = s.team_id
WHERE s.batch_id = @b AND s.status = 'failed'
ORDER BY t.Team_Name;
```

- One failure with a normal URL is usually transient, so leave it.
- Repeat failures usually mean a bad URL; see section 4.

**3.3 Unmatched opponents.** These are in `dbo.Unmatched_Opponents`
(`Resolved = 0`), not the old `Unmatched_Games`:

```sql
SELECT OpponentNameRaw, OpponentMaxPrepsURL, COUNT(*) AS N
FROM dbo.Unmatched_Opponents
WHERE Resolved = 0
GROUP BY OpponentNameRaw, OpponentMaxPrepsURL
ORDER BY N DESC;
```

Opponents are matched by URL. To fix one:
- a new team gets a row in `URL_ProperName_Mapping`;
- an existing team whose URL changed gets a row in
  `URL_ProperName_Mapping_Aliases`.

Then rerun `EXEC dbo.FinalizeMaxPrepsData @BatchID = <B>;`. It is safe to
repeat.

**3.4 Name drift (second spellings created by the scraper).** These are
names like hyphen to space, `St.` to `Saint`, or a dropped apostrophe.

- Run `python consolidation_workflow_latin.py` in `python_scripts\data_import`.
- Action 1 for a state, or `US`, refreshes the GameCounts.
- Edit `<ST>_Alias_Rules.csv` in `excel_files\State_Aliases_ProperNames\`.
  Edit an existing row in place; never append a duplicate `Alias_Name`.
- Action 2 then consolidates `HS_Scores`, the alias table, `games`,
  `team_scraping_status` and the mapping.
- A rule that already exists still needs Action 2 rerun when new games
  arrive under the old spelling.

**3.5 Duplicate games after merges.** Same two teams and same score in a
season, even with home/away flipped:

```sql
;WITH g AS (
  SELECT s.ID, s.Date,
         CASE WHEN s.Home < s.Visitor THEN s.Home ELSE s.Visitor END AS T1,
         CASE WHEN s.Home < s.Visitor THEN s.Visitor ELSE s.Home END AS T2,
         CASE WHEN s.Home < s.Visitor THEN s.Home_Score ELSE s.Visitor_Score END AS S1,
         CASE WHEN s.Home < s.Visitor THEN s.Visitor_Score ELSE s.Home_Score END AS S2
  FROM dbo.HS_Scores s WHERE s.Season = 2026)
SELECT T1, T2, S1, S2, COUNT(*) AS N, MIN(Date) AS D1, MAX(Date) AS D2
FROM g GROUP BY T1, T2, S1, S2 HAVING COUNT(*) > 1 ORDER BY T1;
```

Archive the extras into the duplicates table rather than just deleting them.

**3.6 Suspicious scores.** Check for any 2026 score of 100 or more, and for
forfeits. MaxPreps marks forfeits "(FF)"; set them to 1-0 with
`Forfeit = 1`. Example: Gaston (OR) 950-0.

**3.7 Ratings sanity.**
- `HS_Rankings` should have no Season 2026 week later than the target week.
- One row per team.
- The top margin rating should be about 189 or less.
- The team count should be at or near the prior week's.

The pipeline checks these; recheck them after any manual rerun:

```sql
SELECT Week, COUNT(*) AS Teams FROM dbo.HS_Rankings
WHERE Season = 2026 GROUP BY Week ORDER BY Week DESC;
```

---

## 4. URL mapping maintenance (`dbo.URL_ProperName_Mapping`)

Columns: `Team_ID, ProperName, URL`. **The primary key is `URL`**, so one URL
can belong to only one team. The scraper reads
`URL_ProperName_Mapping JOIN HS_Team_Names` and writes games under
`ProperName`. A bad ProperName therefore creates a second team name every
week.

**Health check.** Find malformed URLs and teams with more than one row:

```sql
SELECT Team_ID, ProperName, URL FROM dbo.URL_ProperName_Mapping
WHERE URL NOT LIKE '%/football/schedule/'
   OR Team_ID IN (SELECT Team_ID FROM dbo.URL_ProperName_Mapping GROUP BY Team_ID HAVING COUNT(*) > 1)
ORDER BY Team_ID;
```

Patterns found 2026-10-21, and how each was handled:

1. **An extra `/football/football/` row next to a good `/football/schedule/`
   row.** Delete the `football/football` row. **Done:** 186 deleted.
2. **Only a `/football/football/` URL.** Rewrite it to `/football/schedule/`.
   - If the rewritten URL already belongs to another Team_ID (a primary-key
     violation), the school has two HS_Team_Names records.
   - In that case, pick the canonical name by game history and naming rules.
     Point the URL row at the canonical Team_ID and ProperName, delete the
     `football/football` row, and merge the names (3.4).
   - **Done:** 14 pairs (Scurry-Rosser, Shiner St. Paul, Skidmore-Tynan,
     Sour Lake Hardin-Jefferson, Stephenville, Fort Bend Kempner, Liberty-Eylau,
     Trophy Club Northwest Byron Nelson, Tyler King's Academy, Universal City
     Randolph, Victoria St. Joseph, Waco Methodist Children's Home, Waco
     Vanguard College Prep, Wellman-Union).
   - To find the remaining rows that rewrite without a conflict, run the
     "skip URLs already taken" rewrite from this chat with ROLLBACK first;
     it reports the count.
3. **Two `/football/schedule/` URLs with different mascot slugs** (~45 teams,
   mostly FL/MO/AL/KS). These are an old and a new MaxPreps slug; the old one
   redirects, so the team is scraped twice.
   - Keep the slug that loads without a redirect.
   - Co-ops and mergers need a decision: Clayton, Principia, University City,
     KC Southeast/Central, Dothan.
   - Casing duplicates: FAMU DRS, Lift for Life, Temple CenTex.
   - **Open.**

How to recognize pattern 2 in game counts: the "existing" name has only
current-season games while the other name has decades. That means the
scraper started writing the wrong spelling this season.

---

## 5. Ratings and publishing

```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts
python run_full_rankings_recalc.py --begin 2026 --end 2026 --week <W> --yes          # HS (league 1)
python run_full_rankings_recalc.py --begin 2026 --end 2026 --week <W> --yes --league 2 --no-snapshot   # college

cd ..\scripts
.\run_update_cycle.ps1          # publish HS site (add -NoPause for unattended)
```

- Rerunning a week overwrites only that Season+Week.
- Never use week 52 mid-season.
- Never run two recalcs at once, HS or college; they share staging tables.
- Never run ratings from SSMS `RatingsCalculator.sql` (v5_Fixed is buggy).
- Publish with `run_update_cycle.ps1`, **not** `Publish-Website.ps1`. The
  latter skips the latest-season JSON and Games of the Week.
- The college site is separate: `python python_scripts\college\generate_college_site.py`,
  then commit and push (see `College_Football_Workflow.md`).
- Each run takes about 1.5 hours.

---

## 6. End of season (late Nov – Jan)

**6.1 Playoffs (MaxPreps).** See `EndofSeason_Workflow_md` Phase 1 (mid-Dec)
and Phase 2 (post-Christmas targeted playoff batch for GA/TX/LA/CA).

- First confirm whether the weekly sweeps already caught the playoff results.
  Check `Future_Games` against `HS_Scores` for December dates.
- Final ratings use `--week 52` only once all playoffs are complete.
- Then delete any stale in-season weeks that would confuse the `MAX(Week)`
  logic, if wanted.

**6.2 Michigan (MHSAA)**, run at season end. See `MSHSS_cvs_creation.md`.

```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts
.\venv\Scripts\Activate
python MHSAA_WebScrapper.py     # Football, date range, Level = Varsity, click Search; 'w' first run
python MHSAA_WebScrapper.py     # again with Level = 8-Man, 'a' to append
```

Then run `Process_MHSAA_for_SQL.py` and `Generate_SQL_MHSAA_Import.py`, and
import. After that, run duplicate checks against the MaxPreps MI games (3.5).

**6.3 Canadian provinces.** See `Canadian_Providence_Import_Workflow.md`.

- Scrapers: `AB_WebScrapper.py`, `BC_WebScrapper.py`,
  `SK_Saskatoon_WebScrapper.py` (plus `SK_Regina_Diagnostic.py`).
- ScoreStream snowball: `Scorestream_Snowball_Scraper_v2.py`, with the
  reseed/batch routine in that doc.
- SQL generators: `Generate_SQL_AB_Import.py`, `_BC_`, `_MB_`, `_NB_`,
  `_SK_Regina`, `_SK_Saskatoon`.

**6.4 Other sources.**
- Previous-season MaxPreps re-import: `MaxPreps_Previous-Season_Re-Import.md`.
- Texas pre-2004 (LoneStar): `LoneStarFootball.net_Scraping_Workflow.md`.
- Newspaper OCR: `Google_AI_Newspaper_OCR_Workflow.md`.

**6.5 Recognition campaign.** See `EndofSeason_Workflow_md`, second half
(`export_recognition_report.py`, `generate_recognition_emails.py`).

**6.6 Next-season prep.**
- Close all batches.
- The season check in `maxpreps_scraper_db.py` switches automatically each July (`_current_season_code()`), so no edit is needed.
- Check that `URL_ProperName_Mapping` still covers every team.
- Run the 2025-vs-2026 name comparison (`compare_2025_2026_team_names.py`).

---

## 7. Open items (as of 2026-10-21)

1. Run TX Action 2 (`consolidation_workflow_latin.py`) for the 14 merged
   pairs, then the 3.5 duplicate check.
2. Four held pairs need a game-by-game look:
   - Tomball Christian HomeSchool vs Tomball Christian (two programs?)
   - Houston vs Tomball Concordia Lutheran (canonical: Tomball; dedupe)
   - Wichita Falls Wichita Christian vs Wichita Falls Christian Academy
   - Wylie Prep Academy vs Wylie Prep
3. Uvalde (69210): the schedule row uses the girls' slug. Point it at the
   boys' slug and delete the `football/football` row.
4. Tulsa Holland Hall (49598) is an Oklahoma school labelled TX.
5. Pattern 2 leftovers (rewrites with no conflict) and pattern 3 (~45 teams
   with two mascot slugs).
6. Old batches still showing `running`/stale (12, 26, 27, 28, 30, 39) need
   closing. Consider auto-close in the scraper.
7. Find the ProperName-generation bug: hyphen to space, `St` split
   mid-word (`St. roudsburg`), `Saint` expansion.
8. About 950 unmapped US teams (`coverage_gaps_2025_vs_2026.csv`).
9. Set `Forfeit = 1` from MaxPreps "(FF)" in finalize. Add a pipeline check
   for scores of 100 or more.
10. Decide how home-field advantage and forfeits are handled in `GetScores`
    (off-season, full recalc).

---

## 8. Kickoff prompt for a new chat

Paste this to start a new chat on this work:

> This chat is for the in-season MaxPreps import, cleanup, ratings and
> publishing of McKnight's American Football Rankings, plus the end-of-season
> imports (playoffs, Michigan MHSAA, Canadian provinces).
>
> **Access.** Use the link to my computer. Connect the folder
> `C:\Users\demck\OneDrive\Football_2024\static-football-rankings` (the repo)
> and, if needed, `SQL Server Management Studio`. You can read, edit and
> create files there with the device shell. You cannot reach SQL Server
> (`MCKNIGHTS-PC\SQLEXPRESS01`, `hs_football_database`): give me SQL or
> Python to run and I'll paste back the output.
>
> **Read first:**
> 1. `_AAA_Instructions/MaxPreps_Scraping_Workflow.md` (this runbook;
>    section 0 is how to work, section 7 is open items)
> 2. the project doc `claude/2026_weekly_pipeline_status.md`
> 3. `_AAA_Instructions/State_Alias_Standardization.md`
> 4. `_AAA_Instructions/EndofSeason_Workflow_md`, only near season end
>
> **Key scripts:**
> - `python_scripts/data_import/`: `weekly_pipeline.py`,
>   `maxpreps_scraper_db.py`, `check_last_night_run.py`,
>   `consolidation_workflow_latin.py`
> - `python_scripts/run_full_rankings_recalc.py`
> - `scripts/run_update_cycle.ps1`
>
> **Rules:**
> - Preview before commit.
> - Commit SQL uses the `SET XACT_ABORT ON / @Commit / @@ROWCOUNT` pattern
>   from section 0.
> - Check for an existing script before writing a new one.
> - Follow the naming rules in section 0.
> - Back up any file before editing it.
> - Update the runbook when a step changes.
>
> Current week: <W>. Today's task: <...>

---

# Archive (notes before 2026-10-21, kept unchanged)

Nightly Auto Run:
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
.\create_watcher_startup_shortcut.ps1

Morning check:
python check_last_night_run.py
Get-Content "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\maxpreps_wrapper_log.txt" -Tail 8


Manual start:
Summary Steps:
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
.\run_maxpreps_scraper.ps1

sql
EXEC dbo.FinalizeMaxPrepsData @BatchID = [Your_Batch_ID];


cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts
   python run_full_rankings_recalc.py --begin 2026 --end 2026 --week 41 --yes

Troubleshhoting:
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
One thing to check is that weekly_pipeline.py --loop is still running, since it’s what creates Sunday’s batch.

how do I check this,  what causes it to stop running, how do I restart?

Your pipeline log shows the looping copy was last started on Oct 4 at 17:25 as PID 133712. The status file says WAITING for Sunday Oct 11 at 06:00. That file only changes when the state changes, though, so it still reads WAITING after the process has died. The reliable check is whether Windows still has the process.

How to check

Run this in PowerShell:

powershell
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
  Where-Object CommandLine -like '*weekly_pipeline*' |
  Select-Object ProcessId, CreationDate, CommandLine

If it shows a row with PID 133712 (or any PID) and --loop, it’s running. If it returns nothing, it has stopped.

What makes it stop

A reboot. Windows Update restarts are the usual cause.
Signing out. It runs inside your logged-in session, not as a service.
Closing its console window, or Ctrl+C in it.

Some things don’t stop it. A failed week (bad checks, a SQL error) is caught, marked FAILED, and the loop carries on to the next Sunday. Sleep only pauses it: when the PC wakes, it notices Sunday has passed and starts right away.

After a reboot, the Startup-folder shortcut relaunches it with --loop. That waits for the next Sunday at 06:00, which is fine unless the reboot happens partway through a week’s batch (see below).

How to restart it

Run the check first so you don’t end up with two copies. Then:

powershell
Start-Process python -ArgumentList "weekly_pipeline.py --loop" `
  -WorkingDirectory "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"

For a restart that happens after Sunday at 06:00, while a batch is still in progress or hasn’t started, use --now --loop instead. It picks up the running batch right away instead of waiting a week.

For today: if the check shows nothing running, use the plain --loop command above, and it will start batch 38 on Sunday at 06:00 as planned.

(.venv) PS C:\Users\demck\OneDrive\Football_2024\static-football-rankings> Get-CimInstance Win32_Process -Filter "Name like 'python%'" |

  Where-Object CommandLine -like '*weekly_pipeline*' |
  Select-Object ProcessId, CreationDate, CommandLine

ProcessId CreationDate         CommandLine                                                                                                              
--------- ------------         -----------                                                                                                              
    37340 10/4/2026 5:25:02 PM "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\.venv\Scripts\python.exe" weekly_pipeline.py --now --loop
   133712 10/4/2026 5:25:02 PM "C:\Users\demck\AppData\Local\Programs\Python\Python311\python.exe" weekly_pipeline.py --now --loop                      

(.venv) PS C:\Users\demck\OneDrive\Football_2024\static-football-rankings>

It’s running. Those two rows are one pipeline, not two.

On Windows, .venv\Scripts\python.exe is a small launcher. It starts your real Python 3.11 as a child process and waits for it to finish. That’s why both rows have the same start time, and why only PID 133712 appears in the pipeline log: it’s the process actually running the code.

To confirm, run:

powershell
Get-CimInstance Win32_Process -Filter "ProcessId=133712" | Select-Object ProcessId, ParentProcessId

ParentProcessId should come back as 37340. If it does, leave both alone, because stopping either one stops the pipeline. Batch 38 will start on Sunday at 06:00 as planned.

When you check this in future, seeing two weekly_pipeline rows with the same start time is normal. You’d only have a real duplicate if there were two pairs with different start times.

(.venv) PS C:\Users\demck\OneDrive\Football_2024\static-football-rankings> Get-CimInstance Win32_Process -Filter "ProcessId=133712" | Select-Object ProcessId, ParentProcessId

ProcessId ParentProcessId
--------- ---------------
   133712           37340

(.venv) PS C:\Users\demck\OneDrive\Football_2024\static-football-rankings>

The parent is 37340, so it’s one pipeline: the .venv launcher (37340) running your real Python (133712). Leave both running. Batch 38 starts on Sunday at 06:00 with all 15,922 teams.

That leaves the Week 40 review, the Week 39 recalc, and the update cycle, which you can do whenever you’re ready.
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
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
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
.\run_maxpreps_scraper.ps1

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
