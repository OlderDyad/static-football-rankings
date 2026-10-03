# State Onboarding & Data-Quality Cleanup — Workflow Guide

Covers the pipeline stage *after* games are already in `HS_Scores` (see
`QUICK_GUIDE.md` for OCR extraction → import). This is the toolset for
finding and fixing data-quality problems: duplicate/ghost games, alias
mess, wrong 6/8-man level, tier mismatches, and legacy date corruption —
plus the checklist for bringing a new state fully up to the same standard
as Oklahoma.

Built and hardened across the OK cleanup and the LA pilot (Sept 2026).
Everything in the "Conventions & Gotchas" section below was learned the
hard way — read it before running anything destructive.

---

## Core table schemas (as confirmed by hand — not exhaustive)

No formal schema doc exists for this database; these are the columns
actually observed/used across this project's sessions. If a query needs a
column not listed here, run `INFORMATION_SCHEMA.COLUMNS` for that table
rather than guessing:
```sql
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'TableNameHere'
ORDER BY ORDINAL_POSITION;
```

**`HS_Scores`** (the core game-results table):
`ID` (uniqueidentifier, PK), `Date`, `Season` (int), `Home`, `Visitor`
(both `"City Qualifier (ST)"` format), `Neutral` (bit), `Location`,
`Location2`, `Line`, `Future_Game`, `Source` (URL or filename string —
provenance), `Date_Added` (datetime — when the row was inserted),
`OT`, `Forfeit` (bit), `Home_Score`, `Visitor_Score`, `Margin`,
`BatchID` (FK-ish to `scraping_batches`, nullable), `Access_ID`,
`Has_Detail_Page`, `Detail_Page_URL`.

**`HS_Scores_Change_Log`** (audit trail — always write here before/with any
`HS_Scores` mutation): `LogID` (PK), `ScoresID` (FK to `HS_Scores.ID`),
`InvestigationID` (FK to `HS_Mapping_Investigations`, nullable),
`FieldChanged`, `OldValue` (**VARCHAR, quite short — confirmed truncating
around ~90-100 chars in practice; always defensively `LEFT()`-truncate or
widen the column, never assume it'll fit**), `NewValue`, `ChangedAt`,
`ChangedBy`, `Reason`, `Script`.

**`HS_Mapping_Investigations`**: `InvestigationID` (PK, int),
`AnchorTeam`, `State` (**parenthesized format, `'(OK)'` not `'OK'`**),
`Season`, `ConflictType` (GhostTeam / DuplicateImport /
AliasReclassification / GameCountAnomaly / TierMismatch / LevelMismatch),
`Priority`, `Status` (**`VARCHAR(20)` — keep status strings short, see
Conventions above**), `Notes`, `GhostTeamCandidate`, `ProposedCorrection`.

**`HS_Mapping_Investigation_Games`**: `InvestigationID` (FK),
`ScoresID` (FK to `HS_Scores.ID`) — many-to-many link table, one
investigation can have multiple linked games.

**`HS_Team_Names`**: `ID` (uniqueidentifier, PK — referenced by FK from
`team_scraping_status.team_id`, so not every row is guaranteed to exist
if a team was never registered), `Team_Name`, `State`, `LogoURL`,
`PrimaryColor`, `Website` (the latter three frequently blank for
older/smaller programs — informational gap, not an error).

**`HS_Team_Level_History`**: `TeamName`, `PlayerLevel` (8 or 11),
`Season_Begin`, `Season_End` (9999 = open-ended/current),
`Is_Verified` (bit — 0 means an unresolved default row, not confirmed
data).

**`HS_Team_Conference_History`**: `TeamName`, `Faux_Conference` (e.g.
`'OK - Statewide'`, `'OK - 8-Man'`), `Season_Begin`, `Season_End`,
`Is_Verified`.

**`scraping_batches`**: `batch_id` (PK), `batch_name`, `created_date`,
`total_teams`, `status`, `season_slug`, `season_year`.

**`games_raw`**: `raw_id`, `primary_team_name`, `opponent_name_raw`,
`result_text`, `game_date` (varchar, not a real date type), `opponent_maxpreps_url`,
`batch_id`, `season_year`. No timestamp column.

**`team_scraping_status`**: has `team_id` with an FK constraint to
`HS_Team_Names.ID` — this FK is why `rescrape_2019_ambiguous.py` had to
add a pre-filter (see script notes) rather than assuming every matched
team has a registry row.

**`HS_Team_Name_Alias`** (no ID/PK column — resolves on the
`(Alias_Name, Newspaper_Region)` combination as a compound key in
practice): `Alias_Name`, `Standardized_Name`, `Newspaper_Region`,
`Newspaper_City`, `Newspaper_State` (all varchar). See the "alias-rule
state mistagging" bug class below. `Newspaper_Region = '*Global*'` is a
special convention used almost exclusively for exact-name-equals-proper-name
rows (the alias already matches the canonical name) — not a real
newspaper, and typically not where source-specific mistagging bugs live;
exclude it when sweeping for the state-mistagging pattern.

**`HS_Mapping_Investigations`** (full column list, confirmed
2026-09-10): `InvestigationID` (int, PK), `AnchorTeam`, `State`
(**parenthesized, `'(LA)'` not `'LA'` — see Conventions above**),
`Season`, `DateIdentified` (datetime), `Status` (**`VARCHAR(20)`, see
Conventions**), `GhostTeamCandidate`, `ProbableCorrectOpponent`,
`VerificationSource`, `Notes`, `FixSQL`, `FixedDate` (datetime),
`MinDaysApart`, `ScoreMatchFlag` (bit), `Priority`,
`AnchorScoreOnlyMatch` (bit), `ConflictType`, `ProposedCorrection`.

**`HS_Mapping_Investigation_Games`**: pure link table, two columns —
`InvestigationID` (int), `ScoresID` (uniqueidentifier, joins to
`HS_Scores.ID`).

**`HS_Team_Tier_Classification`** (written by `classify_team_tiers.py`,
never touched directly): `TeamName` (VARCHAR(150), PK), `Tier`
(`'Weak'` or `'Strong'`), `Basis` (`'NameSeed'` or `'Propagated'`),
`Confidence` (float, Propagated rows only — fraction of games against
seed-tier opponents), `GamesConsidered` (int, Propagated rows only),
`ComputedAt` (datetime). Absence from this table = implicitly `Normal`
tier at query time; the table intentionally only stores Weak/Strong rows.

**Decoy / adjacent tables — know these exist, but they are NOT what they
sound like:**
- `HS_Scores_Archived_Conflicts` — unrelated to
  `RemoveDuplicateGamesParameterized`'s archiving (that logs to
  `HS_Scores_Change_Log`, see Conventions above). Contains manual
  conflict-resolution entries for a different state's data (South Dakota,
  as of the one query run against it 2026-09-10). Don't assume this is
  where dedup runs archive to.
- `ValidationResults_Duplicates` — surfaced via an
  `INFORMATION_SCHEMA.TABLES` search for `%Duplicate%`; purpose
  unconfirmed, never queried. Flag as genuinely unknown (not a decoy) —
  worth investigating the next time it's relevant rather than assuming
  what it does.

**SQL gotcha**: `ROWCOUNT` is a reserved keyword — bracket any column
alias using it (`AS [RowCount]`) or rename, or you'll get a syntax error.

---

## Conventions & Gotchas (read this first)

- **`HS_Mapping_Investigations.Status` is `VARCHAR(20)`.** Always use short
  status strings: `Fixed`, `Verified-FalsePos`, `Spot-Checked`,
  `Verified-Resolved`. A string over 20 chars causes a SQL truncation
  error, and because `bulk_set_status()` / `close_investigation()` run as
  a single UPDATE, it fails **atomically** — silently leaving rows at
  `Status='New'` with no visible error in some call paths. This once let
  ~500 investigations sit unclosed for weeks despite being reported as
  resolved. **After any bulk status change, verify directly against the
  DB** (`SELECT Status, COUNT(*) ... GROUP BY Status`) rather than trusting
  a summary count.
- **`HS_Mapping_Investigations.State` is stored parenthesized**: `'(OK)'`,
  `'(LA)'` — not the raw 2-letter code. Matches `mapping_conflict_audit.py`'s
  `normalize_state()`. Ad hoc SQL using `State = 'OK'` silently matches zero
  rows.
- **Team names in `HS_Scores`/`HS_Team_Names` are `"City Qualifier (ST)"`**,
  e.g. `Tulsa Bishop Kelley (OK)`, `Lake Charles Washington-Marion (LA)`.
- **Before any bulk destructive SQL** (dedup runs, mass UPDATEs, alias
  consolidation's action 2), take a fresh table snapshot:
  ```sql
  SELECT * INTO HS_Scores_Backup_YYYYMMDD FROM HS_Scores;
  ```
  This isn't optional. A 4-day-old backup is the only reason a bad
  `RemoveDuplicateGamesParameterized` run in Sept 2026 (see below) didn't
  become permanent, unrecoverable data loss.
- **`RemoveDuplicateGamesParameterized`**: always pass `@State` explicitly
  unless you deliberately want a full-database sweep. As of the v3 fix
  (2026-09-09) it wraps each archive-then-delete step in a transaction with
  a row-count check, so a failed archive (e.g. `OldValue` truncation) now
  aborts loudly instead of silently deleting unarchived rows. The old
  (pre-fix) version could destroy data with zero audit trail if the archive
  INSERT failed — this happened once, deleted 1,421 rows unlogged, and took
  a full recovery session to fix via backup diffing. If you ever see this
  procedure error out mid-run again, **stop and check `HS_Scores_Change_Log`
  for matching entries before assuming anything was safely archived.**
  It archives INTO `HS_Scores_Change_Log` itself (not a separate table):
  `FieldChanged='ROW_DELETED'`, `OldValue` = `LEFT(CONCAT('Season=...,
  Date=..., Home=..., Visitor=...'), 90)` (truncated to 90 chars, the v3
  fix), `Reason` = `'RemoveDuplicateGamesParameterized run: State=<X>,
  SeasonStart=<Y>, SeasonEnd=<Z> -- exact duplicate of surviving row
  <KeptID>'`, `Script` = `'RemoveDuplicateGamesParameterized (regular)'`
  or `'(swapped)'`. To see what a specific run archived:
  ```sql
  SELECT ScoresID, OldValue, Reason
  FROM HS_Scores_Change_Log
  WHERE FieldChanged = 'ROW_DELETED'
    AND Reason LIKE 'RemoveDuplicateGamesParameterized run: State=<X>%'
  ORDER BY ScoresID;
  ```
  No timestamp filter on that query — it returns every historical run
  matching that state, not just the most recent one; add a date bound if
  you need to isolate a single run. Also worth knowing: `@State` matching
  is `Home LIKE '%' + @State + '%' OR Visitor LIKE '%' + @State + '%'` —
  a substring match against the full team-name string (which carries the
  state as a suffix like `(LA)`), not a lookup against a clean state
  column. Works fine in practice, but it's substring-based, not exact.
- **`RemoveDuplicateGamesParameterized`'s duplicate detection does not
  include `Date`** in its matching logic — only `Season, Home, Visitor,
  Home_Score, Visitor_Score`. It's very likely correct (two rows for the
  same real game reported with slightly different dates by two sources)
  but is not literally guaranteed. Two known source patterns explain most
  date-mismatched "duplicates":
  - **2019 MaxPreps era**: a row with the generic `[www.maxpreps.com]`
    source URL and a date landing on day 1-3 of the month is almost always
    the **corrupted** copy (the legacy date-truncation bug — see below); a
    row with a specific `.../football/19-20/schedule/` URL is the correct
    one.
  - **Newspaper/yearbook era (pre-2000)**: a `classmates.com` /
    `cebyrdathletics.com` (yearbook-derived) row colliding with a dated
    newspaper `.csv`/`newspapers.com/image/...` row is usually the
    yearbook row that's approximate — but not always (a few cases the
    yearbook/newspapers.com row was *more* specific than the survivor).
    **Don't bulk-delete this pattern — review case by case or leave both
    rows in place.**
- **`RemoveDuplicateGamesParameterized` also marks/unmarks a `Forfeit`
  flag** (`@MarkForfeits BIT = 1` param, defaults on) — confirmed via
  `OBJECT_DEFINITION`, this step is explicitly commented "(unchanged)" in
  the procedure itself, i.e. it predates the v3 dedup fix entirely, not
  new behavior. Heuristic: `Home_Score + Visitor_Score = 1` (the standard
  nominal 1-0 forfeit-score convention) → `Forfeit=1`; any row currently
  `Forfeit=1` that does NOT match that sum → `Forfeit=0`. Safe and
  non-overlapping with real games (a genuine final score can essentially
  never sum to exactly 1 — minimum for a scoring team is 6). Running it
  against OK on 2026-09-12 (`@State='OK'`, full `First to Last` season
  range — the first such full sweep against OK's entire history) reported
  "482 games unmarked as forfeits" — a one-time backlog correction of
  stale flags from some earlier process, not a new problem. Verified via
  sample: current `Forfeit=0` OK rows all show plausible real scores, none
  near a 1-0 pattern. This flag is the ONLY thing this step touches —
  never scores or team names.
  Separately, worth registering: running this procedure state-wide finds
  and fixes *all* of that state's outstanding duplicates, not just ones
  created by whatever triggered the run (e.g. running it after the South
  Coffeyville merge above found 474 total OK duplicates, not just the 2
  the merge itself created) — expected once you think about it, but easy
  to be surprised by the count if you don't.
- **Alias consolidation: never invent a new compound name.** When resolving
  a blank `Standardized_Name` in `<STATE>_Alias_Rules.csv`, if a plausible
  target is already an established standalone entry elsewhere in the file,
  map to that exact existing string. Don't create a new variant (e.g. map
  `Lake Charles Marion (LA)` to the existing `Lake Charles
  Washington-Marion (LA)`, not to a freshly-invented `"...Calcasieu Parish
  (LA)"`). Every new compound name is a future unmerged-alias problem.

---

## Tool: `mapping_conflict_audit.py`

Central CLI (in `data_import`). Six `ConflictType`s: `GhostTeam`,
`DuplicateImport`, `AliasReclassification`, `GameCountAnomaly`,
`TierMismatch`, `LevelMismatch`. Backed by
`HS_Mapping_Investigations` / `HS_Mapping_Investigation_Games`.

Key commands:

```powershell
python mapping_conflict_audit.py detect --state XX              # scan for new GhostTeam conflicts, register investigations
python mapping_conflict_audit.py detect-duplicates --state XX   # same-page OCR duplicate imports
python mapping_conflict_audit.py dashboard --state XX           # counts by ConflictType/Era/Priority/Status
python mapping_conflict_audit.py repeat-offenders --state XX    # teams flagged across the most distinct seasons (strongest signal)
python mapping_conflict_audit.py queue --anchor "Team Name" --state XX   # list open investigations for one team
python mapping_conflict_audit.py queue --type TierMismatch --priority High --state XX
python mapping_conflict_audit.py fix --id <ScoresID GUID> --field Home --value "New Name (ST)" --investigation <N> --reason "..."
python mapping_conflict_audit.py delete --id <ScoresID GUID> --investigation <N> --reason "..."   # confirmed duplicate row
python mapping_conflict_audit.py close --investigation <N> --status Fixed --reason "..."
python mapping_conflict_audit.py dismiss --investigation <N> --reason "..."                        # false positive, no HS_Scores change
python mapping_conflict_audit.py defer --state XX --conflict-type TierMismatch --status <short> --priority-like Medium --reason "..."  # bulk status change
python mapping_conflict_audit.py detect-tier-mismatch --state XX
python mapping_conflict_audit.py detect-level-mismatch --state XX
python mapping_conflict_audit.py verify-level-mismatches --state XX --dry-run
python mapping_conflict_audit.py reclassify --state XX --suspect "Name A" --confused-with "Name B"
python mapping_conflict_audit.py apply-reclassify --state XX --suspect "Name A"
```

**Triage approach for a fresh `detect` run**: start with `repeat-offenders`
(teams flagged across the most seasons — strongest signal for a real
recurring mapping problem), not the raw queue in ID order. Within a queue,
`queue --anchor` groups investigations by priority label; the tool's own
priority text is generally trustworthy:
- `High - true same-day conflict`: physically impossible (same team, two
  games, same date) — always a real problem, review individually.
- `Low - possible multi-level scheduling, spot-check only`: usually a
  small program playing two different opponents a day or two apart with
  plausible distinct scores — legitimate scheduling, not a data error.
  Validated as a consistent pattern across multiple repeat-offenders in
  both OK and LA; safe to sample a few anchors to confirm before treating
  as low-priority-safe-to-defer at scale for a given state.

---

## Tool: `consolidation_workflow*.py` family (alias consolidation)

**There are FIVE similarly-named scripts in `data_import/`** — confirmed
2026-09-12 via `ls`/`diff`, worth documenting once so this doesn't need
re-discovering: `consolidation_workflow.py` (the one used earlier this
session for LA's 639-rule run; its own header says "v3"), `_v3.py` (a
*different* file despite the plain one's header claiming v3 — genuinely
confusing, not yet diffed against `_latin`), `_w_geo.py` (not yet
examined), `run_consolidation.py` (not yet examined), and
**`consolidation_workflow_latin.py`** — despite the name suggesting it's
only for Latin-alphabet/accented special characters, `diff` against the
plain script shows it's the newest (April 2026) and genuinely the safer
general-purpose version: encoding fallback (`utf-8-sig` then `latin1`) on
CSV read, **refreshes `GameCount` on already-existing rows** (the plain
script only ever adds new rows, never updates stale counts on old ones),
and — most importantly — a real post-run safety check the plain script
completely lacks: it queries `HS_Scores` afterward for the literal string
`'nan'` in `Home`/`Visitor` and errors loudly if found (catches a known
pandas failure mode where a blank/NaN cell gets silently written as the
text "nan" instead of empty). **Recommendation: use
`consolidation_workflow_latin.py` going forward**, not the plain one,
regardless of whether the state involves special characters. `_v3.py` and
`_w_geo.py` still need diffing before ruling out that one of *them* is
actually the most current — flagged, not yet done.

Interactive: prompts for state code, then action.

- **Action 1** — generate/update `<STATE>_Alias_Rules.csv` in
  `excel_files\State_Aliases_ProperNames\` (columns: `Alias_Name,
  GameCount, Standardized_Name`) via `sp_CreateStateCleanupList`.
- **Action 2** — upload filled rows to `ConsolidationRules_Staging` and run
  `sp_ConsolidateNames_FromStaging @StateCode` (renames `Home`/`Visitor` in
  `HS_Scores` for every row matching a filled alias). Confirmed
  2026-09-12: this reprocesses the **entire** CSV's completed rows every
  time, not just newly-added ones — same as LA's 639-rule run. No hidden
  dependency on Action 1 having run first in the same session.

**Editing an existing row vs. appending a new one — don't append a
duplicate `Alias_Name`.** If a name already exists in the CSV (even with
a blank or wrong `Standardized_Name`), **edit that row's third field in
place**. Appending a second row with the same `Alias_Name` but a
different `Standardized_Name` leaves two conflicting entries for the same
key in the file, risking an ambiguous or last-wins outcome once uploaded
to staging. Only append for names that are genuinely absent from the file
— check with `grep` first (case-insensitively; see the South Coffeyville
case study below for why case matters).

**`sp_ConsolidateNames_FromStaging` V8 (2026-09-12): now has a real audit
trail.** Through V7, every step of this procedure only used `PRINT`
(console-only, nothing persisted) — the bulk `HS_Scores` update reported
just a combined rowcount across *all* rules, with no way to trace which
rule caused which change, no reason, no timestamp. V8 adds:
- An optional `@Reason NVARCHAR(500) = NULL` parameter — backward
  compatible, old callers passing only `@StateCode` still work.
- A new `dbo.HS_Consolidation_Log` table (auto-created on first run,
  same `IF OBJECT_ID(...) IS NULL` pattern used elsewhere in this
  project), logging one row **per rule that actually changed ≥1 row** —
  `StateCode, OldName, NewName, RowsAffectedHome, RowsAffectedVisitor,
  Reason, LoggedAt`. Uses an `OUTPUT` clause on the existing bulk
  `UPDATE` rather than looping per-rule, so the original bulk-update
  performance is preserved.
- Rules matching zero `HS_Scores` rows produce no log entry (expected —
  e.g. a name that only needed correcting in `HS_Team_Names`/alias
  tables but had no games under it).
- The V7 nan/empty/NULL `NewName` guard (hard abort before any table is
  touched) is unchanged.
- **`consolidation_workflow_latin.py` was updated to match**: Action 2
  now prompts `Reason for this consolidation run (optional, press Enter
  to skip)` and passes it through. Blank input → `NULL`, same as before
  this parameter existed.

**Case study: South Coffeyville / Oklahoma Union cluster (OK,
2026-09-12).** Illustrates several of the rules above at once. Four
variant names needed consolidating: `Coffeyville South (OK)` (256 games,
was self-standardized to itself — wrong), `South Coffeyville-Copan (OK)`
(10 games, blank), `Lenapah Oklahoma Union (OK)` (46 games, blank), and
`Oklahoma union cougars (OK)` (0 games — not in `HS_Scores` at all, only
needed for its `HS_Team_Names` master record, hence "can't just drop the
name" — it still needs a resolution row even with nothing to move).
Initial instinct was to invent a new name, `South Coffeyville (OK)` — but
the CSV **already had** `South Coffeyville Oklahoma Union (OK)`
self-standardized with 350 games, the largest count in the cluster. Per
the established naming-consistency rule, that already-established name
should always win over inventing a new compound name. Verified via a
real-world web search (MaxPreps/SI/ScoreStream all confirm "South
Coffeyville High School," Lions, is the current active program) and via
the PA-tagged-VA case elsewhere in this doc (same "check whether the
correctly-tagged version pulls from the same source" verification
pattern). Applied via `consolidation_workflow_latin.py`, reason logged:
confirmed via `HS_Consolidation_Log` that all three ratable rows moved
*exactly* their pre-existing `GameCount` (256, 46, 10 — precise match),
and zero rows remained under any old name afterward. Created exactly 2
new duplicate pairs (both vs. Pawhuska (OK), 2019 season) once the merge
collapsed two identities into one — expected, cleaned up via
`RemoveDuplicateGamesParameterized` immediately after (see next section).

Related: `import_new_teams.py` adds missing `HS_Team_Names` registry rows
(reads `excel_files\New_HS_Team_Names.csv`) — a different problem
(registry gaps), not consolidation.

---

## Legacy date-truncation bug (2019 MaxPreps era)

A subset of 2019-season MaxPreps scrapes got truncated dates (landing on
day 1-3 of the month) with a generic `[www.maxpreps.com]` source URL,
instead of the real date with a team-specific schedule URL.

1. **Diagnose** (any state/season, fully generalized):
   ```powershell
   python diagnose_date_truncation.py --state XX
   ```
   Flags seasons showing a "Friday-share collapse" in day-1/2/3 rows vs.
   the rest of that season (`FRIDAY_DROP_FLAG`) — this is the necessary
   trigger; "elevated day-1/2/3 share" alone is corroborating only, never
   sufficient (validated: using it alone produced false positives on
   seasons that were *more* Friday-heavy in the early days, the opposite of
   corruption).
2. **Fix candidates**:
   ```powershell
   python maxpreps_2019_date_truncation_fix.py --state XX --output xx_2019_dates.csv
   ```
   Classifies each suspect row's confidence (High-UniqueFriday auto-applies;
   Ambiguous-NeedsLiveCheck needs the next step).
3. **Rescrape ambiguous rows**:
   ```powershell
   python rescrape_2019_ambiguous.py --input xx_2019_dates.csv
   ```
   Note: `team_scraping_status.team_id` has an FK to `HS_Team_Names.ID`;
   the script pre-filters and warns about any matched team with no
   `HS_Team_Names` row rather than crashing the whole batch.
4. **Reconcile**:
   ```powershell
   python reconcile_2019_ambiguous.py --input xx_2019_dates.csv
   ```
   Matches rescraped data back against the ambiguous rows, classifies
   Matched-ScoreConfirmed / NoMatch / Matched-DateNotInRange.

All four scripts are confirmed state-generic — no code changes needed to
run against a new state.

---

## Bug class: alias-rule state mistagging (region-scoped)

A single bad row in `HS_Team_Name_Alias` can map a bare, ambiguous team
name (a town name shared by two+ states) to the wrong state's team — and
because alias resolution runs on every import touching that source, the
error silently reproduces across every future import from that
newspaper/region until the **rule itself** is corrected, not just the
already-affected `HS_Scores` rows.

**Signature**: the same specific newspaper/region resolves the identical
bare `Alias_Name` to two different `Standardized_Name` values across
different rows, where at least one doesn't match the newspaper's actual
state.

**Confirmed example (2026-09-10, RESOLVED)**: `HS_Team_Name_Alias` had
`"Lake Arthur" → Lake Arthur (NM)` for two rows keyed to The Shreveport
Journal and The Times (both `Newspaper_City='Shreveport',
Newspaper_State='LA'`), while every other newspaper correctly resolved
the same bare name to `Lake Arthur (LA)` (a real, current LHSAA 2A
school, confirmed against LHSAA's 2025-26 official alignment). This
silently mistagged 44 `HS_Scores` rows across three separate import
sessions (2026-05-05, 2026-05-10, 2026-08-18) before it was caught.

**`HS_Team_Name_Alias` schema** (confirmed via `INFORMATION_SCHEMA.COLUMNS`):
`Alias_Name`, `Standardized_Name`, `Newspaper_Region`, `Newspaper_City`,
`Newspaper_State` (all varchar). No ID/PK column — resolution runs on the
`(Alias_Name, Newspaper_Region)` combination as a compound key in
practice.

**Fixing this is two separate steps, not one**:
1. Correct the already-imported `HS_Scores` rows (archived UPDATE, see
   the Trafton-style single-row `fix` pattern or a batch archived
   transaction for a larger set like this one). *Lake Arthur: done —
   44 rows corrected via archived transaction, followed by
   `RemoveDuplicateGamesParameterized @State='LA'` which caught 15
   resulting duplicate collisions.*
2. **Correct the alias rule itself** in `HS_Team_Name_Alias` — otherwise
   the next import from that same newspaper/region reproduces the
   identical error. Don't consider this bug class closed until both are
   done. *Lake Arthur: done —*
   ```sql
   UPDATE HS_Team_Name_Alias
   SET Standardized_Name = 'Lake Arthur (LA)'
   WHERE Alias_Name = 'Lake Arthur'
     AND Newspaper_Region IN ('The Shreveport Journal', 'The Times')
     AND Newspaper_City = 'Shreveport' AND Newspaper_State = 'LA';
   -- @@ROWCOUNT = 2, confirmed committed
   ```

**Detection** — same-alias-different-resolution self-join, scoped to
avoid false-flagging intentionally global fallback rows:
```sql
SELECT a1.Alias_Name, a1.Standardized_Name AS Resolution_A, a2.Standardized_Name AS Resolution_B,
       a1.Newspaper_Region, a1.Newspaper_City, a1.Newspaper_State
FROM HS_Team_Name_Alias a1
JOIN HS_Team_Name_Alias a2
  ON a1.Alias_Name = a2.Alias_Name
  AND a1.Newspaper_Region = a2.Newspaper_Region
  AND a1.Standardized_Name <> a2.Standardized_Name
  AND a1.Standardized_Name < a2.Standardized_Name
WHERE a1.Newspaper_Region <> '*Global*'
ORDER BY a1.Newspaper_Region, a1.Alias_Name;
```
Run 2026-09-10 as a full-table sweep after the Lake Arthur fix: **0 rows
returned**, confirming no sibling bugs of the same shape existed at that
time. Worth re-running this periodically (especially after onboarding a
new border state) — this bug class is easy to reproduce silently and easy
to miss without an explicit check like this. There are several town names
shared across state borders in the OK/TX/AR/LA/MS region this project
covers.

**Related but distinct case (2026-09-10): source-URL-derived state
mistagging, not an alias-table bug.** While pulling Week=52 ratings for
every `%Deaf%` team nationwide (see the tier-classification section
below), found `Pennsylvania School for the Deaf (VA)` — 6 games,
1928-1948, all vs. `Virginia School for the Deaf & Blind (VA)`, all from
`http://fourseasonsfootball.com/va.html`. Initially assumed this was a
genuinely distinct program (its schedule never overlapped the real
`Pennsylvania School for the Deaf (PA)`'s data), so it was left unmerged
pending verification. That verification actually reversed the conclusion:
the correctly-tagged `(PA)` team has two 1981-82 games from that *same*
source URL (`fourseasonsfootball.com/va.html`) against West Virginia
School for the Deaf, correctly tagged `(PA)`. So the source aggregates
mid-Atlantic Deaf-school football across decades under one page, and a
subset of its rows got state-tagged off the URL/filename (`va.html`)
rather than off the actual team name — same underlying failure mode as
the `HS_Team_Name_Alias` region-scoped bug above (state derived from the
wrong signal), but this one lives directly in `HS_Scores.Home`/`Visitor`
text, no alias table involved, so the self-join detection query above
would never have caught it. Confirmed and merged:
```sql
UPDATE HS_Scores SET Home = 'Pennsylvania School for the Deaf (PA)' WHERE Home = 'Pennsylvania School for the Deaf (VA)';
UPDATE HS_Scores SET Visitor = 'Pennsylvania School for the Deaf (PA)' WHERE Visitor = 'Pennsylvania School for the Deaf (VA)';
```
**Lesson**: when a team name embeds a real place name (a state's own
school "for the Deaf/Blind", a city name matching another state, etc.)
and its state tag looks suspicious, checking whether the *correctly*
tagged version of that same name also pulls from the same source is a
fast, cheap way to catch this pattern — a single source can correctly tag
most of its rows and still mistag a subset, so "no overlap with the
correctly-tagged team's data" is NOT sufficient evidence of a genuinely
distinct entity on its own, as it first appeared to be here.

Also fixed in the same pass, 3 unambiguous same-state misspellings (no
research needed, safe direct merges): `lowa School for the Deaf (IA)` →
`Iowa School for the Deaf (IA)` (OCR l/I), `Wisconcin School for the Deaf
(WI)` / `Wisconsin Schoof for the Deaf (WI)` → `Wisconsin School for the
Deaf (WI)` (typos), `Pennsylviana School for the Deaf (PA)` →
`Pennsylvania School for the Deaf (PA)` (misspelling).

---

## Detector blind spot: `detect`'s reliable-source filter misses well-documented historic programs

`mapping_conflict_audit.py detect`'s conflict-finder (`fetch_reliable_games()`)
only ever looks at rows whose `Source` is a `newspapers.com` clipping, a
filename with an embedded `YYYY_MM_DD`, or `Season >= 2003`:
```python
reliable_mask = (
    df['Source'].str.contains('newspapers.com', case=False, na=False)
    | df['Source'].str.contains(r'\d{4}_\d{2}_\d{2}', regex=True, na=False)
    | (df['Season'] >= 2003)
)
```
This is deliberate — the docstring explains it's meant to avoid flagging
ordinary same-opponent typo/duplicate pairs across two newspapers. But
the side effect: any row sourced from a yearbook site (`classmates.com`),
a program's own alumni site, a rival program's site, or a
playoff-history archive — none of which match any of the three
conditions for pre-2003 seasons — **never enters `detect`'s conflict-
finding logic at all**, regardless of how clean the GhostTeam signature
on it is. `queue --anchor` for a team whose only real duplicates live in
these excluded sources will come back empty, not because the team is
clean, but because `detect` structurally never registered anything for
it.

**Confirmed via `diagnose_game_count_anomaly.py`'s first real hit
(2026-09-10, New Orleans Jesuit, LA)**: a well-documented program pulling
from 8+ independent source types (`jesuitnola.org`, several `classmates.com`
yearbook pages, newspaper CSVs, `newspapers.com` images, `cebyrdathletics.com`,
`ahsfhs.org`, `14-0productions.com`, `bluejaystigers.com`) showed the exact
GhostTeam "same game, wrong opponent name" signature (identical 19-7
score, same date, two different named opponents) plus straightforward
score-conflict duplicates (two sources disagreeing on a final score) and
at least one likely OCR-garbled score (`20-1` — no legitimate football
score ends in a lone unmatched point; the real game was a `12-0` on the
same date-adjacent matchup). None of it was visible to `detect` because
none of the colliding sources were `newspapers.com`, dated-filename, or
post-2003.

**The generalizable lesson**: a program's source richness is a
duplication risk surface, not purely a data-quality asset. The more
independent historical archives that documented a team (alumni sites,
rival-program sites, dedicated playoff-history sites), the more likely
overlapping, un-reconciled entries exist for it — and the *less* likely
`detect`'s current filter catches it, since these richer sources are
exactly the kind most likely to be pre-2003 and non-newspapers.com.
`diagnose_game_count_anomaly.py` (run against all sources, unfiltered)
is a useful complementary check precisely because it doesn't share this
blind spot — worth running periodically per state even after `detect`'s
queue looks clean, especially against well-known historic programs.

**Remediation for rows `detect` never registered**: no existing queue
entry to pull from — these need manual investigation registration and
`fix`/`delete`, the same pattern used for the one-off Trafton duplicate
(see below). Not yet decided: whether `fetch_reliable_games()`'s filter
should be widened to also trust a pair of two different non-newspapers.com
sources when they show the airtight "identical score on both sides"
signature — a real design trade-off, not resolved as of 2026-09-10.

---

## Case study: institutional renames aren't data errors (Trafton Academy → Chapel Trafton)

Two `HS_Scores` rows for the same real 1994 game, same score, one day
apart, under two different team names (`Baton Rouge Trafton Academy
(LA)` and `Baton Rouge Chapel Trafton (LA)`), surfaced as investigation
4609 (and again independently as 4770 — the same root cause can surface
under multiple separate `InvestigationID`s for the same anchor team; when
closing one with a root-cause fix, check whether other open
investigations for the same anchor share the same explanation before
treating them as separate problems).

Resolution came from the school's own official history page
(`dunhamschool.org/history` — a school's "History"/"About" page is often
the fastest way to resolve an ambiguous rename, worth trying before
assuming a name discrepancy is a data error): Trafton Academy opened
independently in 1981, merged with The Chapel School in 1986, was
officially renamed "The Chapel Trafton School" in 1988, then became "The
Dunham School" in 1996. Both database names are genuinely correct for
different eras — pre-1988 rows should say "Trafton Academy," 1988+ rows
should be consolidated to "Chapel Trafton" (any 1988+ row still saying
"Trafton Academy" is a newspaper using the legacy name after the
official rename, not an error). This is a **date-scoped** fix, same
shape as the Reserve/Leon Godchaux 1972-77 split earlier — can't go
through the simple state-wide alias-consolidation CSV, needs individual
row fixes scoped by season. Investigations 4609 and 4770 both closed on
this basis; 12 resulting duplicate rows cleaned up via
`RemoveDuplicateGamesParameterized` afterward.

**Don't over-apply this pattern — confirmed via a real near-miss
(2026-09-19, Midland Lee/Legacy, TX).** Not every rename is date-scoped
like Trafton/Chapel Trafton. This project's actual naming convention,
confirmed directly by the user: when the SAME continuous school
temporarily changes its name and later reverts (Midland Lee → Midland
Legacy for a few years over a Civil-War-reference name controversy, then
back to Midland Lee), **every historical `HS_Scores` row gets retroactively
updated to the CURRENT name** — a flat, all-seasons alias merge, not
date-scoped. If the name changes again, all rows get updated again. The
`<STATE>_Alias_Rules.csv` entry `Midland Legacy (TX) → Midland Lee (TX)`
is exactly this and is CORRECT as a flat merge — don't blank it out or
date-scope it. The distinguishing question before assuming a rename needs
Trafton-style date-scoping: is this a genuine institutional change (a
merger, a school literally becoming a different entity) or just the same
continuous school using a different name for a while and reverting? Only
the former gets date-scoped; the latter always collapses to whatever name
is current.

---

## Team tier classification (Weak/Strong opponent detection)

Not the same thing as 6/8-man `LevelMismatch` — this is a **competitive-strength**
classification (Weak/Strong/implicitly-Normal), built and consumed by
two separate tools:

- **`classify_team_tiers.py`** — builds/refreshes a **nationwide**
  (not state-scoped) reference table, `HS_Team_Tier_Classification`.
  Two-stage: **Stage 1 (name-seed)** — `Weak` if the name has a
  sub-varsity suffix (` JV `/` B `/` C `/` Lightweight `/` Freshmen `/
  ` Frosh ` immediately before the state tag); `Strong` only for "College
  Frosh"/"College JV" specifically (deliberately narrow so it doesn't
  misfire on real schools like "___ College Prep"). **The module
  docstring also claims "Deaf" in the name is a Stage-1 seed — this is
  NOT what the code does; see the confirmed bug below.** **Stage 2
  (one-hop propagation)** — a team with no distinguishing name gets `Weak` if
  ≥65% of its entire game history (min 5 games, both configurable) is
  against a Stage-1 weak-seed opponent. Propagation stops at one hop
  deliberately, so it doesn't mislabel an entire legitimate small-school
  league (like 8-man OK football) just for being a tightly-connected
  cluster. Teams that hit neither bar aren't stored at all — absence =
  implicitly `Normal`.
  ```powershell
  python classify_team_tiers.py --dry-run     # counts only, zero writes
  python classify_team_tiers.py               # write for real (still nationwide)
  ```
- **`mapping_conflict_audit.py detect-tier-mismatch --state XX`** — reads
  that table to flag actual suspicious games. Weak-vs-Weak and
  Normal-vs-Normal are always skipped. A Strong-tier opponent (college
  frosh/JV) gets flagged regardless of margin. A Weak-tier opponent only
  gets margin-checked if its own **name** contains "Deaf" (JV/B/C/etc.
  presence alone isn't suspicious); `--margin-threshold` (default 15)
  sets how close a margin has to be before it's flagged as implausible
  for facing a genuinely weak opponent.
  ```powershell
  python mapping_conflict_audit.py detect-tier-mismatch --state XX --margin-threshold 15 --dry-run
  ```
  Both scripts' `--dry-run` are confirmed true dry-runs (zero DB writes).

**Confirmed root-cause bug in `classify_team_tiers.py` (2026-09-10)**:
Stage 1's `static_seed` dict (`build_classification()`, lines ~119-124)
is populated *only* from `COLLEGE_FROSH_JV_RE` and `WEAK_SUFFIX_RE` —
`DEAF_RE` is never checked there, despite the module docstring claiming
"Deaf" in the name is a Stage-1 seed. `DEAF_RE` only appears later
(lines ~138-139), and only to decide whether an *opponent* counts as
weak when scoring some *other* team's Stage-2 propagation percentage.
**No Deaf-named team is ever directly seeded — every single one,
without exception, depends entirely on whether its own schedule happens
to be ≥65% against already-weak opponents**, which is arbitrary relative
to the documented intent. A Deaf school with a schedule mixed between
deaf-school peers and mainstream small schools can easily land under
65% and simply never classify as `Weak` at all, defaulting to `Normal`.

This is the actual root cause behind the LA/NC false-positive symptom
described below (investigations 4853/4854, both closed
Verified-FalsePos) — not a coincidental "one side happened not to
propagate" story, but a structural gap affecting every Deaf-named team
nationwide.

Confirmed empirically (2026-09-10) with the actual pair from 4853/4854:
`North Carolina School for the Deaf (NC)` is `Weak`/`Propagated` (69.95%
of 213 games against seed-weak opponents — happened to clear the 65%
threshold by luck of its particular opponent mix), while `Louisiana
School for the Deaf (LA)` returns zero rows from
`HS_Team_Tier_Classification` — genuinely absent, defaulting to
`Normal`, because it never had a direct path to `Weak` regardless of
propagation outcome. This asymmetry is also provable directly from
`find_tier_mismatches()`'s control flow without querying the DB: its
three early `continue`s (Normal-vs-Normal, Weak-vs-Weak,
Strong-either-side) are mutually exclusive and exhaustive, so the only
way a Deaf-vs-Deaf game reaches the margin check at all is if exactly
one side is `Weak` and the other `Normal`.

**Fix #1 — PATCHED 2026-09-10** in `classify_team_tiers.py`: Stage 1 now
directly seeds Deaf-named teams as `Weak`, era-gated per name (using that
name's max season across the full dataset, since `HS_Team_Tier_Classification`
only stores one `Tier` per `TeamName` — no season column — so per-season
granularity isn't representable in the table regardless; matches the
same era-gating already used in the Stage 2 propagation check). Deaf-named
teams will now mostly get `Basis='NameSeed'` instead of depending on
propagation luck. **`classify_team_tiers.py` needs to be re-run for this
fix to take effect** — the patched code doesn't retroactively update
`HS_Team_Tier_Classification` until it's run again.

**Fix #2 — still open**: even with fix #1 applied, still worth having
`find_tier_mismatches()` also skip when the *anchor's* name matches the
Deaf pattern directly, as defense in depth rather than relying solely on
tier-table membership. Not yet patched as of 2026-09-10.

**Since so many LA team names got renamed this session** (Trafton, Lake
Arthur, Bossier merges, Tallulah, etc.) **and this classifier fix just
landed**, re-run `classify_team_tiers.py`
fresh before trusting a `detect-tier-mismatch --state LA` pass — Stage 1
seeding depends on exact current name strings.

**Confirmed post-fix (2026-09-10)**: re-ran `classify_team_tiers.py` fresh
(4721 name-seed rows: 4510 weak/211 strong, 13 propagated) then
`detect-tier-mismatch --state LA` — 63 flagged games, 0 *new*
investigations (all had already been registered pre-fix). Of the 59 open
`Medium - Weak-tier margin inconsistent` investigations, effectively all
were **Louisiana School for the Deaf** (one was Texas School for the Deaf)
against ordinary small LA schools, spanning **1938 through 2016** with
margins from blowouts (48-6, 39-0, 41-7) to nailbiters (30-25, 0-0, 6-6) —
many against the same recurring small-town opponents across multiple
decades (Franklinton Pine, Livonia, White Castle, Brusly, Cottonport,
etc.). This is not noisy data — it is a real, long-running competitive
varsity program. **The Weak-tier "expect a blowout margin" assumption
baked into the margin check does not hold for genuine Deaf-school
programs**, and this is now a confirmed *systemic* false-positive class,
not a one-off: OK had already independently hit the identical pattern and
closed 321 rows the same way. All 59 LA rows were bulk-closed in one shot:
```powershell
python mapping_conflict_audit.py defer --state "(LA)" --type TierMismatch \
  --priority-like "Medium" --status "Verified-FalsePos" --from-status New \
  --reason "Deaf-school opponent margin check false positive, see OK precedent (321 rows)"
```
**Takeaway for the next state**: expect the `Medium - Weak-tier margin`
bucket to be dominated by this same false-positive class every time a
state has a School for the Deaf with real game history. Don't triage it
row-by-row — spot-check a handful first (confirm they're genuinely a
Deaf-school opponent with plausible small-school scores, not something
else), then bulk-`defer` the whole `Medium` priority bucket. The `High -
Strong-tier` (college frosh/JV opponent) bucket is a different, much
smaller, and NOT presumptively-false-positive check — that one still
needs individual review. This strengthens the case for Fix #2 above (skip
the margin check entirely when the anchor is itself Deaf-named) since the
false-positive rate on this specific check is apparently very high nearly
everywhere it's been run — worth considering removing the Deaf-margin
check's individual-row registration altogether in favor of a one-line
"known non-issue" note, rather than generating hundreds of rows across
every state that then need the same bulk-dismiss treatment.

**Historical "why" (David, via Gemini research, 2026-09-10)**: state
schools for the deaf were genuinely competitive mid-20th-century varsity
peers, not a structurally weak tier, for real historical reasons — pre-WWII
and mid-century high school football was hyper-local/informal
(geographic-proximity scheduling, primitive travel), and state residential
schools drew a statewide catchment pool comparable to or larger than tiny
rural villages, giving them real roster depth. The shift toward
classification-by-enrollment leagues (LHSAA and peers formalizing Class
A/AA/AAA/AAAA tiers post-WWII) plus shrinking residential-school
enrollment (mainstreaming, evolving deaf-education law) drove the later
move to specialized/lower-enrollment divisions (e.g. present-day 8-man
conferences) where a real competitive gap reemerged. This matches what we
saw in LA's data: the close-margin games we just bulk-closed cluster in
1938-1998 (real localism-era parity), while the two 2016 LSD blowouts (8-68,
60-14) land in the specialization era Gemini describes — consistent with a
real, historically-grounded parity/gap split rather than pure detector
noise. **Open, not-yet-acted-on refinement**: this suggests
`MIN_WEAK_TIER_SEASON = 1930` in `classify_team_tiers.py` may be
mis-targeted — it's closer to "earliest season with organized records"
than "the year Deaf programs became a genuinely weak tier," which per this
account didn't happen until the classification-era shift decades later.
Not changing the constant without season-by-season margin data across
multiple states' Deaf programs to locate the real inflection point —
noting it here so it isn't re-discovered from scratch later.

**Follow-up (2026-09-10): replaced the era-cutoff idea with a
rating-differential check, and it caught a real error the bulk-dismiss
missed.** Rather than guess a better `MIN_WEAK_TIER_SEASON`, David proposed
using each team's own `HS_Rankings` Week=52 (season-final) rating to derive
an *expected* margin per game — `ExpectedMargin = Rating(Anchor, Season) -
Rating(Opponent, Season)` — instead of a flat `--margin-threshold`. Rating
formula matches the one used throughout `generate_*.py`: `0.958 *
Avg_Of_Avg_Of_Home_Modified_Score + 2.791`.

A nationwide pull of every `%Deaf%` team's Week=52 rating by season
(prototype: `diagnose_deaf_tier_margin_ratings.py`, read-only) confirmed
this isn't LA-specific: the Deaf-cohort's season-average rating declines
almost monotonically, from roughly -5 to -25 in the 1920s-30s, through -30
to -45 in the 1960s-70s, to -60 to -85 by the 1990s-2010s — a *continuous*
decline, not a single inflection year, with the spread (StdDev) also
widening over time (~15-20 mid-century vs. ~30 in recent decades). This is
exactly why no single cutoff year could ever be right, and why a
season-aware rating differential is structurally the better check.

Testing the rating-differential model against all 64 ratable rows from
LA's 59 closed Deaf-margin investigations (`--test-la`) showed a tight fit
— residual (actual margin minus expected margin) mean -3.0, median -3.2,
std 9.8 across games spanning 1938-2025. That tightness is itself a strong
validation: **one row broke the pattern badly** — investigation 4877
(Baton Rouge University Lab vs. Louisiana School for the Deaf, 1984),
residual -35.6, more than 3x any other row. Pulling the actual `HS_Scores`
rows revealed why: **two independent sources for the same 1984-10-19
game disagreed** — `newspapers.com` (a contemporary box score) said
34-6, a `classmates.com` yearbook scan said 34-33. LSD's other two 1984
results (55-8, 6-0) confirm single-digit margins were the season's norm;
the yearbook's "33" was a transcription/OCR error, not a real one-point
upset. This was a genuine `DuplicateImport`-class error that the earlier
flat-margin-based bulk `Verified-FalsePos` close had incorrectly swept up
along with the 58 real false positives — the rating-differential residual
is what surfaced it. Fixed: `delete`d the yearbook duplicate (ID
`6533F703-14BE-4D90-899A-2A34D97BD851`), kept the newspapers.com row,
re-`close`d investigation 4877 as `Fixed` (was wrongly `Verified-FalsePos`).

**Decision**: the rating-differential check will **replace** (not
supplement) the flat `--margin-threshold` in `find_tier_mismatches()` —
self-calibrating per season/team, no static cutoff year needed, and
demonstrably tighter than raw margin alone. **Not yet implemented in
`mapping_conflict_audit.py` itself** — `diagnose_deaf_tier_margin_ratings.py`
is still a standalone prototype in the outputs folder; porting the
`ExpectedMargin`/residual logic into `find_tier_mismatches()` as the real
check is the next concrete step. Two known gaps to carry into that port: a
game where either side lacks a Week=52 rating that season (sparse/very old
eras) can't be scored this way and needs a fallback (or stays excluded, as
it did for investigation 4906 in this test); and the rating itself is
computed from `HS_Scores`, the same table being checked, so a badly wrong
game can distort both sides of the comparison — same circularity the
existing name-seed tier system already has, not a new risk, but worth
remembering when a residual looks large only because the *opponent's*
rating (not the anchor's) is itself corrupted by bad data.

---

## OK 6-man/8-man mapping (`ossaa_8man_import.py`) — status as of 2026-09-12

Bespoke tooling already exists for this (unlike Iowa's more manual
"Historical Level Correction" investigative approach documented in an
earlier master workflow doc) — `ossaa_8man_import.py` +
`ossaa_8man_match_review.csv`, seeding `HS_Team_Level_History`/
`HS_Team_Conference_History` from the official 2025-26 OSSAA Class B/C
manual. **OSSAA's 8-man tier has no separate 6-man division** — one
combined class covers it. The review CSV has **82 data rows** (not 83 —
an early miscount, corrected), **81 `Confirmed=1`** (ready to apply as-is)
and **exactly 1 `Confirmed=0`**: `Central High,B-I,Marlow Central (OK)`,
originally resolved via unrecorded "opponent evidence."

**That one unconfirmed row needs real scrutiny before trusting it.**
`ghostteam_wrongname_triage.csv` (from `auto_triage_ghostteam_wrongname.py`,
a separate GhostTeam auto-triage tool) independently shows `Marlow (OK)`
and `Marlow Central (OK)` flagged `SUBSTRING_BUT_RISKY_QUALIFIER`
**11 separate times**, spanning 1929-1955, several with actual head-to-head
games between the two on the same date (e.g. 1929-10-26, 1953-10-10,
1954-10-30). That's proof — not a guess — that these are two genuinely
distinct real programs in this dataset. Don't apply the OSSAA
`Central High → Marlow Central (OK)` row until whatever "opponent
evidence" originally justified it is re-found and re-verified against
this now-confirmed risk.

The other 81 rows are safe to run:
```powershell
python ossaa_8man_import.py --input ossaa_8man_match_review.csv --apply
```
(omit `--apply` for a dry-run preview first.)

**South Coffeyville (task #41) turned out to live inside this same OSSAA
file.** `South Coffeyville,C,Coffeyville South (OK),ExactNormalized,1,1`
was already `Confirmed=1` — mechanically fine for the 8-man import since
name-order doesn't matter to its matcher, but it surfaced the real,
separate naming-consistency problem worked through in the consolidation
section above (`Coffeyville South (OK)` had the words backwards relative
to both the real-world school name and the DB's own already-established
`South Coffeyville Oklahoma Union (OK)`).

---

## New Orleans Jesuit cluster (LA) -- naming fixed, same-date collision backlog documented (2026-09-13)

**Naming/ID confusion resolved.** `HS_Team_Names` had 4 Jesuit-named LA entries;
verified via each school's own official history before touching anything
(`jesuitnola.org/about/history`, Loyola College Prep's Wikipedia page):
- `New Orleans Jesuit (LA)` (65848) -- canonical, 1910-2025, 918 games (now 921).
  Founded 1847 as College of the Immaculate Conception; became Jesuit High
  School in 1926. DB already used one canonical name across the full
  history (not date-scoped like Trafton/Chapel Trafton -- that case involved
  an actual institutional merger, this is just a rename, and the existing
  convention here is one name per continuously-operating program).
- `Jesuits College (LA)` (1477) -- 3 games, 1914-1919, all vs. Gulf Coast
  Military Academy (MS), single source (ahsfhs.org). Sits well inside NOJ's
  own already-covered range -- old newspaper naming variance, not an era
  boundary. Checked for duplicate collision against NOJ's own log first
  (zero matches) -- merged via alias, confirmed clean (918+3=921 after).
- `Jesuit blue jays (LA)` (54789) -- 0 games, mascot-variant stub. Merged
  via alias (registry-only, no HS_Scores rows to move), per the
  never-delete-from-HS_Team_Names rule (same treatment as the Oklahoma
  Union 0-game stub in the South Coffeyville case).
- `Shreveport Jesuit (LA)` (25580) -- 206 games, 1941-1994. Confirmed
  genuinely distinct via Loyola College Prep's own history: St. John
  Berchmans College (1902) -> St. John's High School (1941) -> **Jesuit
  High School of Shreveport (1960-1982)** -- the DB's date range already
  spans this program's full St. John's/Jesuit/Loyola-era history under one
  name, same "one canonical name per continuous program" convention.
  **Left untouched** -- an earlier suggestion to rename it to "Shreveport
  Jesuit Caddo Parish (LA)" was rejected: would have invented a new
  compound name the project's own conventions warn against, and the
  existing name is already unambiguous (different city from New Orleans).

Ran `RemoveDuplicateGamesParameterized @State='LA'` (first-ever full
`First to Last` sweep for LA) immediately after the merge: 82 regular +
2 swapped duplicates archived/deleted (consistent with a first full-state
sweep finding the whole backlog, not just what the merge itself created --
same pattern as OK), 2544 stale forfeit flags corrected (one-time backlog,
not a new problem, same as OK's 482).

**Original cluster problem (the actual reason this was flagged, per the
"Detector blind spot" section above) is much bigger than first scoped.**
Pulled `New Orleans Jesuit (LA)`'s full 921-game log and scanned
programmatically for same-date collisions (impossible for one team to play
two games in a day, so every hit is either a duplicate/wrong-opponent
GhostTeam case or a source date error): **91 same-date groups found (193
rows)** -- far more than the handful the original narrative description
implied. This confirms the blind-spot theory at scale: none of these are
`newspapers.com`/dated-filename/post-2003-exclusive, so `detect` never
touched any of them.

**Fixed (high confidence, applied 2026-09-13):**
- `1937-11-06`: Alexandria Bolton (Times-Picayune, contemporary clipping)
  vs. Holy Cross (bluejaystigers.com, compiled site), both 6-6 -- identical-
  score ghost-team signature. Deleted the Holy Cross row (`8793A3A3-...`).
- `1960-11-18`: Lake Charles LaGrange appears twice from jesuitnola.org's
  own two different documents -- Post-Season Records PDF says `1-20`
  (tripped the suspicious-score check: no legitimate score ends in a lone
  point), 1960 yearbook PDF says `12-0`. Deleted the Post-Season-Records
  row (`1ADB8BB1-...`), kept the yearbook's `12-0`.

**Deferred -- 89 remaining same-date groups, NOT yet resolved.** Spot-
checked several during triage; source-reliability heuristics (dated
newspaper clipping > compiled/yearbook site) do NOT cleanly resolve most
of these:
- Some are the same source disagreeing with itself (e.g. `1953-11-07`:
  bluejaystigers.com lists Holy Cross at both 7-6 and 47-13 same date --
  likely two different seasons' games cross-listed, not a source-quality
  issue).
- Some show a newspaper roundup image apparently producing two unrelated
  teams' scores both tagged to Jesuit (e.g. `1980-09-19`: the same
  `newspapers.com/image/216287513` produced both a Lake Charles score and
  a Shreveport Green Oaks score) -- looks like a multi-game-roundup
  scraping/attribution bug, a distinct pattern from a simple duplicate,
  not yet root-caused.
- One (`1949-10-01`, New Orleans Redemptorist vs. Baton Rouge Redemptorist,
  both 14-12) is a genuine toss-up: both schools were real and had football
  in 1949 (Baton Rouge's Redemptorist HS founded 1947, New Orleans's
  Redemptorist Boys and Girls HS ran 1937-1980). Identical score strongly
  suggests one real game with a city mixup (same bug class as the Lake
  Arthur state-mistagging case), but which city is correct isn't
  resolvable from what's available online.

**Recommendation for the next pass on this list**: this volume (89 cases,
likely several distinct root-cause patterns mixed together) is a strong
argument for finally answering the open question in the "Detector blind
spot" section above -- whether to widen `fetch_reliable_games()`'s filter
to also trust a pair of two non-newspapers.com sources with an airtight
signature, rather than hand-triaging each case. Not built as of
2026-09-13. Full list of the 89 deferred groups (ID/date/opponent/score/
source for each row) below for whenever this gets picked back up.

- `1920-11-05`:
  - `01B7F443-7668-4C2E-8E23-2603AD1DD740` Opp=New Orleans Easton (LA) Jesuit 0-7 src=http://www.classmates.com/siteui/yearbooks/4182832395?page=29
  - `99F16F1F-EA46-46C9-BB05-304E7B2BE7B5` Opp=New Orleans Easton (LA) Jesuit 0-6 src=http://www.classmates.com/siteui/yearbooks/4182832475?page=19
- `1931-11-27`:
  - `511F8583-7D44-425A-91B3-361884ED299C` Opp=Shreveport Byrd (LA) Jesuit 0-14 src=http://www.cebyrdathletics.com/uploadedfiles/files/14401715412015ByrdFootballRecordBook.pdf
  - `4B9B47C7-E1AC-4706-980F-DBE2977492C6` Opp=New Orleans Easton (LA) Jesuit 12-0 src=http://www.classmates.com/siteui/yearbooks/92321?page=87
- `1933-11-10`:
  - `8A68E3E6-60A7-49D4-805D-040703A7159C` Opp=New Orleans Easton (LA) Jesuit 25-0 src=http://www.classmates.com/siteui/yearbooks/4182832475?page=19
  - `EECFC6DE-AB2A-4BB9-B0F0-7AB8DD9A156F` Opp=Morgan City (LA) Jesuit 6-0 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1937-11-05`:
  - `CBA5526A-D08F-4534-B8CB-2DEABBB00520` Opp=Picayune (MS) Jesuit 8-0 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `FDEE853D-69E4-4CA0-B4E9-808EB359F375` Opp=New Orleans Easton (LA) Jesuit 0-6 src=http://www.classmates.com/siteui/yearbooks/4182832475?page=19
- `1940-11-09`:
  - `5DD0F82F-83B3-4718-9132-B70B4EBE665C` Opp=New Orleans F.T. Nicholls (LA) Jesuit 45-6 src=Morning_Advocate_1940_11_09_13.csv
  - `4E7F24FB-1D48-4229-8BCC-A921DAC7B8E7` Opp=New Orleans Holy Cross (LA) Jesuit 25-7 src=http://www.bluejaystigers.com/
- `1943-11-19`:
  - `79B59040-E5EF-43D9-9FE2-90D4D7DE225E` Opp=Mount Carmel (IL) Jesuit 12-0 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `C18208D3-1908-471B-99D6-7FF3EF582AB3` Opp=Shreveport Byrd (LA) Jesuit 25-7 src=http://www.cebyrdathletics.com/uploadedfiles/files/14401715412015ByrdFootballRecordBook.pdf
- `1946-11-15`:
  - `113FD4C8-1A7D-43EC-ABFB-AA93CCAB1CF7` Opp=Jennings (LA) Jesuit 48-14 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `55FB774B-BF3F-4103-993B-BF2413821537` Opp=Baton Rouge Istrouma (LA) Jesuit 19-6 src=https://www.classmates.com/siteui/yearbooks/4182731923?page=46
- `1947-11-07`:
  - `1417536B-9321-4BC1-BF5A-F36EE92A34CD` Opp=Port Arthur St. James (TX) Jesuit 19-7 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `974157C1-4602-4C00-A40B-4947843CA9CE` Opp=New Orleans Easton (LA) Jesuit 6-14 src=http://www.classmates.com/siteui/yearbooks/4182832698?page=16
- `1949-10-01`:
  - `A287A75A-FF76-4B3D-B4A7-D18684ED03DF` Opp=New Orleans Redemptorist (LA) Jesuit 14-12 src=The_Crowley_Post_Signal_1949_10_01_6.csv
  - `0F165D7B-A405-4EB2-86AF-EB22D151D25E` Opp=Baton Rouge Redemptorist (LA) Jesuit 14-12 src=The_Shreveport_Journal_1949_10_01_6.csv
- `1950-11-11`:
  - `D762FF6C-7F59-425C-85C5-6A07ABF1B731` Opp=Pensacola (FL) Jesuit 8-7 src=The_Shreveport_Journal_1950_11_11_6.csv
  - `D5F3FE6B-522E-4EA2-BF20-1661B289D264` Opp=New Orleans Holy Cross (LA) Jesuit 14-18 src=http://www.bluejaystigers.com/
- `1952-11-08`:
  - `5CC39585-3A14-452C-B988-375A458FC450` Opp=Pensacola (FL) Jesuit 20-7 src=The_Shreveport_Journal_1952_11_08_6.csv
  - `C91A5764-A7E2-4CEE-9EE1-7F70E7F52FC3` Opp=New Orleans Holy Cross (LA) Jesuit 14-7 src=http://www.bluejaystigers.com/
- `1953-11-07`:
  - `75B40C03-7DBD-44D3-9B1B-98B1C70D35A1` Opp=Pensacola (FL) Jesuit 6-7 src=The_Crowley_Post_Signal_1953_11_07_6.csv
  - `FCF0A479-1CBE-45A1-9E7B-EF8D0DC762F4` Opp=New Orleans Holy Cross (LA) Jesuit 7-6 src=http://www.bluejaystigers.com/
  - `354E1117-07F4-4FCD-9D78-491CFCC23391` Opp=New Orleans Holy Cross (LA) Jesuit 47-13 src=http://www.bluejaystigers.com/
- `1957-11-15`:
  - `5F2B4876-A49F-4695-8904-8AB9D57A9FFA` Opp=New Orleans De La Salle (LA) Jesuit 14-12 src=https://www.classmates.com/siteui/yearbooks/4182817931?page=107
  - `5D4220A4-FB42-464D-8AA5-ABCA1C1CF915` Opp=Baton Rouge Redemptorist (LA) Jesuit 0-28 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1958-10-31`:
  - `D2D4EFB4-F9FD-4942-ABBD-001F0F29671E` Opp=Baton Rouge (LA) Jesuit 19-0 src=https://www.classmates.com/siteui/yearbooks/33890?page=95
  - `D35CEF91-2CF9-478E-9507-4764185721F1` Opp=New Orleans De La Salle (LA) Jesuit 48-13 src=https://www.classmates.com/siteui/yearbooks/94307?page=135
- `1959-11-07`:
  - `073166C2-5943-45BD-A5FF-2F126B23EDD5` Opp=Baton Rouge Redemptorist (LA) Jesuit 33-6 src=The_Shreveport_Journal_1959_11_07_6.csv
  - `DE69831C-5574-4E7C-9AF7-1FDD6184725B` Opp=New Orleans Holy Cross (LA) Jesuit 33-20 src=http://www.bluejaystigers.com/
- `1960-09-23`:
  - `75A307DA-E0F7-4211-AA67-114123F0FDD1` Opp=Pensacola (FL) Jesuit 7-19 src=http://www.classmates.com/siteui/yearbooks/4182862619?page=206
  - `089E45A1-6442-488A-AC5B-1F835B3D10D5` Opp=Murphy (LA) Jesuit 35-6 src=https://cdn1.jesuitnola.org/site/wp-content/uploads/2015/04/JHS_1960_Yearbook_P67-91_Sports_Intramurals.pdf
  - `0D9B93C9-360F-4215-9ECA-4D052F0FCD4C` Opp=Houma Terrebonne (LA) Jesuit 19-7 src=http://www.classmates.com/siteui/yearbooks/99338?page=168
  - `29976C2D-1BC9-41A9-9C2F-4E123698EB1E` Opp=Springhill (LA) Jesuit 26-13 src=https://www.classmates.com/siteui/yearbooks/4182718074?page=109
- `1960-10-01`:
  - `38E01C8D-17B3-4B74-A8EF-E2F5485EE675` Opp=New Orleans Fortier (LA) Jesuit 52-0 src=The_Shreveport_Journal_1960_10_01_6.csv
  - `C02F23D9-20CB-4062-B5D5-FC88272D3C7B` Opp=Haynesville (LA) Jesuit 21-7 src=The_Shreveport_Journal_1960_10_01_6.csv
- `1960-11-04`:
  - `D6F448CE-D72F-414B-8060-7E2FA25859C2` Opp=New Orleans De La Salle (LA) Jesuit 46-0 src=https://www.classmates.com/siteui/yearbooks/38781?page=123
  - `B04114A4-B31F-423E-A97F-7B547F3698EF` Opp=Bay St. Louis St. Stanislaus (MS) Jesuit 40-0 src=http://www.ahsfhs.org/MISSISSIPPI/
  - `6147EB26-1B03-43CA-A132-13CCDD1EECE7` Opp=New Orleans De La Salle (LA) Jesuit 27-0 src=https://cdn1.jesuitnola.org/site/wp-content/uploads/2015/04/JHS_1960_Yearbook_P67-91_Sports_Intramurals.pdf
- `1960-11-11`:
  - `2396BFB5-6383-40C5-9629-0574A48C6398` Opp=New Orleans Easton (LA) Jesuit 12-0 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `33D65CBD-BE0E-468B-B11E-DAF7EB85CC1B` Opp=New Orleans Holy Cross (LA) Jesuit 33-20 src=https://cdn1.jesuitnola.org/site/wp-content/uploads/2015/04/JHS_1960_Yearbook_P67-91_Sports_Intramurals.pdf
- `1961-10-14`:
  - `A132C557-DD9C-4E02-8104-DEDB8920523C` Opp=Homer (LA) Jesuit 41-6 src=The_Shreveport_Journal_1961_10_14_6.csv
  - `9FD9F7CE-22B6-4B56-BE4B-223CAF8790A6` Opp=New Orleans Fortier (LA) Jesuit 20-0 src=The_Shreveport_Journal_1961_10_14_6.csv
- `1962-09-14`:
  - `79C338AF-FA62-470C-92CB-896AF04E69F2` Opp=Baton Rouge Istrouma (LA) Jesuit 3-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182738650?page=122
  - `80A347D6-13E5-4E6C-8B6C-2B903C40F51E` Opp=Houma Terrebonne (LA) Jesuit 13-0 src=http://www.classmates.com/siteui/yearbooks/4182877037?page=66
- `1962-09-21`:
  - `6CD3A033-FBCF-4138-818F-D5D50D5C28FC` Opp=Springhill (LA) Jesuit 7-14 src=https://www.classmates.com/siteui/yearbooks/1000255776?page=91
  - `CCB03A9C-0C51-4405-BB0E-1ADEFDA1A999` Opp=Lafayette (LA) Jesuit 13-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182738650?page=122
- `1964-09-11`:
  - `0CB99225-F594-4DD0-92A7-E48AF6498B54` Opp=New Orleans Easton (LA) Jesuit 19-20 src=http://www.classmates.com/siteui/yearbooks/4182832065?page=216
  - `FB30B601-0C2D-4673-91C0-A7143DCE8D08` Opp=Harvey West Jefferson (LA) Jesuit 24-6 src=http://www.classmates.com/siteui/yearbooks/227070?page=216
- `1965-10-08`:
  - `2C14AC13-F074-4BC2-BA3B-4EDA5B554A03` Opp=New Orleans De La Salle (LA) Jesuit 32-13 src=https://www.classmates.com/siteui/yearbooks/34334?page=164
  - `A192187C-FFE4-4B14-8CC0-5480289A46F3` Opp=Bourg South Terrebonne (LA) Jesuit 26-0 src=https://www.classmates.com/siteui/yearbooks/4182877047?page=146
- `1966-11-11`:
  - `738E4664-F7B4-479B-A4DA-20E896AAFA78` Opp=Harvey West Jefferson (LA) Jesuit 7-14 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `935B927C-1047-474A-8E0A-28931B4F617E` Opp=New Orleans De La Salle (LA) Jesuit 7-7 src=https://www.classmates.com/siteui/yearbooks/29063?page=138
- `1966-11-18`:
  - `079EDF42-F9A2-4DD1-A72E-6936E353A24A` Opp=Harvey West Jefferson (LA) Jesuit 27-14 src=http://www.classmates.com/siteui/yearbooks/4182792545?page=157
  - `E0677AD1-8860-4684-AF48-5938A5893329` Opp=Baton Rouge Glen Oaks (LA) Jesuit 19-6 src=http://www.classmates.com/yearbooks/Glen-Oaks-High-School/4182731883?page=110
- `1967-09-15`:
  - `2E479527-A101-4431-A8E4-6D77B0200F7B` Opp=Shreveport CaptainShreve (LA) Jesuit 34-0 src=http://www.classmates.com/siteui/yearbooks/183791?page=157
  - `DD107F99-8429-4BC9-B67D-0FF8D709A2CB` Opp=Houma Terrebonne (LA) Jesuit 20-14 src=http://www.classmates.com/siteui/yearbooks/63257?page=88
- `1967-11-17`:
  - `20DDBD55-4EF1-4F7B-BF89-A7FAE2618D12` Opp=Bourg South Terrebonne (LA) Jesuit 7-13 src=https://www.classmates.com/siteui/yearbooks/4182877063?page=168
  - `97B152C4-E191-4045-8108-F0C84642B1B2` Opp=New Orleans De La Salle (LA) Jesuit 0-6 src=https://www.classmates.com/siteui/yearbooks/25899?page=120
- `1967-11-24`:
  - `CD102F09-EA31-4873-A906-13E70BCD2C44` Opp=Jennings (LA) Jesuit 26-9 src=https://www.classmates.com/siteui/yearbooks/4182838440?page=176
  - `DBD4B75E-AA09-4BF4-A927-24621AECE45E` Opp=Metairie Archbishop Rummel (LA) Jesuit 7-6 src=http://www.classmates.com/siteui/yearbooks/4182845533?page=82
- `1968-09-13`:
  - `51544076-008A-4AC0-9BA0-57E1CA437EEB` Opp=Shreveport CaptainShreve (LA) Jesuit 6-0 src=http://www.classmates.com/siteui/yearbooks/166907?page=243
  - `D6F1E6AD-B948-4C81-A403-33EA5BA4CAFB` Opp=Alexandria Bolton (LA) Jesuit 21-6 src=http://www.classmates.com/yearbooks/Bolton-High-School/125332?page=214
  - `57C384F5-440B-4C9C-95FB-FC116AEDD7C3` Opp=New Orleans Holy Cross (LA) Jesuit 7-14 src=http://www.classmates.com/yearbooks/Holy-Cross-High-School/190089?page=110
- `1968-10-04`:
  - `1D186BDE-A6E0-40EF-966E-3BF8236FD2B0` Opp=Bossier City Airline (LA) Jesuit 13-34 src=http://www.classmates.com/siteui/yearbooks/4182715531?page=207
  - `E5A26CF2-CEDA-4A1C-AE17-10675B77AE3F` Opp=New Orleans St. Aloysius (LA) Jesuit 21-6 src=https://www.classmates.com/siteui/yearbooks/4182830355?page=94
- `1969-10-03`:
  - `322D5C28-9B0A-4549-9C87-94226D81D1F7` Opp=New Orleans Brother Martin (LA) Jesuit 19-14 src=http://www.classmates.com/yearbooks/Brother-Martin-High-School/142419?page=88
  - `A22C9B0C-D57F-418F-A74B-112EC293D86B` Opp=Bossier City Airline (LA) Jesuit 6-29 src=http://www.classmates.com/siteui/yearbooks/55691?page=196
- `1971-09-03`:
  - `56A4B79D-1D98-483F-A90D-D258D000A982` Opp=Bourg South Terrebonne (LA) Jesuit 0-6 src=https://www.classmates.com/siteui/yearbooks/94912?page=93
  - `16392194-27D2-4F65-A197-9C2F8E5573E8` Opp=New Orleans Brother Martin (LA) Jesuit 16-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182783321?page=74
- `1971-10-29`:
  - `516700D6-C498-40E2-97F3-5DF8823BFCF8` Opp=New Orleans Holy Cross (LA) Jesuit 10-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182783321?page=74
  - `219D61FA-751B-43A0-80F8-79F6FDEC5807` Opp=New Orleans De La Salle (LA) Jesuit 30-7 src=https://www.classmates.com/siteui/yearbooks/188489?page=123
- `1972-09-15`:
  - `FE7B5528-82A5-4061-99B2-75AC628DDD99` Opp=Bourg South Terrebonne (LA) Jesuit 0-0 src=https://www.classmates.com/siteui/yearbooks/86380?page=78
  - `1BCB84F0-E780-4B2C-9611-3B37E151DE75` Opp=New Orleans Brother Martin (LA) Jesuit 0-33 src=http://www.classmates.com/yearbooks/Brother-Martin-High-School/188571?page=78
- `1973-09-07`:
  - `2F7543AB-06D2-4719-9819-C96A5FD4B0E6` Opp=Bourg South Terrebonne (LA) Jesuit 0-0 src=https://www.classmates.com/siteui/yearbooks/88062?page=76
  - `6B69E56F-CF26-46C5-85BD-1A8A72FDA644` Opp=Bossier City Airline (LA) Jesuit 3-6 src=http://www.classmates.com/siteui/yearbooks/52789?page=155
- `1974-09-06`:
  - `E92B3DC7-631F-4353-B459-21AFB49CDDA3` Opp=Bossier City Airline (LA) Jesuit 0-13 src=http://www.classmates.com/siteui/yearbooks/4182779515?page=155
  - `5EC4EA8E-D29A-407B-8BEE-F2F5942C0B9A` Opp=Bourg South Terrebonne (LA) Jesuit 0-7 src=https://www.classmates.com/siteui/yearbooks/88063?page=81
- `1975-09-05`:
  - `2D239553-B921-4701-87DB-CE160CF5277E` Opp=Bossier City Airline (LA) Jesuit 0-14 src=http://www.classmates.com/siteui/yearbooks/53375?page=160
  - `7A667299-E6E8-40BA-8D10-519E2C97C669` Opp=New Orleans St. Augustine (LA) Jesuit 7-35 src=https://www.classmates.com/siteui/yearbooks/4182928892?page=131
- `1975-09-12`:
  - `850DB77C-1F77-4980-AD56-5B7F3D344886` Opp=Shreveport Southwood (LA) Jesuit 7-13 src=https://www.classmates.com/siteui/yearbooks/151300?page=157
  - `DA36BE06-6DB8-4DEF-86DE-2010168C3067` Opp=Bourg South Terrebonne (LA) Jesuit 6-26 src=https://www.classmates.com/siteui/yearbooks/4182877048?page=117
- `1975-10-03`:
  - `8C7796FA-6B08-4106-ADFC-3594E7F219EF` Opp=New Orleans Brother Martin (LA) Jesuit 0-26 src=http://www.classmates.com/yearbooks/Brother-Martin-High-School/1300337634?page=102
  - `84E3AF89-1FA2-40E7-A990-B3255BBBB3F9` Opp=Ruston (LA) Jesuit 17-0 src=http://www.classmates.com/yearbooks/Ruston-High-School/123097?page=180
- `1976-10-01`:
  - `65EABC39-5899-44BC-877E-80ADD8C944BF` Opp=Ruston (LA) Jesuit 10-3 src=http://www.classmates.com/yearbooks/Ruston-High-School/9978?page=94
  - `6E1C6B6A-7EF6-43AF-9305-906128D5D3A5` Opp=New Orleans Brother Martin (LA) Jesuit 10-34 src=http://www.classmates.com/yearbooks/Brother-Martin-High-School/192783?page=194
- `1977-10-14`:
  - `5908F77F-C188-4AFB-9724-211A7BDC9408` Opp=New Orleans Holy Cross (LA) Jesuit 34-35 src=http://www.classmates.com/yearbooks/Holy-Cross-High-School/4182780881?page=100
  - `9DAB5485-CD22-486C-9C1C-1295099AE75E` Opp=Ruston (LA) Jesuit 14-6 src=http://www.classmates.com/yearbooks/Ruston-High-School/123079?page=96
  - `3EE42574-ADDA-4370-8D63-939C73FFB62E` Opp=New Orleans Brother Martin (LA) Jesuit 7-13 src=http://www.classmates.com/yearbooks/Brother-Martin-High-School/188572?page=112
- `1978-10-06`:
  - `4653795F-B11A-4CD2-8E64-DB960C452C4F` Opp=Ruston (LA) Jesuit 29-10 src=http://www.classmates.com/yearbooks/Ruston-High-School/123098?page=148
  - `219A1412-6F20-4A9D-8718-E5A52725EE1F` Opp=Marrero John Ehret (LA) Jesuit 20-0 src=http://www.classmates.com/siteui/yearbooks/4182797696?page=175
- `1978-11-10`:
  - `1B457F3D-8613-48A7-93BE-D6B017D3CA08` Opp=Harvey West Jefferson (LA) Jesuit 28-14 src=http://www.classmates.com/siteui/yearbooks/4182840406?page=108
  - `2AB4E126-BFCD-43EA-8FEE-5D6347EBD270` Opp=Harvey West Jefferson (LA) Jesuit 8-14 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1979-09-07`:
  - `5897F4C2-BBF5-4338-8FF4-977779053425` Opp=New Orleans McDonogh 35 (LA) Jesuit 30-6 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182786920?page=80
  - `E1EBBA8A-EC92-433F-A88B-4BCB0C53CE05` Opp=Bossier City Airline (LA) Jesuit 14-0 src=http://www.classmates.com/siteui/yearbooks/97162?page=118
- `1979-09-15`:
  - `9F73C7AB-E70F-4FD6-8133-35E8500F89C8` Opp=New Orleans McDonogh (LA) Jesuit 30-6 src=The Shreveport Journal
  - `1F015AD4-E630-41D0-A282-67C494CB694A` Opp=Bossier City Bossier (LA) Jesuit 7-0 src=The Shreveport Journal
- `1979-10-12`:
  - `FC368BF4-3A7B-40BD-A13E-299C759A13FA` Opp=Ruston (LA) Jesuit 23-0 src=http://www.classmates.com/yearbooks/Ruston-High-School/1000255837?page=102
  - `DA886E6F-DF6E-4D38-A362-B526D1E6DB26` Opp=New Orleans Brother Martin (LA) Jesuit 14-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182786920?page=80
- `1979-10-19`:
  - `A039A23C-D81B-4FB7-8A8A-4FD11A5B7E6B` Opp=New Orleans De La Salle (LA) Jesuit 28-7 src=https://www.classmates.com/siteui/yearbooks/1300336787?page=129
  - `F95087CB-7026-4FD9-BA25-6F9A0262CCB3` Opp=New Orleans St. Augustine (LA) Jesuit 7-23 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182786920?page=80
- `1979-10-27`:
  - `68190E38-FC5E-4A4E-84F7-ABCA0637E338` Opp=Minden (LA) Jesuit 7-22 src=The Shreveport Journal
  - `32F797C9-5D05-45AB-9710-7DE8E5EF0A84` Opp=New Orleans St. Augustine (LA) Jesuit 7-24 src=The Shreveport Journal
- `1980-09-19`:
  - `6B9396FA-8BC2-46EF-9FD5-81A552A439A6` Opp=Lake Charles (LA) Jesuit 27-6 src=https://www.newspapers.com/image/216287513
  - `B4EE7C93-C5AD-47AA-9499-C578CB62215F` Opp=Shreveport Green Oaks (LA) Jesuit 28-21 src=https://www.newspapers.com/image/216287513
  - `F136FBE8-9E97-4220-B67E-D3873F75CA8A` Opp=Lake Charles (LA) Jesuit 27-26 src=https://www.newspapers.com/image/216187766
- `1980-09-26`:
  - `1752BC9F-CFE6-4E58-A0AC-D61EC55D1233` Opp=Metairie Archbishop Rummel (LA) Jesuit 0-14 src=http://www.classmates.com/yearbooks/Archbishop-Rummel-High-School/75709?page=56
  - `E66E0A45-A995-411E-9A9F-B70A9DECB121` Opp=New Orleans Holy Cross (LA) Jesuit 14-24 src=https://www.newspapers.com/image/216288935/
- `1980-10-17`:
  - `2D803BBB-33E1-49C3-88D0-E57908575458` Opp=Ruston (LA) Jesuit 34-35 src=https://www.newspapers.com/image/216575425
  - `828BF65F-ABD2-4C53-8CDC-8C789C4F815C` Opp=New Orleans Brother Martin (LA) Jesuit 0-3 src=https://www.newspapers.com/image/216575425
- `1980-10-31`:
  - `6B8D6510-B0F8-4E57-8F42-762285306DB1` Opp=Marrero Archbishop Shaw (LA) Jesuit 6-22 src=http://www.classmates.com/yearbooks/Archbishop-Shaw-High-School/4182731852?page=76
  - `E2AEA297-E18E-4679-99F7-F46D3854BB6C` Opp=Chalmette (LA) Jesuit 14-9 src=https://www.newspapers.com/image/216274109
- `1981-09-04`:
  - `EC46521A-718E-4171-8A61-4CDB15BCA51E` Opp=Bossier City Airline (LA) Jesuit 3-14 src=https://www.newspapers.com/image/215137939
  - `21826660-E13F-46F2-93D2-03935E4864C7` Opp=New Orleans Washington (LA) Jesuit 3-6 src=http://www.classmates.com/yearbooks/Jesuit-High-School/20614?page=174
- `1981-09-18`:
  - `823C62C3-E3CD-4745-BB8E-7DAF0D348BB6` Opp=Houma Terrebonne (LA) Jesuit 21-6 src=http://www.classmates.com/siteui/yearbooks/101292?page=124
  - `88149968-42E2-4387-9446-304A36C82779` Opp=Thibodaux (LA) Jesuit 23-6 src=https://www.newspapers.com/image/215219024
- `1981-09-25`:
  - `23FB05C3-CA48-46F0-B20C-6DA5375B840C` Opp=Mansfield (LA) Jesuit 14-21 src=https://www.newspapers.com/image/215245757
  - `C4804A20-74E7-4D68-A0A4-6D4EA05FD592` Opp=Metairie Archbishop Rummel (LA) Jesuit 20-17 src=http://www.classmates.com/yearbooks/Jesuit-High-School/20614?page=174
- `1981-10-09`:
  - `C4CC987D-1B79-4EA1-A3C1-D697481C7057` Opp=New Orleans Holy Cross (LA) Jesuit 42-27 src=http://www.classmates.com/yearbooks/Jesuit-High-School/20614?page=174
  - `99E6FE55-F7D5-4139-BE2D-545D337970C6` Opp=Monroe Richwood (LA) Jesuit 22-0 src=https://www.newspapers.com/image/216588699
- `1981-10-16`:
  - `F6E63FF4-3CD0-42A0-927B-D4DD4269943D` Opp=Marrero Archbishop Shaw (LA) Jesuit 25-28 src=https://www.newspapers.com/image/215216434/
  - `5DB2F419-1279-4EA2-BB5A-8339F704D682` Opp=Minden (LA) Jesuit 15-35 src=https://www.newspapers.com/image/215216434/
- `1981-10-23`:
  - `1CAB1CFD-CD13-40FD-844E-C27A4D19021D` Opp=Monroe Wossman (LA) Jesuit 6-40 src=https://www.newspapers.com/image/215247170
  - `1B0930A8-A2B6-4616-9200-8D907B4DFCE3` Opp=New Orleans De La Salle (LA) Jesuit 35-7 src=http://www.classmates.com/yearbooks/Jesuit-High-School/20614?page=174
  - `E3CD7177-5E40-4A96-A5EE-01923300B031` Opp=Chalmette (LA) Jesuit 24-16 src=https://www.newspapers.com/image/215247170
- `1981-10-30`:
  - `98A0511E-1DE6-4E81-A9F6-DA5F08A86387` Opp=Haughton (LA) Jesuit 0-23 src=http://www.classmates.com/siteui/yearbooks/166438?page=77
  - `00E30DD2-EDA3-49D7-972D-FA14BC519AD1` Opp=DeRidder (LA) Jesuit 34-13 src=https://www.newspapers.com/image/215954795
- `1981-11-06`:
  - `FE240E02-718A-4543-9AC4-1E6AEEAF9775` Opp=New Orleans St. Augustine (LA) Jesuit 19-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/20614?page=174
  - `E75CCA20-3DEE-4F02-A3FF-42F065F03EFC` Opp=New Orleans Brother Martin (LA) Jesuit 7-0 src=https://www.newspapers.com/image/216573618
  - `45BF6210-AF70-4B29-86B8-6E43BD301258` Opp=Shreveport Northwood (LA) Jesuit 28-8 src=https://www.newspapers.com/image/215777674/
  - `DE057FB9-B588-452F-9FE1-2863807D87D0` Opp=Vivian North Caddo (LA) Jesuit 27-0 src=https://www.newspapers.com/image/216573618
- `1982-09-03`:
  - `042B2247-FBBC-455F-BA4C-CC943DBBAE0F` Opp=Dallas Kimball (TX) Jesuit 0-28 src=https://www.newspapers.com/image/215956902
  - `B7793F21-1594-4AED-9314-8694ED1CBCFD` Opp=Bossier City Airline (LA) Jesuit 6-2 src=http://www.classmates.com/siteui/yearbooks/4182715545?page=165
- `1983-09-09`:
  - `419DE3D6-586B-4FCF-A6E3-B587C96F1973` Opp=New Orleans Brother Martin (LA) Jesuit 19-18 src=http://www.classmates.com/yearbooks/Jesuit-High-School/134432?page=146
  - `E1734966-B4F2-4D8C-8939-83B173F35AC2` Opp=Houma Terrebonne (LA) Jesuit 7-26 src=https://www.newspapers.com/image/219906410
- `1983-09-16`:
  - `39725436-8A5E-4A99-8C4C-41AE9A67ABFB` Opp=Slidell Salmen (LA) Jesuit 30-6 src=https://www.newspapers.com/image/219918531/
  - `04622D5F-8EED-4A40-AC88-BCEBEBD4EDD1` Opp=New Orleans De La Salle (LA) Jesuit 14-16 src=http://www.classmates.com/yearbooks/Jesuit-High-School/134432?page=146
- `1983-10-14`:
  - `23850B81-EB89-4F8B-AA52-BE4FD7BC08D8` Opp=Marrero Archbishop Shaw (LA) Jesuit 14-28 src=https://www.newspapers.com/image/219905841
  - `C71F0B3A-4867-44BF-A56D-9ADEB0B69A57` Opp=Marrero Archbishop Shaw (LA) Jesuit 14-21 src=https://www.newspapers.com/image/216144758
- `1984-09-07`:
  - `F7756F69-2ECF-4595-ADB1-F583275C06FF` Opp=Gray Bourgeois (LA) Jesuit 21-6 src=http://www.classmates.com/yearbooks/Jesuit-High-School/24933?page=176
  - `8BE4588D-7CDC-4957-A841-7F8F3A24E650` Opp=Houma Terrebonne (LA) Jesuit 17-7 src=https://www.newspapers.com/image/217399466
- `1984-11-09`:
  - `000F5C34-D2B0-4E7F-9C6C-DDFEAD61640F` Opp=Harvey West Jefferson (LA) Jesuit 0-33 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `7B59C896-1FB5-4DF8-96A2-A08FCA2F982A` Opp=Harvey West Jefferson (LA) Jesuit 10-33 src=https://www.newspapers.com/image/216339359
- `1985-10-11`:
  - `0687DECD-897F-4804-A3DA-A357075DF40D` Opp=Chalmette (LA) Jesuit 26-15 src=http://www.classmates.com/yearbooks/Jesuit-High-School/41577?page=204
  - `0F0E4225-5592-4D1F-A370-F7330A011A5E` Opp=Chalmette (LA) Jesuit 40-8 src=https://www.newspapers.com/image/217731074/
- `1986-11-07`:
  - `31B3F0C7-7CA5-4BF1-9AF0-E00A2149EAC8` Opp=Marrero Archbishop Shaw (LA) Jesuit 0-33 src=https://www.classmates.com/siteui/yearbooks/4182803743?page=152
  - `AA2CC1E0-8155-4B7D-AF93-64B63B99A8AF` Opp=Baton Rouge Belaire (LA) Jesuit 2-13 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1987-09-25`:
  - `5A144BDA-81C2-4375-AC83-AE712C8EAF64` Opp=New Orleans Brother Martin (LA) Jesuit 39-7 src=https://www.newspapers.com/image/216553873/
  - `5DA58B6A-0B4A-4D25-945D-9532FBCE41FF` Opp=New Orleans St. Augustine (LA) Jesuit 30-35 src=http://www.classmates.com/yearbooks/Jesuit-High-School/129766?page=42
- `1987-10-09`:
  - `7F662543-4578-4402-BEAD-59CD56BBFE62` Opp=Metairie Archbishop Rummel (LA) Jesuit 31-0 src=http://www.classmates.com/yearbooks/Archbishop-Rummel-High-School/26402?page=118
  - `6EEDFB51-7444-4F4F-8DD1-09CDACFD752D` Opp=New Orleans De La Salle (LA) Jesuit 29-9 src=http://www.classmates.com/yearbooks/Jesuit-High-School/129766?page=42
- `1987-10-23`:
  - `0592A051-5728-4967-97AD-91DF78548A22` Opp=New Orleans Holy Cross (LA) Jesuit 46-20 src=http://www.classmates.com/yearbooks/Jesuit-High-School/129766?page=42
  - `0CCD530E-E2C4-4DE1-9FE9-648A3D4A8474` Opp=Marrero Archbishop Shaw (LA) Jesuit 0-21 src=http://www.classmates.com/yearbooks/Archbishop-Shaw-High-School/137406?page=130
- `1987-11-06`:
  - `8FF7F058-86BF-4ED3-80E7-036689774FF9` Opp=Harvey West Jefferson (LA) Jesuit 0-25 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `2E4EDCFD-4165-43F7-AA9F-A4AE7C8822E3` Opp=Chalmette (LA) Jesuit 30-6 src=https://www.newspapers.com/image/211023807/
- `1988-10-07`:
  - `52414828-1520-46C0-AD24-D79229A68C84` Opp=Metairie Archbishop Rummel (LA) Jesuit 37-34 src=http://www.classmates.com/yearbooks/Archbishop-Rummel-High-School/27320?page=62
  - `644341B9-1585-4959-BB1B-9F29CC5ED094` Opp=Metairie Archbishop Rummel (LA) Jesuit 37-24 src=https://www.newspapers.com/image/216914783
- `1989-09-08`:
  - `985B9545-6126-48D1-8DBC-2211DDB035A5` Opp=Mandeville (LA) Jesuit 6-32 src=https://www.newspapers.com/image/216967946/
  - `C00A44B9-068A-4368-B535-00B14E08C6F0` Opp=New Orleans McDonogh (LA) Jesuit 0-23 src=http://www.classmates.com/yearbooks/Jesuit-High-School/1000240437?page=22
- `1989-09-29`:
  - `00467BD0-0636-467A-A4AB-CC32536B112E` Opp=New Orleans Holy Cross (LA) Jesuit 14-7 src=http://www.classmates.com/yearbooks/Jesuit-High-School/1000240437?page=22
  - `DBD79651-5F56-41F3-894B-3182D2D2616B` Opp=New Orleans De La Salle (LA) Jesuit 40-14 src=https://www.newspapers.com/image/216996663/
- `1989-10-20`:
  - `E2A684FA-A70F-46BD-B5DD-0D0404B1EDE8` Opp=New Orleans J.S. Clark (LA) Jesuit 14-0 src=https://www.newspapers.com/image/213949971
  - `B835FF06-C9B0-4715-9B0D-CD89167896A9` Opp=New Orleans St. Augustine (LA) Jesuit 34-11 src=http://www.classmates.com/yearbooks/Jesuit-High-School/1000240437?page=22
- `1990-11-16`:
  - `0B08A135-10C2-4C40-BF28-F4106A34AABB` Opp=Monroe Neville (LA) Jesuit 13-12 src=https://www.newspapers.com/image/216911418
  - `DF0EB354-C957-46EB-8CE2-0DBA23841E32` Opp=Monroe Neville (LA) Jesuit 3-12 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1990-11-23`:
  - `3CE28D84-3253-4BA9-9049-B20E9DB00AFB` Opp=New Orleans Landry-Walker (LA) Jesuit 2-26 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `08779382-C475-490B-85D2-E5E3F03509F5` Opp=New Orleans Landry-Walker (LA) Jesuit 32-26 src=https://www.newspapers.com/image/217317646
- `1992-11-06`:
  - `A66B3BAE-D026-43EB-A148-F77D23BC170C` Opp=New Orleans Easton (LA) Jesuit 35-6 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `46F668D4-D3FC-4BDE-A3D6-147FB0E4E32B` Opp=New Orleans Brother Martin (LA) Jesuit 3-0 src=https://www.newspapers.com/image/218008401
- `1994-11-11`:
  - `EB6B24B1-582D-46F0-BD5B-5FEC89D0A92B` Opp=Metairie Archbishop Rummel (LA) Jesuit 48-7 src=http://www.classmates.com/yearbooks/Jesuit-High-School/204311?page=10
  - `4384064E-8226-4FCF-A7EE-EB80C0EA961E` Opp=Harvey West Jefferson (LA) Jesuit 9-22 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1994-11-18`:
  - `F1C1FC49-6DAE-42A5-AD62-010CAE7777E1` Opp=Harvey West Jefferson (LA) Jesuit 29-22 src=http://www.classmates.com/yearbooks/Jesuit-High-School/204311?page=10
  - `F45066F1-BAA3-42C2-970C-5059752CC480` Opp=New Orleans St. Augustine (LA) Jesuit 4-21 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1994-12-02`:
  - `4573B6E1-8EEE-4727-9AF6-950FC04BDDD0` Opp=Marrero John Ehret (LA) Jesuit 44-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/204311?page=10
  - `B2738ABE-920F-41E9-A03C-477AE14C185B` Opp=Monroe Ouachita Parish (LA) Jesuit 0-42 src=https://www.newspapers.com/image/218065595
- `1996-09-20`:
  - `84CF7C2E-4D64-4555-BC10-0311EC9A4DD0` Opp=Baton Rouge Catholic (LA) Jesuit 7-28 src=https://www.newspapers.com/image/218428038/
  - `1A85BDCA-FFD2-421F-8169-9CB8272B0551` Opp=Bastrop (LA) Jesuit 50-0 src=http://www.classmates.com/yearbooks/Jesuit-High-School/4182782632?page=134
- `1996-11-22`:
  - `67DD14A5-2091-4C6D-AA85-5F66763562C7` Opp=Slidell (LA) Jesuit 17-6 src=https://www.newspapers.com/image/217444553
  - `D5DA02AD-2D2F-4140-9BBD-B01F8C275491` Opp=Raceland Central Lafourche (LA) Jesuit 0-0 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1996-11-29`:
  - `95E2A720-1853-4DFD-81FE-1C44EE523609` Opp=Lafayette Carencro (LA) Jesuit 4-24 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
  - `211ED7B2-0F4B-491E-B52A-08DC2385769D` Opp=Raceland Central Lafourche (LA) Jesuit 30-0 src=https://www.newspapers.com/image/218449845
- `1997-11-14`:
  - `8C431059-ED8F-473E-AACD-B0D0A6DFDAFE` Opp=Ponchatoula (LA) Jesuit 20-17 src=https://www.newspapers.com/image/218554011/
  - `FBD460F5-17F3-4B30-A304-3FE1344A6D2F` Opp=Reserve East St. John (LA) Jesuit 27-13 src=https://cdn3.jesuitnola.org/site/wp-content/uploads/2013/08/Football_Post-Season_Records_20151214.pdf
- `1999-09-17`:
  - `046850F0-D28A-4715-A669-C50F6E12C389` Opp=Picayune (MS) Jesuit 27-28 src=http://www.ahsfhs.org/mississippi/
  - `939A525D-D25A-4BD3-A2D2-48C57948CE38` Opp=Picayune (MS) Jesuit 7-28 src=https://www.newspapers.com/image/213296497
- `2003-11-28`:
  - `0221E58A-F162-4F72-A456-DB8A2AA22388` Opp=Lafayette Carencro (LA) Jesuit 41-56 src=https://www.newspapers.com/image/360230845
  - `04543014-0E48-4B2A-9828-80F794255D6A` Opp=Lafayette Carencro (LA) Jesuit 41-55 src=https://sites.google.com/a/lpssonline.com/crobear-football/seasons-results-articles

---

## Tool: `maxpreps_scraper_db.py` overnight automation (set up 2026-09-13/15)

**Goal**: scrape every team's current-season MaxPreps schedule automatically,
overnight, resuming across multiple nights until a full sweep completes, then
sitting idle until the next weekly re-sweep (Sunday nights) — without a
human needing to babysit it or manually run `EXEC FinalizeMaxPrepsData`
each morning.

**Pieces**:
- `maxpreps_scraper_db.py` — the scraper itself (unchanged CLI: no args for
  a normal/resumed run; `--force-new-batch` to deliberately start a new full
  sweep on a non-Sunday, for a manual first kickoff or an off-schedule
  restart — the unattended nightly trigger never passes this flag).
- `run_maxpreps_scraper.ps1` (same folder) — the wrapper. Sets working
  directory, enforces a hard runtime cap so a stuck run can't eat into the
  next day, kills orphaned chromedriver/chrome processes on timeout, logs
  its own start/stop/PID to `maxpreps_wrapper_log.txt` (separate from the
  scraper's own log, so you can tell "never fired" apart from "fired, had a
  problem"). Caps the scraper at **8 hours**. Widened from the original
  10PM–5AM/7-hour window on 2026-09-14 once real pacing data (~18 sec/team)
  showed 8 hours gets through ~1,600 teams/night vs. ~1,400 at 7 hours.
- **`maxpreps_watcher.ps1`** (same folder) — **what actually triggers the
  wrapper nightly, as of 2026-09-17. Windows Task Scheduler is NOT used for
  this anymore** — see fix #10/#11 below for why. This is a standalone
  PowerShell loop: sleeps in ≤1-hour chunks (heartbeat-logged to
  `maxpreps_watcher_log.txt`) until 9PM, calls `run_maxpreps_scraper.ps1`
  unchanged, loops forever. Must be launched detached so it survives closing
  the terminal:
  ```powershell
  Start-Process powershell.exe -ArgumentList '-ExecutionPolicy Bypass -File "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\maxpreps_watcher.ps1"' -WindowStyle Hidden
  ```
  **Does not survive reboot/logout** — needs a shortcut to that same command
  in the Startup folder (`Win+R` → `shell:startup`) to relaunch on login;
  this was identified as the last piece but has not actually been created
  yet. **Only ever run one instance** — launching the start command twice
  (e.g. retrying after a failed double-click attempt) leaves two watchers
  both firing at 9PM; check with
  `Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Select-Object ProcessId, CommandLine`
  and `Stop-Process -Id <PID> -Force` the extra one. Also: if you stop the
  watcher for a manual same-day run, **you must restart it afterward** —
  this was missed once (2026-09-17) and no automated run fired that night at
  all, caught only by cross-referencing the empty log against what should
  have been a 9PM entry.

**Fixes made getting this working (all in `maxpreps_scraper_db.py` unless
noted) — read these before touching the automation again, each one was a
real incident, not theoretical**:

1. **Batch-completion marking**. The original script found/resumed a
   `'running'` batch or created a new one, but never marked a finished batch
   `'completed'` — so the *next* run kept "resuming" the same empty batch
   forever, silently doing nothing. This is the root cause of last year's
   automation dying invisibly. Fixed: when a run finds zero
   `pending`/`failed` teams left, it now marks the batch `'completed'`.

2. **Sunday-only new-batch creation**. Once (1) was fixed, a naive nightly
   trigger would immediately start a brand-new full sweep every single
   night the moment a batch finished, instead of the intended
   "sweep once, then idle until next Sunday" cadence. Fixed: a new batch is
   only created on Sunday (`datetime.now().weekday() == 6`), unless
   `--force-new-batch` is passed.

3. **Batch-table namespace collision (real incident, 2026-09-13/14)**.
   `scraping_batches`/`team_scraping_status` are SHARED with
   `rescrape_2019_ambiguous.py` (task #40's 2019 date-truncation
   reconciliation tool — its batches are named
   `"2019 Date Truncation Reconciliation - <timestamp>"`). The scraper's
   original "resume any `status='running'` batch" query doesn't
   distinguish whose batch it is. This actually happened: our automation
   resumed and auto-finalized two of that tool's batches (31, 32),
   including scraping one team (Barnsdall) through the wrong URL-building
   logic. Verified no real data corruption resulted (the finalized rows
   were legitimately 2019-dated — MaxPreps happened to be serving that
   inactive program's last real season as its "current" schedule), but the
   risk was real, and batches 27/28/30 still had genuine pending
   reconciliation work that could have been corrupted the same way. Fixed:
   the batch lookup is now scoped to `batch_name LIKE 'MaxPreps Scrape - %'`
   only — it can never again touch another tool's batch. **If you build
   another tool that uses these shared tables, give it a distinctive
   `batch_name` prefix and scope its own lookups the same way.**

4. **File logging**. Originally logged only to console via
   `logging.basicConfig()` with no file handler — under Task Scheduler
   (no attached console), a failure left zero diagnostic record. This is
   why last year's failure looked "silent." Fixed: logs to both console and
   `maxpreps_scraper_log.txt` (same folder) via an explicit `FileHandler`.

5. **Auto-finalize, originally called exactly once per batch — SUPERSEDED,
   see fix #13.** Originally the script only printed a reminder
   (`EXEC dbo.FinalizeMaxPrepsData @BatchID=X`) for a human to run
   manually — useless unattended. First fix: call it automatically, but
   only once, at the moment a batch flips `running` → `completed`, because
   `Unmatched_Opponents` had no dedup guard and would duplicate rows if
   called repeatedly on a still-growing batch. This had a real cost: for a
   ~16k-team national batch that takes over a week to exhaust, NO games
   became visible in `HS_Scores` until the entire week-plus sweep finished —
   a multi-day blackout every weekly cycle. Fix #13 below adds the missing
   dedup guard and makes finalize safe (and now default) to call every
   night.

6. **Dead-driver recovery**. Observed live: when chromedriver/Chrome
   crashes mid-batch, every subsequent team failed identically for ~35
   seconds (3 retries) before giving up — left overnight this would burn
   the entire runtime cap failing team after team instead of recovering.
   Fixed: ported the same dead-session detection
   (`'WinError 10061'`/`'Connection aborted'`/`'invalid session id'`/
   `'session not created'` in the error text) and driver-restart logic that
   `rescrape_2019_ambiguous.py` already had, into the main scrape loop.

7. **Chromedriver/Chrome version mismatch** (2026-09-13 incident, not a
   code fix). `setup_driver()` uses Selenium Manager with no explicit
   chromedriver path/version, which caches a resolved driver binary. After
   Chrome auto-updated, the cached driver no longer matched and every
   launch failed with `session not created: Chrome instance exited`.
   Fix was operational, not code: clear the cache —
   `Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\selenium"` — and
   Selenium Manager re-resolves the correct driver on next launch. **If
   this exact error reappears, try this first before assuming it's the
   headless/display issue in #8.**

8. **Headless mode** (2026-09-15 incident). Both automated 9PM runs on
   9/14 and 9/15 failed within ~8 seconds with the *same* `session not
   created: Chrome instance exited` message as #7 — but this time a
   visible-but-blank Chrome window was observed sitting on a bare `data:`
   URL, meaning Chrome *did* launch but the WebDriver session handshake
   never completed. Root cause: the PC's screen sleeps after 1 hour idle
   (disk/PC power itself never sleeps), and non-headless Chrome's
   renderer/GPU process can fail to attach once the display is asleep —
   which lines up with the 9PM trigger landing well after the screen had
   gone to sleep. Fixed: added `--headless=new` (the modern headless mode —
   not the deprecated `--headless`) to `setup_driver()`'s Chrome options.
   Renders pages/JS identically to headful mode, just with no visible
   window, so screen sleep can no longer interfere. `rescrape_2019_ambiguous.py`
   inherits this automatically since it imports `setup_driver` from this
   module.

9. **Chromedriver/GPU/elevation dead ends, then real diagnostic data
   (2026-09-16/17)**. After #7/#8 didn't fully hold (Task-Scheduler-
   triggered runs kept failing with `session not created: Chrome instance
   exited` and zero further detail), tried and ruled out, in order:
   `--disable-gpu` (headless Chrome still inits a GPU process by default;
   didn't help), removing "Run with highest privileges" from the Task
   Scheduler action (didn't help), Windows Defender (Protection History
   showed nothing blocked at the relevant times). Turned on chromedriver's
   own verbose logging (`Service(log_output=..., service_args=['--verbose'])`)
   as the next step instead of guessing a sixth flag — this showed Chrome
   launching with a fully valid command line and exiting with zero further
   information, pointing at something structural about Task Scheduler's
   logon session itself, not a Chrome flag.

10. **Path A (Task Scheduler "run whether logged on or not") abandoned.**
    The fix that fully explains #7-#9: Task Scheduler's unattended/batch
    logon mode needs a real stored password, and this machine's account is
    passwordless (Windows Hello PIN only) — confirmed via Settings →
    Accounts, no password exists to enter into the credential prompt.
    "Run only when user is logged on" (the original setup) is what kept
    failing in #7-#9. This path is closed for this machine.

11. **Path B: `maxpreps_watcher.ps1` replaces Task Scheduler entirely
    (2026-09-17, confirmed working 2026-09-18 21:00:00).** Runs as an
    ordinary interactive-session process instead — the exact kind of
    session every manual test had always succeeded in. See the `Pieces`
    section above for how to launch/monitor it. This is the actual
    triggering mechanism now; Task Scheduler is not part of the automation
    anymore.

12. **`--disable-component-update` (2026-09-18)**. Found a ~10-hour orphaned
    Chrome updater background process left running after `driver.quit()`
    (repeated "Failed to open named pipe server... Access is denied"
    messages from `chrome\updater\ipc\...`). Added to `setup_driver()`'s
    Chrome options; unrelated to the Task-Scheduler saga above, just
    resource hygiene.

13. **Nightly finalize + `Unmatched_Opponents` dedup guard (2026-09-19)**.
    Root-caused why batch 33 sat with **zero** 2026 games visible in
    `HS_Scores` for 5+ days despite scraping running successfully every
    night: finalize only fired once, at full batch completion (fix #5).
    Added a `RawGameID` column (`= games_raw.raw_id`) to
    `Unmatched_Opponents` plus a `NOT EXISTS` guard on it in
    `FinalizeMaxPrepsData`, matching the guard `HS_Scores`/`Future_Games`
    already had. `maxpreps_scraper_db.py`'s `main()` now calls
    `EXEC dbo.FinalizeMaxPrepsData` after every night's chunk, not just once
    at the "no more teams" transition — games now land in `HS_Scores` within
    a day of being scraped instead of after the whole multi-day sweep
    finishes. Verified by calling finalize twice in a row on real data: zero
    new `Unmatched_Opponents` rows on the second call.

14. **Opponent-URL normalization bug — the big one (2026-09-19)**. Even
    after fix #13, the first real finalize run on batch 33 sent **96,198**
    rows to `Unmatched_Opponents` and **0** to `HS_Scores` — a 100% opponent-
    match failure across the entire 2026 season's scraped data. Root cause:
    `scrape_schedule_data_robust()` captured each opponent's raw scraped
    `href` unmodified (e.g. `.../mustangs/football/`) — MaxPreps links a
    schedule row's opponent to their team HOME page, never their schedule
    sub-page — while `URL_ProperName_Mapping.URL` is always
    `.../football/schedule/`-suffixed. A bare equality join can never match
    these. The PRIMARY team's URL never had this problem because
    `get_urls_to_process()` always runs it through `_clean_schedule_url()`
    before navigating there; the opponent side never got the same
    treatment. Fixed two places: (a) `scrape_schedule_data_robust()` now
    runs the captured `href` through `_clean_schedule_url()` at capture
    time, fixing all future scrapes; (b) `FinalizeMaxPrepsData` normalizes
    the opponent URL inline (CROSS APPLY, append `schedule/` if missing)
    before the join, which retroactively fixed the 96,198 already-stuck
    `games_raw` rows without needing to re-scrape anything — re-running
    finalize after this fix landed 6,433 real games into `HS_Scores`
    immediately (the first 2026-season data to ever reach that table).
    **If a future scraper variant captures opponent URLs differently,
    re-check this exact assumption before trusting its output.**

15. **`HS_Team_MaxPreps` is known-corrupted — this is documented elsewhere,
    not a new discovery.** `_AAA_Instructions/Re-Importing_MaxPreps_Data.md`
    (written 2026-06-08, for the separate past-season re-import project)
    already states: some `HS_Team_MaxPreps.Team_ID`s (example given: 9221)
    were incorrectly assigned hundreds of URLs, national "ALL" runs use
    `HS_Team_MaxPreps` anyway because the corruption "averages out" across
    16,000 teams, and — critically — *"Teams in team_scraping_status with no
    URL_ProperName_Mapping entry sit as 'pending' forever and are inert —
    not an error."* Investigating batch 33's ~6,552 permanently-pending rows
    (2026-09-19) confirmed this is working exactly as designed: they never
    block `get_urls_to_process()`'s completion check (it INNER JOINs to
    `URL_ProperName_Mapping`, so unmapped rows are invisible to it) and
    batch 33 completed correctly once every *mapped* team finished. Sizing
    the actual distinct-team gap (not raw stuck rows, which are inflated by
    ~486 team_ids having duplicate `team_scraping_status` rows — see below)
    found **973 distinct team_ids**, and — the real finding — **every single
    one is a duplicate `HS_Team_Names` record for a team that already has a
    correctly-mapped sibling team_id** (e.g. team_id 109 "Gilbertville-Don
    Bosco (IA)" duplicates the already-mapped team_id 31214 "Gilbertville
    Don Bosco (IA)" — same real school, hyphen vs. space is the only
    difference). This is task #52/#53's real shape: not "missing URLs" to
    backfill (backfilling would create a second legitimate-looking mapping
    and start double-scraping the same real school), but a **duplicate-team-
    record consolidation problem**, to be merged via the existing
    `sp_ConsolidateNames_FromStaging`-style tooling, not a URL-mapping fix.
    Root cause of the duplicates themselves (why a new `HS_Team_Names` row
    gets created instead of matching an existing team under a slightly
    different spelling) is not yet found — flagged as follow-up, see below.

16. **Periodic finalize during the loop, not just after it (2026-09-21) —
    fix #13 had a real gap.** Batch 34's first overnight run (2026-09-20
    21:00 → 2026-09-21 05:00, the exact 8-hour cap) scraped 33,391 raw games
    into `games_raw` and finalized **zero** of them. Root cause: a single
    chunk (`URL_PROCESS_LIMIT=2000` teams at ~18 sec/team ≈ 10 hours) is
    itself longer than the 8-hour runtime cap, so `run_maxpreps_scraper.ps1`
    force-kills the Python process externally (`Stop-Process -Force`) before
    it ever finishes the per-team loop — meaning the post-loop finalize call
    from fix #13 never gets reached most nights, silently, no error (the
    process is killed, not exceptioned). Fixed: finalize is now also called
    every 200 teams *inside* the loop, not just once after it, so a forced
    kill can only ever lose the last <200 teams' progress instead of a whole
    night's. Confirmed via a manual catch-up run
    (`EXEC dbo.FinalizeMaxPrepsData @BatchID = 34`) that the 33,391 backlogged
    rows finalized correctly once run. **If `HS_Scores`'s most recent
    `Date_Added` for `Source LIKE '%maxpreps%' AND Season = <current>` is
    stale relative to when the watcher last fired, this is the first thing
    to suspect** — check with:
    ```sql
    SELECT MAX(Date_Added) FROM HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = <current season>;
    ```

17. **Single-instance lock, and a Startup-folder shortcut for the watcher
    (2026-09-21) — closes two real gaps found the same day.** (a) The user
    manually launched the wrapper twice, 06:27 and 11:05, both with an
    8-hour cap — the first was almost certainly still running when the
    second started. Two concurrent scraper processes both writing to
    `games_raw`/`HS_Scores`/`Unmatched_Opponents`/`team_scraping_status`
    (made worse by fix #16's more-frequent periodic finalize) is the likely
    cause of an SSMS lock-up that same day. Fixed: `maxpreps_scraper_db.py`
    now writes a PID-stamped `maxpreps_scraper.lock` file on start and
    refuses to start if another instance's PID (checked via `tasklist`) is
    still alive; removes it on exit. Self-heals correctly after a forced
    kill (the wrapper kills the same PID recorded in the lock file, so
    `tasklist` correctly shows it gone next time and the lock is
    overwritten). (b) The user rebooted their PC, which — exactly as
    documented — killed the watcher (it never survived reboot/logout; this
    was a known, not-yet-closed gap since it was first built). Fixed:
    `create_watcher_startup_shortcut.ps1` (new, in `data_import/`) creates a
    Startup-folder shortcut so the watcher relaunches automatically on every
    future login. Run once: `.\create_watcher_startup_shortcut.ps1` — it
    does NOT start the watcher immediately, only sets up the future
    auto-start; it prints the one-off launch command for right now.

**Monitoring**: `maxpreps_watcher_log.txt`, `maxpreps_wrapper_log.txt`, and
`maxpreps_scraper_log.txt` (all in `data_import/`) are the three log files,
outermost to innermost. Check batch progress anytime with:
```sql
SELECT status, COUNT(*) AS TeamCount
FROM team_scraping_status
WHERE batch_id = <current batch_id>
GROUP BY status;
```
Check whether games are actually landing (not just scraped) with:
```sql
SELECT COUNT(*) FROM HS_Scores WHERE Source LIKE '%maxpreps%' AND Season = <current season>;
```

**2026 first full sweep**: batch 33, started 2026-09-14 (`--force-new-batch`,
since no real "MaxPreps Scrape -" batch had ever existed before this
automation). ~16,333 total teams, ~9,781 with a real `URL_ProperName_Mapping`
entry (the rest are the duplicate-record gap in fix #15). As of 2026-09-19,
first real 2026 games (6,433) landed in `HS_Scores` via fix #14; nightly
finalize (fix #13) now keeps it current going forward.

**Known follow-up work, not yet built**:
- **Duplicate-`HS_Team_Names`-record consolidation** (fix #15) — merge the
  973 confirmed duplicates into their canonical sibling team_id. Sized via
  a city+state-gated name-matching approach: 709 resolve with high
  confidence, 264 need manual review (195 where `HS_Team_MaxPreps` itself
  has no plausible candidate for that city, 69 genuinely tied same-city
  candidates). Deliberately deferred to the ongoing per-state alias-cleanup
  work rather than a bespoke script, per direction 2026-09-19.
- **Root cause of the duplicate-record creation itself** — not yet found.
  Something in the team-creation/import pipeline creates a new
  `HS_Team_Names` row instead of matching an existing team under a
  near-identical spelling; fixing this prevents next season's version of
  the same 973-team problem rather than just cleaning up this year's.
- **Startup-folder shortcut** for `maxpreps_watcher.ps1` so it survives
  reboot/logout (see fix #11) — agreed as the last piece, not yet created.
- General URL maintenance (new programs never scraped until added, closed/
  renamed programs scraped harmlessly but wastefully) — planned cadence:
  an early-season pass and a final end-of-season pass, per the onboarding
  checklist below. `team_scraping_status` rows with `games_found = 0` or
  `status = 'failed'` (not the permanently-`pending` duplicate-record rows,
  which are fix #15's problem, not this one) are the candidate list.

---

## Methodology tips

- **Finding a stored procedure's real current behavior**: `SELECT
  OBJECT_DEFINITION(OBJECT_ID('dbo.ProcName'))` pulls the actual live
  definition straight from SQL Server — faster and more reliable than
  trusting a doc that may be stale. This is how the v3 dedup-procedure
  fix and its real archive destination were confirmed.
- **Researching ambiguous historical team names/renamings**: a school's
  own official "History"/"About" page (often `<domain>/history`)
  frequently has an exact, dated rename timeline. Resolved the entire
  Trafton/Chapel Trafton ambiguity in one fetch after several rounds of
  guessing — try this before assuming a name discrepancy is a data
  error.
- **Cross-referencing repeat anchors across investigation numbers**: the
  same root cause can surface under multiple separate `InvestigationID`s
  for the same anchor team. Before treating two open investigations for
  the same team as separate problems, check whether they share one
  explanation.

---

## State onboarding checklist

Order used for the LA pilot, validated against the OK-derived workflow:

1. **Alias consolidation** — `consolidation_workflow.py` actions 1 then 2
   (see above).
2. **Ghost-team detection** — `mapping_conflict_audit.py detect --state XX`,
   then `dashboard` / `repeat-offenders` to see the shape of it before
   diving into the queue.
3. **Queue triage** — work repeat-offenders first; sample the
   Low-priority bucket across a few anchors before treating it as
   safe-to-defer at scale.
4. **Duplicate cleanup** —
   `EXEC dbo.RemoveDuplicateGamesParameterized @State = 'XX', @SeasonStart = 1877, @SeasonEnd = 2025;`
   (back up first — see Conventions above).
5. **Date-truncation check** — run the 4-script pipeline above for any
   state/season that flags in `diagnose_date_truncation.py`.
6. **Tier classification** — team-tier classifier +
   `detect-tier-mismatch`, with a fresh margin sample specific to the new
   state (rules tuned on OK data may not transfer directly).
7. **Level (6/8-man) mapping** — a state-association roster import script
   analogous to `ossaa_8man_import.py`, IF that state's governing
   association actually runs an 8-man division. **Confirm this before
   building anything** — don't assume every state has one just because OK
   does. Checked 2026-09-09: **LHSAA (Louisiana) has no 8-man division** —
   pulled LHSAA's full 2025-26 official football alignment (all schools,
   classes 5A-1A) directly from lhsaa.org and every school is standard
   11-man; only history is an unrealized 2014 proposal. So this step is
   N/A for LA. Any `LevelMismatch` investigations LA's `detect-level-mismatch`
   surfaces should mostly resolve as "no real mismatch, LA is just all
   11-man" rather than a genuine mapping gap needing a roster-import fix —
   the OK playbook doesn't transfer here. When triaging these: check which
   side is flagged 8-man first. Usually it's an out-of-state opponent (TX/MS
   programs with real 8-man history) playing a normal LA 11-man team — not
   an error. If the LA-side team itself is flagged 8-man, that's worth a
   closer look (rare small private/independent-association programs
   reportedly played reduced-roster ball historically, per informal
   research, unverified against a primary source) before assuming a real
   data error.
8. **Delivery package** (if sending to an external partner) — see
   `data_export\export_scores_loren_maxwell.py`,
   `export_names_loren_maxwell.py`,
   `export_investigation_report_loren_maxwell.py`, and the per-state cover
   note pattern in `J:\...\Shared_Loren_Maxwell\<State>\`.

---

*See `QUICK_GUIDE.md` for the earlier pipeline stage (raw newspaper scans →
imported into `HS_Scores`).*
