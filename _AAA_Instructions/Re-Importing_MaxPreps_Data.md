# Project Notes — MaxPreps Re-Import & Rating-Anomaly Investigation
_Synthesis for future chats. Status as of 2026-06-04._

## 1. What we set out to do
Re-import historical MaxPreps seasons because the old Excel-macro imports are
unreliable: MaxPreps changed page formats yearly, and across ~16,000 teams /
~80,000 games per year the macros silently substituted wrong names / prior-year
schedules when a URL or format shifted. Pilot: **MO 2022**. Then CO 2021, FL 2014,
and eventually the full 2004–2024 campaign (year-by-year, all states per year).

## 2. What we actually built (committed, working)
- `maxpreps_scraper_db_seasonal_v2.py` — season-aware scraper. Reads season slug
  per-batch from `scraping_batches.season_slug`; builds `.../football/<slug>/schedule/`
  URLs; **driver session recovery** + per-team retry (fixes the WinError 10061
  crash cascade that killed v1); throttle backoff on 5 consecutive failures.
- `FinalizeMaxPrepsData_seasonaware_v2.sql` — calibrated proc:
  - year from `games_raw.season_year` (fallback `YEAR(GETDATE())`)
  - date cleaned at first **CHAR(10)** newline OR space (MaxPreps puts date+time
    on separate lines: `8/26\n7:00pm`); old code's space-split produced NULL and
    silently dropped every row
  - opponent join strips `/<slug>/` and matches the mapping URL directly (NO
    appended `schedule/` — the scraped opponent URL already ends in `/schedule/`)
  - **Source = the per-game MaxPreps URL** (carries `/22-23/`), making each
    season's import self-distinguishing from old `www.maxpreps.com` rows
- `mo2022_gapfinder_mappings.sql` — created 6 new schools + mapped 38 opponent URLs.
- `SOP_MaxPreps_Season_Reimport.md` — the reusable workflow.

**MO 2022 result:** 1,531 new rows imported, gap-filled (0 unmatched opponents),
count sanity-checked against neighboring years (old layer was 1,564; neighbors
1,398–1,591). Committed.

## 3. Hard-won lessons (these cost real debugging — keep them)
1. **`HS_Scores.BatchID` is NOT unique** — reused across years of loads. `BatchID=14`
   already matched 174k unrelated historical rows. Never identify/verify/undo an
   import by BatchID. Identify by Source.
2. **`Access_ID`** is a repurposed (ex-MS-Access) column now holding the
   pipeline GameID `yyyyMMdd-Home-Visitor`. Populated = pipeline row; NULL = old
   macro/Access-era row. Useful as an old-vs-new discriminator.
3. **Always finalize inside `BEGIN TRAN`**, verify in the SAME window, then
   COMMIT/ROLLBACK. Open transactions cause silent multi-minute lock hangs;
   a second window querying the same rows blocks on them.
4. **MaxPreps format drifts by year** — date separator and opponent-URL shape
   that held for 2022 may differ for 2014/2008. The one-team PROBE (read raw
   `game_date`, check opponent-URL shape) is mandatory every state-season.
5. **SQL Server**: can't put a subquery/aggregate inside `GROUP BY` or inside
   `SUM(CASE WHEN EXISTS…)`. Compute classifications in a CTE/temp table first,
   then group. (Hit this repeatedly.)
6. **`trg_LockTeamIdentity`** makes `HS_Team_Names.Team_Name` permanent (no
   UPDATE/DELETE). `ID` is IDENTITY; `UQ_HS_Team_Names_Team_Name` blocks dup names.
7. **Reconcile must be name-INDEPENDENT.** Old vs new can't match on team names —
   names are the inconsistent thing (aliasing). Match on date + score (order-
   insensitive). Name-based matching turned ~370 real games into false "phantoms".

## 4. The reconcile (designed, NOT yet executed)
Old layer (`Source='www.maxpreps.com'`, `Access_ID` NULL) and new layer
(`Source LIKE '%/22-23/%'`) currently COEXIST in HS_Scores — every MO 2022 game
is present twice. Reconcile = delete old where a verified new twin exists.

Bucketing of the 1,564 old MO 2022 rows (name-based, so imperfect):
- **1,149 MATCH** (exact date+teams+score twin in new) → safe to delete
- **32 OLD_ONLY, team not in new scrape** → KEEP (uncovered/defunct teams)
- **383 OLD_ONLY, team in new** → mostly **name-mismatched real games** (e.g.
  `University City` vs `Saint Louis University City`), NOT phantoms. Re-bucket
  name-independently (date+score) before deleting. True phantom count is small.

Prereqs before executing: `.bak` to `E:\SQLBackups\`; separate preview/commit
scripts; spot-check borderline rows against live MaxPreps pages (ground truth).
**This still needs to be done for MO 2022 and is the first validation of Step 8
in the SOP.**

## 5. The rating-anomaly investigation — the bigger discovery
**Symptom:** small 8-man teams rating near national-champ level, persistent for
MONTHS across many full all-seasons recalcs. Seeds: MO 2022 (Rosendale North
Andrew), CO 2021 (Cheyenne Wells), FL 2014. `FindRatingOutliers_MovingAvg`
showed a whole CLUSTER of northwest-MO 8-man schools spiking together in 2022
(North Andrew, Archie, Albany, Orrick, Drexel, Concordia St. Paul Lutheran,
Sweet Springs-Malta Bend).

**What we ruled OUT:**
- Not the re-import duplication — the anomaly predates the import by months;
  the calc ran on old data only.
- Not North Andrew's own data — its old-layer schedule is clean (13 games, one
  per week, real opponents, sane scores). Verified.
- Not a cross-state mismerge (no Mater-Dei-CA-vs-IN type bad link found).

**Leading hypothesis (David's, strong):** the rating calc seeds each team from
**surrounding-season ratings**, but teams with no surrounding-season rating get a
**NULL seed instead of 0**. NULL = unconstrained = no gravity pulling the team
toward the population; an undefeated, big-margin, geographically-isolated small
school then floats as high as its margins push it. The whole NW-MO 8-man cluster
lacks surrounding-season coverage simultaneously (pre-scraper gaps + cross-year
name drift), so they all float and mutually inflate through the iterative passes.

**Why this explains everything the data-theories couldn't:**
- The persistence (re-running doesn't help — the seed is structurally absent, not
  just uncalculated).
- The cluster co-occurrence (shared missing-seed condition).
- The **Throckmorton 2005 contrast**: it DROPPED when re-run with surrounding-
  season seeds — because that time it GOT a seed. The persistent cases are the
  ones still seeded NULL.

**Corroborating evidence:** In the opponent-network query, `Combined_Rating`
came back NULL for the whole MO 2022 cluster (component margin ratings present).
And the existing **Chronic Volatile Programs** tracker already classifies exactly
this as `'Geographic isolation - network island'` (Unique_States_Played = 1) and
`'Systematic data gaps'` (low games/season) — the same mechanism, independently.

**The fix (David's call):** replace NULL seed with **0**. Rationale: the 2048-loop
convergence pulls 0 to a stable value regardless, and the next run's seeds inherit
that stability (self-correcting over runs). It's a **one-line logic fix**
(`ISNULL(prior_season_rating, 0)`) in the seed step of the calc
(`CalculateRankings_v4_Optimized` or wherever the pre-seed is read) — NOT a data
fix, and far faster than re-importing for the deadline.

## 6. Two distinct phenomena (don't conflate)
- **MO 2022 cluster** → missing-seed (NULL→0) logic issue, AND data duplication
  pending reconcile. Logic fix likely resolves the rating; reconcile cleans data.
- **Isolated historical/island teams** (Throckmorton-style; the non-MO outliers
  De Smet SD 2003, Fort Myers Canterbury FL 2011, Cheyenne Wells CO 2021 with
  normal game counts) → genuine network-island math, addressed by surrounding-
  season seeding (which the NULL→0 fix supports).

## 7. Deadline context
MaxPreps is writing articles referencing the site late June–July (150th
anniversary of HS football; site featured as most comprehensive). Priority:
fix GLARING rating embarrassments (8-man teams as all-time-greatest); do NOT be
mid-major-rebuild. Editorial stance: cross-era comparison is fine (1920 Everett
vs Mater Dei) as long as inputs are clean; remove the INDEFENSIBLE outliers, not
the merely-high-but-earned ones.

## 8. Path forward — ordered
1. **[fast, deadline-critical]** Apply `ISNULL(seed,0)` in the calc's pre-seed
   step. Re-run. Check: does the NW-MO cluster drop off BOTH the outlier list and
   the volatility tracker? (Two-sided confirmation.) — *find the seed code first.*
2. **Reconcile MO 2022** — name-independent (date+score) delete of old duplicate
   layer; `.bak` first; preview/commit; spot-check vs MaxPreps. Validates SOP Step 8.
3. **Re-import CO 2021 and FL 2014** via the SOP (different slugs `21-22`, `14-15`;
   run the mandatory probe each — format may differ for 2014).
4. **[deferred, post-deadline]** National naming schema (city spelled out / school
   abbreviated, e.g. `Saint Louis St. Mary's (MO)`; collapse city=school;
   `[bracketed]` co-ops; Latinized names preserved for cultural Spanish/French).
   Then the alias-helper (modeled on `master_scores_importer.py`'s 3-suggestion +
   opponent-overlap engine, with a Gemini date-aware canonical hook) and the full
   2004–2024 campaign. Anti-merge rule: a wrongly-merged school is far worse than
   an isolated one (Mater Dei CA ≠ Mater Dei IN); opponent-overlap count is the
   guardrail.
5. **[validation tool]** Build the faux-league simulator: run synthetic clean
   data through the iterative calc to test whether isolated undefeated clusters
   EVER produce these outliers without input error — settles "input error vs math
   artifact" definitively.

## 9. Open items / to confirm next session
- Tracker results (running now) — do the NULL-seed teams show as island/volatile?
- Surrounding-season seed check: do North Andrew / Archie / Albany have
  `HS_Rankings` rows in 2021 & 2023? (Confirms the missing-seed structure.)
- Locate the seed-application code in the calc to place `ISNULL(...,0)` correctly
  (must be the pre-seed, not an active-iteration spot where 0 would distort).
- `Combined_Rating` is NULL for the MO 2022 cluster though margin rating exists —
  understand why (calc didn't populate it? separate step?).