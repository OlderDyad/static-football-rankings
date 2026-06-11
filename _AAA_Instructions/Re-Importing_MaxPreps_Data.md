# WORKFLOW — MaxPreps Previous-Season Re-Import
_Authoritative reference. Built from FL 2014 full end-to-end run (2026-06-08).
Supersedes all earlier versions of this document._

---

## Why this exists
The old Excel-macro imports are unreliable: MaxPreps changes its page format
yearly, and the macros silently substituted wrong names or pulled prior-year
schedules when a URL or format shifted. Errors accumulated invisibly across
2004–2024. The visible symptom is rating anomalies (small schools rating near
national-champion level); the real goal is re-establishing trust in the whole
pre-scraper record.

**Unit of work:** one state-season (e.g. FL 2014, MO 2022). ~500–600 teams per
state for large states. A national all-state run covers ~16,000 teams.
**Campaign ordering:** year-by-year (all states in a year → internally consistent
for cross-state rating), OR state-by-state. Either works; pick and stay consistent.

---

## CORE ARTIFACTS

- `maxpreps_scraper_db_v2.py` — THE past-season scraper. Based directly on the
  proven `maxpreps_scraper_db.py` (current season). Only change: season slug
  inserted into URL (`/football/14-15/schedule/` vs `/football/schedule/`).
  Includes full driver resilience (dead session rebuild, per-team retry/backoff).
  Prompts for state and season interactively, or accepts `--state`/`--season` flags.

- `FinalizeMaxPrepsData` (stored proc, installed) — season-aware finalize.
  Handles date cleaning (M/D + time on separate line), correct year from
  `games_raw.season_year`, opponent URL join stripping season slug.
  Source = per-game MaxPreps URL carrying `/YY-YY/` segment.

- `fl2014_reconcile.sql` — proven reconcile template. Name+date+score matching
  (see Hard-Won Rules below on why name matching is required for large states).

---

## ONE-TIME DATABASE FIXES (completed 2026-06-08, do not repeat)

These were root-cause fixes that benefit all future imports:

**Fix 1 — HS_Team_Names.State populated from Team_Name suffix**
11,319 rows had NULL State. The `(ST)` suffix in Team_Name is universally
enforced, so State was derived directly:
```sql
UPDATE dbo.HS_Team_Names
SET State = SUBSTRING(RIGHT(Team_Name, 3), 1, 2)
WHERE State IS NULL AND RIGHT(Team_Name, 4) LIKE '([A-Z][A-Z])';
```

**Fix 2 — URL_ProperName_Mapping Team_IDs corrected**
8,759 rows had phantom Team_IDs (pointing to IDs that don't exist in
HS_Team_Names). 7,048 were fixed by matching ProperName → Team_Name:
```sql
UPDATE m SET m.Team_ID = t.ID
FROM dbo.URL_ProperName_Mapping m
JOIN dbo.HS_Team_Names t ON t.Team_Name = m.ProperName
LEFT JOIN dbo.HS_Team_Names t2 ON m.Team_ID = t2.ID
WHERE t2.ID IS NULL;
```
1,711 remaining orphans need investigation separately.

**Result:** FL coverage in URL_ProperName_Mapping jumped from 146 → 577 teams.
National coverage is now properly linked for ~7,048 additional teams.

---

## HARD-WON RULES (do not skip — each cost real debugging)

1. **HS_Scores.BatchID is NOT unique** — reused across years. NEVER identify
   or undo an import by BatchID. Use Source LIKE '%/YY-YY/%' AND Season=YYYY.

2. **Access_ID** = pipeline GameID `yyyyMMdd-Home-Visitor`. Populated = pipeline
   row; NULL = old macro row. Clean discriminator between layers.

3. **Source = per-game MaxPreps URL** carrying `/YY-YY/` → each season's import
   is self-distinguishing from old `www.maxpreps.com` macro rows.

4. **Always finalize inside BEGIN TRAN**; verify in the SAME window; then
   COMMIT/ROLLBACK. A second window blocks on the open transaction.

5. **MaxPreps format drifts by year.** The date probe (Step 3) is MANDATORY
   every state-season. 2014 dates came as `M/D time` (space separator) with NO
   year on the page — season_year tag from scraper saves the year.

6. **trg_LockTeamIdentity** permanently blocks UPDATE/DELETE on Team_Name.
   New school names are permanent on insert — verify carefully before creating.

7. **Reconcile for large states REQUIRES name matching.** Date+score alone
   generates massive false positives for FL/TX/CA (hundreds of games per Friday,
   common scores like 0-35 or 7-14 collide constantly). At least one team name
   must match between old and new layers. This differs from MO 2022 where
   date+score alone worked due to lower game volume.

8. **HS_Team_MaxPreps is corrupted** — Team_ID 9221 (and others) were
   incorrectly assigned hundreds of URLs. Do NOT use HS_Team_MaxPreps for
   state-filtered batch creation. Use URL_ProperName_Mapping instead (now fixed).
   HS_Team_MaxPreps is still used for ALL-state national runs where the corruption
   averages out across 16,000 teams.

9. **Batch creation source by run type:**
   - State-specific run → `URL_ProperName_Mapping JOIN HS_Team_Names WHERE State=?`
   - National ALL run → `HS_Team_MaxPreps` (same as current-season scraper)

10. **Scraper finds teams via URL_ProperName_Mapping** regardless of how the
    batch was seeded. Teams in team_scraping_status with no URL_ProperName_Mapping
    entry sit as 'pending' forever and are inert — not an error.

11. **UnmappedURL_Log** (16k+ rows) contains opponent URLs that were unmatched
    during 2025 finalization. This is a future URL discovery source for expanding
    URL_ProperName_Mapping coverage. Not yet integrated into the workflow.

12. **Backup before reconcile** — take a .bak to E:\SQLBackups\ before the
    destructive delete step. The automated backup script covers this but verify.

---

## PROCEDURE (per state-season)

### Step 1 — Run the scraper

```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
.\.venv\Scripts\Activate
python maxpreps_scraper_db_v2.py --season 14-15 --state FL
```

Or interactively (prompts for season and state):
```powershell
python maxpreps_scraper_db_v2.py
```

The script:
- Checks for an existing 'running' batch and resumes it if found
- Otherwise creates a new batch from URL_ProperName_Mapping filtered by state
- Builds past-season URLs: `.../football/14-15/schedule/`
- Tags every games_raw row with season_year for correct finalization
- On completion prints the BatchID and next-step instructions

**Note the BatchID printed** — used in all subsequent steps.

If Chrome crashes (WinError 10061): kill orphaned processes first:
```powershell
taskkill /F /IM chromedriver.exe /T
taskkill /F /IM chrome.exe /T
```
Then re-run — the script resumes the running batch automatically.

### Step 2 — Verify scrape completion

```sql
SELECT status, COUNT(*) AS team_count
FROM dbo.team_scraping_status
WHERE batch_id = <B>
GROUP BY status;
```

If any `failed` teams: re-run the scraper (retries failed teams first).
`pending` teams with no URL mapping are inert — ignore them.

```sql
SELECT COUNT(*) AS total_raw_games
FROM dbo.games_raw WHERE batch_id = <B>;
```

Expect ~10-12 games per completed team for a typical state.

### Step 3 — MANDATORY PROBE: verify date format

```sql
SELECT DISTINCT game_date, season_year
FROM dbo.games_raw WHERE batch_id = <B>
ORDER BY game_date;
```

- Dates should look like `8/29 7:00pm` or `8/29 TBA` — proc strips at first space ✅
- season_year should match the target year (e.g. 2014) ✅
- If dates look different (e.g. `Aug 29, 2014`) → STOP, adjust the finalize
  proc's date-clean step before proceeding

Also verify opponent URLs carry the season slug:
```sql
SELECT DISTINCT opponent_maxpreps_url
FROM dbo.games_raw WHERE batch_id = <B>;
```
URLs should contain `/14-15/` (or whatever slug). ✅

### Step 4 — Finalize (in a transaction)

```sql
BEGIN TRAN;

EXEC dbo.FinalizeMaxPrepsData @BatchID = <B>;

SELECT COUNT(*) AS new_rows_imported
FROM dbo.HS_Scores
WHERE Source LIKE '%/<slug>/%' AND Season = <YYYY>;

-- Spot check 25 rows
SELECT TOP 25 Date, Season, Home, Visitor, Home_Score, Visitor_Score,
              Access_ID, Source
FROM dbo.HS_Scores
WHERE Source LIKE '%/<slug>/%' AND Season = <YYYY>
ORDER BY NEWID();

-- COMMIT;  (or ROLLBACK if anything looks wrong)
```

Verify: Season correct, dates in-season, Access_ID populated, scores sane.

### Step 5 — Gap-finder loop (resolve unmatched opponents → 0)

```sql
DECLARE @slug VARCHAR(10) = '<YY-YY>';

SELECT
    REPLACE(g.opponent_maxpreps_url, '/' + @slug + '/', '/') AS Mapping_URL,
    COUNT(*) AS games_lost,
    MIN(g.opponent_name_raw) AS sample_name
FROM dbo.games_raw g
LEFT JOIN dbo.URL_ProperName_Mapping m
    ON REPLACE(g.opponent_maxpreps_url, '/' + @slug + '/', '/') = m.URL
WHERE g.batch_id = <B>
  AND m.ProperName IS NULL
  AND g.opponent_maxpreps_url != ''
  AND g.opponent_maxpreps_url NOT LIKE '%pseudo_schools%'
GROUP BY REPLACE(g.opponent_maxpreps_url, '/' + @slug + '/', '/')
ORDER BY games_lost DESC;
```

For each unmatched URL:
1. Check if team already exists in HS_Team_Names (use exact name and near-match queries)
2. If exists: INSERT into URL_ProperName_Mapping with correct Team_ID
3. If genuinely new: INSERT into HS_Team_Names first, then INSERT mapping
4. Re-run FinalizeMaxPrepsData (dedup guard prevents doubling)
5. Repeat until gap-finder returns 0 rows

**Naming convention:** `City School (ST)`; city spelled out; collapse when city=school
(`Hilliard (FL)`); preserve apostrophes. Cross-border opponents map to THEIR state.
**Anti-merge:** wrongly-merged schools are far worse than isolated ones. When unsure,
leave separate.

**Skip:** `about_pseudo_schools.aspx` — MaxPreps placeholder for homeschool/co-op
teams with no real page. Cannot be mapped, accept the loss.

### Step 6 — Re-finalize after gap resolution

```sql
BEGIN TRAN;
EXEC dbo.FinalizeMaxPrepsData @BatchID = <B>;
SELECT COUNT(*) AS total_rows
FROM dbo.HS_Scores WHERE Source LIKE '%/<slug>/%' AND Season = <YYYY>;
-- COMMIT;
```

### Step 7 — Sanity check

```sql
SELECT Season, COUNT(*) AS games
FROM dbo.HS_Scores
WHERE Source LIKE '%maxpreps%'
  AND Season BETWEEN <YYYY-2> AND <YYYY+2>
  AND (Home LIKE '%(ST)%' OR Visitor LIKE '%(ST)%')
GROUP BY Season ORDER BY Season;
```

New season should land in the same band as neighbors. If 2x higher than
neighbors: old macro layer still present (double-counted) → proceed to reconcile.
If far lower: incomplete scrape or mapping gap.

### Step 8 — Take a backup

```sql
BACKUP DATABASE hs_football_database
TO DISK = 'E:\SQLBackups\hs_football_database_pre_<ST><YYYY>_reconcile.bak'
WITH FORMAT, COMPRESSION;
```

### Step 9 — Reconcile (delete old macro layer duplicates)

**SECTION 1 — Preview only (run first):**

```sql
WITH OldLayer AS (
    SELECT s.ID, s.Date, s.Home, s.Visitor, s.Home_Score, s.Visitor_Score,
        IIF(s.Home_Score <= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMin,
        IIF(s.Home_Score >= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMax
    FROM dbo.HS_Scores s
    WHERE s.Source = 'www.maxpreps.com' AND s.Access_ID IS NULL
      AND s.Season = <YYYY>
      AND (s.Home LIKE '%(ST)%' OR s.Visitor LIKE '%(ST)%')
),
NewLayer AS (
    SELECT s.Date, s.Home, s.Visitor,
        IIF(s.Home_Score <= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMin,
        IIF(s.Home_Score >= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMax
    FROM dbo.HS_Scores s
    WHERE s.Source LIKE '%/<slug>/%' AND s.Season = <YYYY>
),
ScrapedTeams AS (
    SELECT DISTINCT m.ProperName
    FROM dbo.URL_ProperName_Mapping m
    JOIN dbo.team_scraping_status ts ON m.Team_ID = ts.team_id
    WHERE ts.batch_id = <B> AND ts.status = 'completed'
),
Bucketed AS (
    SELECT o.ID,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM NewLayer n
                WHERE n.Date = o.Date AND n.ScoreMin = o.ScoreMin AND n.ScoreMax = o.ScoreMax
                  AND (n.Home = o.Home OR n.Home = o.Visitor
                    OR n.Visitor = o.Home OR n.Visitor = o.Visitor)
            ) THEN 'DELETE'
            WHEN NOT EXISTS (
                SELECT 1 FROM ScrapedTeams st
                WHERE st.ProperName = o.Home OR st.ProperName = o.Visitor
            ) THEN 'KEEP'
            ELSE 'REVIEW'
        END AS Bucket
    FROM OldLayer o
)
SELECT Bucket, COUNT(*) AS row_count
FROM Bucketed GROUP BY Bucket ORDER BY Bucket;
```

**Expected buckets:**
- DELETE: the verified twins — must be ≤ new_rows_imported count
- KEEP: uncovered/defunct teams — protect these, they have no new layer counterpart
- REVIEW: team scraped but no twin found (name mismatch) — left in place safely

**SECTION 2 — Commit delete (run in a SEPARATE window after verifying Section 1):**

```sql
BEGIN TRAN;

WITH OldLayer AS (
    SELECT s.ID, s.Date, s.Home, s.Visitor,
        IIF(s.Home_Score <= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMin,
        IIF(s.Home_Score >= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMax
    FROM dbo.HS_Scores s
    WHERE s.Source = 'www.maxpreps.com' AND s.Access_ID IS NULL
      AND s.Season = <YYYY>
      AND (s.Home LIKE '%(ST)%' OR s.Visitor LIKE '%(ST)%')
),
NewLayer AS (
    SELECT s.Date, s.Home, s.Visitor,
        IIF(s.Home_Score <= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMin,
        IIF(s.Home_Score >= s.Visitor_Score, s.Home_Score, s.Visitor_Score) AS ScoreMax
    FROM dbo.HS_Scores s
    WHERE s.Source LIKE '%/<slug>/%' AND s.Season = <YYYY>
)
DELETE FROM dbo.HS_Scores
WHERE ID IN (
    SELECT o.ID FROM OldLayer o
    WHERE EXISTS (
        SELECT 1 FROM NewLayer n
        WHERE n.Date = o.Date AND n.ScoreMin = o.ScoreMin AND n.ScoreMax = o.ScoreMax
          AND (n.Home = o.Home OR n.Home = o.Visitor
            OR n.Visitor = o.Home OR n.Visitor = o.Visitor)
    )
);

SELECT @@ROWCOUNT AS rows_deleted;

-- Verify season lands back in the normal band
SELECT Season, COUNT(*) AS total_games
FROM dbo.HS_Scores
WHERE Season BETWEEN <YYYY-1> AND <YYYY+1>
  AND (Home LIKE '%(ST)%' OR Visitor LIKE '%(ST)%')
GROUP BY Season ORDER BY Season;

-- COMMIT;  (or ROLLBACK if @@ROWCOUNT doesn't match Section 1 DELETE count)
```

### Step 10 — Recalculate ratings

Only AFTER reconcile (else calc rates doubled games). Run surrounding-season
window (target year ±2). Both directions per standing protocol. ~1.5 hrs/season.

### Step 11 — Close the batch

```sql
UPDATE dbo.scraping_batches SET status='completed' WHERE batch_id=<B>;
```

---

## SLUG REFERENCE
Pattern: year Y → `YY-(YY+1)`.
2024→24-25, 2022→22-23, 2021→21-22, 2014→14-15, 2004→04-05.
Always verify with the date probe — do not assume.

---

## FL 2014 REFERENCE RESULTS (use as sanity check baseline)

- Teams scraped: 554 completed / 1 failed (Lutz Steinbrenner, rate-limited)
- Raw games collected: 6,231
- New rows imported after gap resolution: 3,056
- Unmatched opponents: 17 (resolved to 0)
- Season band check: 2013=3,070 | 2014=3,248 | 2015=3,080 ✅
- Reconcile: 2,882 DELETE / 132 KEEP / 60 REVIEW
- Final 2014 FL game count: 3,248

---

## DIAGNOSTIC: is a flagged team's high rating real or a data artifact?

Run BEFORE assuming a re-import is needed.

1. `EXEC dbo.MeasureTeamConnectivity '<team>', <season>` — % of season reached.
   <2% at hop 5 = island. Era-normalized.

2. Check the hop expansion shape. Hop-2 should fan out to 70-90 new teams
   (opponents' full schedules). If hop-2 returns only 5-10: either the opponents
   themselves are alias-split (data artifact) OR they genuinely only play within
   a small private school circuit (real isolation).

3. Check the team's schedule — duplicate rows? Unusual opponents?

4. Check opponents' game counts for the season. 1-3 games = alias-split suspect.

5. A data-artifact island RESOLVES after re-import + alias consolidation.
   A genuine isolated league does NOT and should NOT be "fixed" — the correct
   fix is the ratings calculation (ISNULL seed handling), not data manipulation.

**Clearwater Academy International (FL) 2014 — confirmed genuine isolation:**
   Small private school league, correctly mapped, hop-5 = 1.47%. The rating
   anomaly requires a ratings calc fix (ISNULL seed), not further data work.

---

## URL MAPPING COVERAGE NOTES

As of 2026-06-08:
- URL_ProperName_Mapping: 16,435 rows, 16,236 distinct teams — full national coverage
- FL specifically: 577 filterable teams (up from 146 before the one-time fixes)
- 1,711 orphaned Team_IDs nationally still need investigation
- UnmappedURL_Log has 14,008 unmatched opponent URLs from 2025 scrape —
  future source for expanding coverage, not yet integrated
- HS_Team_MaxPreps: corrupted for state-filtered use; fine for national ALL runs