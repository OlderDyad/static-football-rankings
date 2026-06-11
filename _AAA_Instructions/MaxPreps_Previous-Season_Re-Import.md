# WORKFLOW — MaxPreps Previous-Season Re-Import
_Authoritative reference. Reconstructed from the full MO 2022 build + CO/FL investigations.
Supersedes the earlier SOP draft. Last updated 2026-06-05._

## Why this exists
The old Excel-macro imports are unreliable: MaxPreps changes its page format
yearly, and the macros (run over ~16,000 teams / ~80,000 games per season)
silently substituted wrong names or pulled prior-year schedules when a URL or
format shifted. Errors accumulated invisibly across 2004–2024. The visible
symptom is rating anomalies (small schools rating near national-champion level);
the real goal is re-establishing trust in the whole pre-scraper record.

**Unit of work:** one state-season (e.g. MO 2022, FL 2014). ~200–600 teams each.
**Campaign ordering:** year-by-year (all states in a year → internally consistent
for cross-state rating), OR state-by-state. Either works; pick and stay consistent.

---

## CORE ARTIFACTS (built and calibrated — in /outputs)
- `maxpreps_scraper_db_seasonal_v2.py` — season-aware scraper with driver session
  recovery + per-team retry/backoff (fixes the WinError 10061 crash cascade).
  Reads season slug from the batch row; `--season YY-YY` is a fallback flag.
- `FinalizeMaxPrepsData_seasonaware_v2.sql` — finalize proc (INSTALLED). Handles:
  year from `games_raw.season_year`; date cleaned at first CHAR(10) newline OR
  space; opponent join strips `/YY-YY/` and matches the mapping URL directly (no
  appended `schedule/`); **Source = the per-game MaxPreps URL** (carries `/YY-YY/`).
- `prev_season_reimport_PARAMETERIZED.sql` — set `@State` + `@SeasonSlug` at top;
  creates the scoped batch (or `@State=NULL` for all-USA). Generalized from MO.
- `mo2022_gapfinder_mappings.sql` — template for the create-schools + map-URLs step.
- `mo2022_reconcile.sql` — the proven reconcile (preview/commit, name-independent).
- `MeasureTeamConnectivity.sql` — diagnostic proc: per-hop network reach as % of
  season; flags TRUE ISLAND vs WELL CONNECTED (era-normalized).

---

## HARD-WON RULES (do not skip — each cost real debugging)
1. **HS_Scores.BatchID is NOT unique** — reused across years (BatchID 14 matched
   174k unrelated rows). NEVER identify/verify/undo an import by BatchID. Use Source.
2. **Access_ID** = repurposed column now holding pipeline GameID `yyyyMMdd-Home-Visitor`.
   Populated = pipeline row; NULL = old macro row. A clean old-vs-new discriminator.
3. **Source = per-game MaxPreps URL** (carries `/YY-YY/`) → each season's import is
   self-distinguishing from old `www.maxpreps.com` rows. Old layer has no season marker.
4. **Always finalize inside BEGIN TRAN**; verify in the SAME window; then COMMIT/ROLLBACK.
   A second window blocks/hangs on the open tran. Never leave a tran open.
5. **MaxPreps format drifts by year.** The PROBE (Step 4) is MANDATORY every
   state-season. 2022 dates came as `M/D\n time` (CHAR(10) newline) with NO year on
   the page — the scraper's `season_year` tag is what saves the year. Older years
   may differ; never assume.
6. **trg_LockTeamIdentity** permanently blocks UPDATE/DELETE on HS_Team_Names.Team_Name.
   New school names are permanent on insert — eyeball before creating.
7. `HS_Team_Names.ID` is IDENTITY (omit on insert). Only `Team_Name` is required;
   City/State/etc. nullable. `URL_ProperName_Mapping` = URL + ProperName (both NOT
   NULL) + Team_ID (nullable). The finalize proc matches opponents by URL→ProperName.
8. **Cross-border opponents** map to THEIR state's team (Pittsburg KS, not in-state).
   Don't mechanically treat a cross-state game as an error — border games are real.
9. **Reconcile must be NAME-INDEPENDENT** (date + order-insensitive score pair).
   Old/new layers spell teams differently (aliasing); name-based matching turns
   real games into false "phantoms". (MO: name-based said 383 phantoms; ~374 were
   just name mismatches.)
10. **SQL Server**: no subquery/aggregate inside GROUP BY or inside SUM(CASE WHEN
    EXISTS…). Compute the classification in a CTE/temp table first, then group.

---

## PROCEDURE (per state-season)

### Step 0 — Prereqs (once per DB, done)
`scraping_batches.season_slug`, `.season_year`, `games_raw.season_year` exist.
`FinalizeMaxPrepsData_seasonaware_v2` installed.

### Step 1 — Set scope + create the batch
Open `prev_season_reimport_PARAMETERIZED.sql`, set `@State` and `@SeasonSlug`
(e.g. `'FL'`, `'14-15'`). Run Sections A–E. It confirms no stray 'running' batch,
shows coverage gaps (teams with no URL mapping), scopes the existing suspect data,
and creates the scoped season-tagged batch. **Note the BatchID printed.**

### Step 2 — *** MANDATORY PROBE: scrape ONE team, verify format ***
Run `python maxpreps_scraper_db_seasonal_v2.py --season <slug>` on a probe subset
(or let it do one team, then stop). Then check the raw date format:
```sql
SELECT DISTINCT game_date, season_year FROM dbo.games_raw WHERE batch_id=<B> ORDER BY game_date;
```
- If `game_date` matches the 2022 shape the proc already handles (`M/D` + time on a
  separate line, or `M/D/YYYY`) → proceed.
- If it renders differently for this (older) year → STOP; adjust the proc's date-
  clean step before finalizing. Wrong-year rows in HS_Scores are painful to untangle.
Also confirm opponent-URL shape: `REPLACE(opponent_maxpreps_url,'/<slug>/','/')`
should equal a current-season mapping URL.

### Step 3 — Finish the scrape
Re-run the scraper until "No more teams". (It retries `failed` teams first, so
re-running resumes.) Verify:
```sql
SELECT status, COUNT(*) FROM dbo.team_scraping_status WHERE batch_id=<B> GROUP BY status;
```

### Step 4 — Finalize (in a transaction)
```sql
BEGIN TRAN;
EXEC dbo.FinalizeMaxPrepsData_seasonaware_v2 @BatchID=<B>;
SELECT COUNT(*) FROM dbo.HS_Scores WHERE Source LIKE '%/<slug>/%' AND Season=<YYYY>;
-- sample 25 rows: Season correct, dates in-season, Access_ID populated, count sane
-- COMMIT;  (or ROLLBACK)
```

### Step 5 — Gap-finder loop (resolve unmatched opponents → 0)
```sql
DECLARE @slug VARCHAR(10) = (SELECT season_slug FROM dbo.scraping_batches WHERE batch_id=<B>);
SELECT REPLACE(g.opponent_maxpreps_url,'/'+@slug+'/','/') AS Mapping_URL,
       COUNT(*) AS games, MIN(g.opponent_name_raw) AS sample
FROM dbo.games_raw g
LEFT JOIN dbo.URL_ProperName_Mapping m
  ON REPLACE(g.opponent_maxpreps_url,'/'+ISNULL(@slug,'~~none~~')+'/','/') = m.URL
WHERE g.batch_id=<B> AND m.ProperName IS NULL
GROUP BY REPLACE(g.opponent_maxpreps_url,'/'+@slug+'/','/') ORDER BY games DESC;
```
For each distinct URL: derive ProperName per the naming convention; check if it
exists in HS_Team_Names; map existing, create+map genuinely-new (cross-border →
other state). Insert URL_ProperName_Mapping rows (preview then commit), re-run
Step 4 finalize (dedup guard prevents doubling). Repeat until unmatched = 0.
(Template: `mo2022_gapfinder_mappings.sql`.)

**Naming convention:** `City School (ST)`; city spelled out / school abbreviated
(`Saint Louis St. Mary's (MO)`); collapse when city = school (`California (MO)`);
`[bracketed]` co-op members; preserve Latinized Spanish/French names.
**Anti-merge:** a wrongly-merged school is FAR worse than an isolated one
(Mater Dei CA ≠ Mater Dei IN). When unsure, leave separate. NOTE: same lat/long
means same CITY (geocoder resolves on city token), NOT necessarily same school.

### Step 6 — Sanity check
Compare the new count vs neighboring years for that state — should land in the
same band (MO 2022: new 1,531 vs old 1,564 vs neighbors 1,398–1,591). A wild miss
= incomplete scrape or mapping gap.

### Step 7 — Reconcile (DELETE old duplicate layer) — *** PROVEN on MO 2022 ***
Template: `mo2022_reconcile.sql`. **Take a `.bak` to E:\SQLBackups\ first** (this
is the destructive step). Name-independent (date + score), not name-based.
- **Preview** (Section 1) buckets old rows: `DELETE` (has new twin), `KEEP` (team
  not in new scrape — uncovered/defunct, protect), `REVIEW` (team in new, no twin).
- **Commit** (Section 2) deletes ONLY the verified-twin bucket; leaves REVIEW in
  place (conservative — un-twinned rows don't double-count). Verify @@ROWCOUNT
  matches the preview, then COMMIT.
- MO 2022 result: 1,452 DELETE / 25 KEEP / 87 REVIEW.

### Step 8 — Recalculate ratings
Only AFTER the reconcile (else the calc rates doubled games). Run the surrounding-
season window (target year ±2, since `Power_Rankings_Prelim` seeds from ±1,±2).
Both directions per standing protocol. ~1.5 hrs/season.

### Step 9 — Close the batch
```sql
UPDATE dbo.scraping_batches SET status='completed' WHERE batch_id=<B>;
```

---

## SLUG REFERENCE (confirm per year with the probe — do not assume)
Pattern: year Y → `YY-(YY+1)`.  2024→24-25, 2022→22-23, 2021→21-22, 2014→14-15,
2004→04-05.

---

## DIAGNOSTIC: is a flagged team's island real or a data artifact?
(From the rating-anomaly investigation. Run BEFORE assuming a re-import is needed.)
1. `MeasureTeamConnectivity '<team>', <season>` — % of season reached. <2% = island.
   Era-normalized, so it correctly keeps legitimate sparse greats (Everett 1920 =
   10.66%) WELL CONNECTED while flagging modern small-school clusters (~1.9%).
2. Check the team's own schedule (clean? duplicates? split-name opponents?).
3. Check opponents for alias-split (same school under 2+ names) / missing games —
   that fragmentation manufactures FALSE islands and inflates ratings.
4. A data-artifact island RESOLVES after re-import + alias consolidation (North
   Andrew: 103 → off all-time top 5000, whole cluster dropped in lockstep). A
   genuine isolated great (Everett 1920) does not and should NOT be touched.
   **Never apply a blanket isolation discount — it demotes the legitimate greats.**