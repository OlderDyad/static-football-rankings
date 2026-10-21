# College Football Workflow

Last updated: October 20, 2026

Everything for the college database, ratings and weekly updates in one place. College uses the same SQL rating procedures as high school (`CalculateRankings_v4_Optimized`, league 2). All scripts live in `python_scripts/college/` unless noted, and run from that folder in the `.venv` PowerShell. Scripts that read SQL or the internet run on Windows.

General rules (same as HS): preview first, commit second; separate preview and commit steps; fixes by `Access_ID`; duplicates are moved to `College_Scores_Duplicates`, never just deleted; score conflicts follow default-and-flag (keep the older `Access_ID`, set `Score_Disputed = 1`).

---

## 0. Strategy and priorities (advisory -- start here in a new chat)

Where things stand (Oct 19, 2026): college data imported and cleaned (280k+ games), ratings converged (Run 6 avg change 0.67; Runs 7-9 only pick up data fixes), college site live (home, current season, all-time teams/programs, champions, programs, coaches, rivalries, greatest games), weekly Wolfe update automated, first newspaper season (1906 Lansing State Journal + Dayton Herald) imported and both target islands (Michigan St, Dayton) fixed.

**Guiding idea: data quality beats more runs.** The ratings have settled; what still moves them is wrong or missing games. Spend effort in this order:

1. **Keep the current season running (weekly, ~15 min).** Section 2. This is what visitors see.
2. **Find and fix wrong games before adding new ones (highest value per hour).** Each fix can move a whole season's ratings.
   - `game_residuals.py --min-games 5` after every full run: biggest misses first. Most top misses so far were *name collisions* (two schools sharing a name: Georgetown DC/KY, Pacific/OR, Union KY/NY/TN, California/Cal PA, Indiana/IUP, Notre Dame/JC, Illinois/Illinois College, Colorado/Colorado College, Mississippi/Mississippi College, Arkansas/Arkansas College, Northwestern/NW College, Trinity/Trinity CT, Loyola/LMU, Marshall/College of Marshall TX, Centre/Centre AL HS). Fix pattern: `split_name_collisions.py` (by rules) or `suspect_collisions.py` (by residuals) -> review CSV by opponent and season -> `apply_name_collisions.py --file ... --commit` -> duplicate check -> next full run.
   - Always review proposals by opponent *and season*: every rule set so far needed 3-10 exceptions (real intersectional games, rivalries, D-II playoffs, modern conference mates).
   - Remaining known suspects: section 4 "Still to do".
3. **Bridge islands with targeted newspaper seasons (proven on 1906).** Use `island_worklist.py` to pick seasons; work one paper across 5-10 consecutive seasons (same aliases, same map file, less review each season). Priorities:
   - Michigan/Ohio 1904-1910 (Lansing State Journal, Dayton Herald -- already set up; Michigan St, Albion, Alma, Dayton, Ohio colleges recur on the weak list)
   - Western Pennsylvania club era 1896-1900 (Pittsburgh paper; Duquesne hangs on Orange AC / Homestead AC)
   - Oregon 1899/1907 (Portland paper), North Dakota 1904/1909 (Fargo/Grand Forks), Colorado Mines 1918 (Denver), Purdue/Minnesota 1892 (Chicago/Minneapolis)
   - Skip: 1870s groups (Columbia/Stevens/NYU/Harvard) and segregation-era HBCU networks (Morgan St, Tuskegee, Hampton) -- structural islands, not missing data; the site notes explain them.
   Measure each season: island list before/after, then rerate that season. Stop a paper when new seasons add few cross-region games.
4. **Fill missing small-college schedules (`missing_games_audit.py`).** Record books / media guides first (one PDF can fill a program's whole history), newspapers for pre-1950. Do this after the island seasons; it matters most for small-college ratings and coach records.
5. **Coaches.** Fill recent gaps (2024-26 carousel pages), parse bullet-list Wikipedia pages, reload coach seasons after name fixes (coach seasons were loaded before the Union/Georgetown/Pacific/etc. renames).
6. **Site additions (when data work needs a break):** media/poll champions column, conference strength, cross-level comparison, upsets, streaks, bowl/playoff history.

**How Claude should work on this (for a new chat):**
- The session is linked to David's computer: use the device tools to read and write files in the repo folder (`python_scripts/college/`, `_AAA_Instructions/`), inspect CSV outputs and script code directly, and test scripts before handing them over. Don't ask David to paste file contents Claude can read itself, and don't guess column names -- check the loader/scripts (`College_Team_Names.Team_Name`, `College_Scores.Access_ID`, etc.).
- SQL Server is only reachable from David's Windows PC, so database work goes through scripts he runs. Prefer a Python script in `python_scripts/college/` with **preview by default and `--commit`** (writes a review CSV, prints counts, one transaction, rolls back on mismatch) over long ad-hoc SQL. Short read-only SQL checks are fine. When SQL fixes are needed, give **separate preview and commit scripts**, not one script with COMMIT/ROLLBACK choices.
- Reuse the existing tools (`split_name_collisions.py`, `suspect_collisions.py`, `apply_name_collisions.py`, `merge_same_school.py`, `newspaper_college_split.py`, `fix_newspaper_names.py`) -- add rules to them rather than writing one-off rename SQL.
- Check name-split rules against history before proposing them (e.g. Miami OH has played since 1888, Miami FL only since 1926; Union TN football ended 1952) and review proposals by opponent and season.
- Keep this doc current: update it (and the project copy) at the end of each work session.

**Full runs:** only after a batch of data fixes (not weekly). Run a full pass (alternate forward/backward), then `game_residuals.py --min-games 5`, `island_worklist.py`, `generate_college_site.py`, publish. One pass is enough now; the volatility check should show movers only where data changed.

**Rules that keep it clean:**
- Preview first, commit second; every script here works that way. Fixes by Access_ID.
- College table = any game where at least one team is a college (direct opponents only); HS table keeps HS games and copies of college-vs-HS games. (Moving college-vs-college games out of HS_Scores removes some early HS rating links; `--keep-hs` keeps them.)
- New college names go in `College_Team_Names`; newspaper names go in `newspaper_college_map.csv` (grows every season).
- After any rename: run the duplicate check for the new names.
- Weekly 2026 runs use `--no-snapshot` so convergence history only holds full runs.

---

## 1. Tables

| Table | What it holds |
|---|---|
| `College_Scores` | All games 1869-present (~280,000). Key columns: `ID`, `Access_ID`, `Season`, `Date`, `Home`, `Home_Score`, `Visitor`, `Visitor_Score`, `Neutral`, `Score_Disputed`. Aug 1 = date unknown (entered in playing order, so `Access_ID` order = game order). |
| `College_Scores_Duplicates` | Duplicate games moved out of `College_Scores` |
| `College_Rankings` | v4 output; `Combined_Rating` filled at the end of each run |
| `College_Rankings_Convergence_Master` | One snapshot per full run (`Snapshot_College_Convergence`), for volatility checks |
| `College_Team_Names` | One row per team: Kind (College / HS/Prep / Club / Military / JC / Academy / Freshmen), State, Division_History, HS link |
| `College_Team_Aliases`, `College_Name_Fixes`, `College_Dup_Actions` | Name-cleanup history from the Access import |
| `College_Division_Alignment` | Access division by school and years |
| `College_Coach_Seasons`, `College_Coaches` | Coach for each team-season (with `Coach_ID`), coach identities |
| View `College_Coach_Season_Records` | W-L-T per coach-season (NULL when two coaches shared a season) |
| `College_Future_Games` | Unplayed games of the current season from Wolfe's schedule page (Games of the Week source) |
| `College_Rankings_Access` | Old Access ratings, comparison only |
| `LeagueConfig` | League 2 = College_Scores / College_Rankings; `Seed_Window` (college 15, HS 2) |

Inclusion rule: a game belongs in `College_Scores` when at least one team is a college (any opponent a college played directly: athletic clubs, YMCAs, alumni, town and prep teams). Games between those non-college teams go to `HS_Scores`.

---

## 2. Weekly update (each Sunday after Wolfe's update)

1. Load scores and schedule from wolferatings.com:

   ```
   python wolfe_weekly.py                          (preview)
   python wolfe_weekly.py --commit --update-scores (load)
   ```

   - `scores.htm` -> `College_Scores`: NEW games inserted (Source 'Wolfe'), SAME skipped, CHANGED scores updated to Wolfe's with `--update-scores` (he corrects scores as reports come in). A location on the line = neutral site.
   - `schedules.htm` -> `College_Future_Games` (unplayed games only, refreshed each run; cancelled games marked).
   - Check the printed unknown team names (`wolfe_weekly/unknown_names.csv`): a new program or a spelling change needs a `College_Team_Names` row or a fix.
   - wolferatings.com is reachable only from the Windows PC.

2. Rate the current season at the current week:

   ```
   cd ..
   python run_full_rankings_recalc.py --league 2 --begin 2026 --end 2026 --week <week> --yes --no-snapshot
   ```

3. `python generate_college_site.py` (from `python_scripts/college`), then commit and push `docs/data/college` (and any page changes). Week number = the same week number the HS weekly run uses.

---

## 3. Full rating recalculation (history)

```
cd python_scripts
python run_full_rankings_recalc.py --league 2 --begin 1869 --end 2025 --week 52 --yes   (forward)
python run_full_rankings_recalc.py --league 2 --begin 2025 --end 1869 --week 52 --yes   (backward)
```

- Alternate forward and backward runs until settled. Each league-2 run ends with `Snapshot_College_Convergence` and prints the run number.
- Settled = average change well under 1 point and few team-seasons moving more than 5. Watch progress in `dbo.RankingsProcessLog`.
- Seeding: each season starts from the average of the surrounding seasons, +/- `LeagueConfig.Seed_Window` (15 for college). Detached clusters (regions that played no one else) keep the level of their seed, so they move as a block from run to run until the wide window settles them.
- `--no-snapshot` skips the convergence snapshot. Step 1 (ScoresWinLoss) is skipped for college; v4 reads games through `GetScores`.
- Runs so far: Run 1 2025 baseline; Run 2 forward (2026-10-16); Run 3 backward (avg change 0.73); Run 4 forward, first with Seed_Window 15 (avg 1.45, expected jump); Run 5 backward after the name fixes of 2026-10-17; Run 6 (avg change 0.67 -- settled); Runs 7-9 after data fixes (movement only where data changed). Add each run's direction, date and avg change here as it finishes.

Volatility query: compare the two latest snapshots in `College_Rankings_Convergence_Master` (HS query adapted, state/kind/games from `College_Team_Names`). Large uniform moves of a whole small group = a detached cluster, not instability.

---

## 4. Data-quality tools

| Script | Purpose | Changes data? |
|---|---|---|
| `island_worklist.py` | Weakly linked / detached clusters among top-25 team-seasons; one-opponent teams set aside (2-core); `Hangs_On` shows what a team's rating rests on. Outputs `island_worklist.csv`, `island_clusters.csv`. `--keep-leaves` = old counting. | No |
| `missing_games_audit.py` | Team-seasons with far fewer games than the team's nearby seasons or its division peers; gap seasons. Outputs `missing_games_by_team.csv` (record-book shopping list) and `missing_games_by_season.csv`. | No |
| `split_name_collisions.py` | Games filed under a name shared by two schools (California / California PA, Indiana / Indiana PA, Georgetown DC / Georgetown KY, Pacific / Pacific OR). `ROUND` picks the rule set; round 4 = bare names where every game belongs elsewhere (rules by school football years and opponent state, `ROUND4_BY_ID` overrides, `ROUND4_NEW_DATE` date fixes, unmatched games = CHECK; games already under the new name get `Dup_Of`) -> `name_collision_review.csv` | No |
| `apply_name_collisions.py` | Applies that review by `Access_ID`; `--skip "Opponent"`, `--include-weak`, `--commit`. Skips CHECK rows; `Dup_Of` rows go to `College_Scores_Duplicates` (Kept_Access_ID, Reason); `New_Date` fixes dates; new non-college names get their Kind from `NEW_KIND`. | Yes |
| `merge_same_school.py` | Merges two names for the same school without doubling games (DUPLICATE / CONFLICT / REVIEW / SELF / RENAME); `--old`, `--new`, `--commit` | Yes |
| `wolfe_weekly.py` | Weekly scores and schedule load | Yes (with `--commit`) |
| `suspect_collisions.py` | Big names shared with small colleges (Illinois/Illinois College etc.), found by result (big school lost far below its rating), modern schedule (FBS vs D-II/III/NAIA after 1950) or place -> `residual_collision_review.csv` for `apply_name_collisions.py --file`. | No |
| `newspaper_college_split.py` | Newspaper season in HS_Scores -> College_Scores (MOVE / COPY / skip existing); map file `newspaper_college_map.csv`. | Yes (with `--commit`) |
| `fix_newspaper_names.py` | Renames wrongly mapped newspaper rows, moves exposed duplicates, updates the map file. | Yes (with `--commit`) |
| `generate_college_site.py` | All college site data (`docs/data/college`). | Writes JSON only |
| `game_residuals.py` | Every game's actual margin vs the margin the two teams' ratings predict; worst misses first, ranked by Impact (rating points the game moves), with hints (scores swapped?, undated, far apart, few games, huge score). Best general tool for misnamed opponents (Centre AL vs Centre College, Notre Dame JC) and score typos. Output `game_residuals.csv`. | No |

Aug-1 outlier query (name collisions): a team with a fully dated season that has one Aug-1 game against an opponent whose season is all Aug-1 is a likely name collision (found Notre Dame / Minnesota-Crookston 1967-68 and the California, Indiana, Georgetown, Pacific mixes). Most hits are real games from undated small-school sources; judge by geography.

### Fixes done (2026-10-16/17)

- Bowl/post-season: 191 January games moved to the previous season; CFP dates fixed.
- Notre Dame vs Minnesota-Crookston 1967, 1968 -> 'Notre Dame JC' (Access_IDs 358913, 358978).
- SW Missouri St merged into Missouri St: 735 duplicates and 9 conflicts moved, 119 renamed.
- Name collisions: 531 games renamed (California PA 66, Indiana PA 67, Georgetown KY 240, Pacific OR 158). Kept with the main school: Cal-Pennsylvania, Cal-Wagner 2026, Indiana-Villanova/Fordham/Colgate/William & Mary. 6 resulting duplicates (Indiana PA-St Francis PA) moved.

- Round 2 (2026-10-18): Union KY -> Union NY / Union TN (to 1952), King's PA -> King TN (before 1946), Cumberlands KY -> Cumberland TN (to 1959), St Mary's MI -> St Mary's KY.
- Round 3 (2026-10-18, by residuals): 524 games to Arkansas College, Colorado College, Illinois College, Loyola Marymount, East Texas Baptist (College of Marshall), Mississippi College, Northwestern College / IA / MN, Trinity CT. Kept with the big school: Colorado-Mines before 1950, Marshall-College of Charleston 1913, Northwestern-Chicago 1899, Trinity TX-Centenary.
- 14 Arkansas schools had state AK -> AR.
- 2026-10-17: Jacksonville St 1920 opponents 'Centre' (2 games) and 'Ashland' were Alabama town teams -> 'Centre AL HS', 'Ashland AL HS'.
- 2026-10-20: 'Central St' was Central State (OH) entered a second time (1947-96). Three Anderson twins moved by hand (332094, 332212, 336662), then `merge_same_school.py --old "Central St" --new "Central St OH"`: 461 moved (456 duplicates + 5 conflicts, kept rows flagged Score_Disputed), 23 renamed (Southern, Saint Joseph's IN, Federal City, Salem WV, playoff games), 0 left. Kept conflict rows with a blank-as-0 score fixed: 133065 (1991 vs Central Arkansas) -> 16-19, 302595 (1992) -> 30-23, Margin recomputed.
- 2026-10-20: round 4 bare names (Anderson, Detroit MercyAC, Miami, Union) split -- see "Still to do" for details.
- 2026-10-20 (newspapers): MTSU-Miami FL 1931 (83838) -> 24-6, date Fri Nov 13 (Miami Herald Sat Nov 14; Miami played Fridays). Central St OH vs 'Indiana' 1994 (303018, 43-29) and 1995 (303026, 20-17) -> Indiana PA (Plain Dealer lists 'Indiana, Pa.'; the Hoosiers lost 62-13 at Wisconsin on 1994-09-24).
- Newspaper dates are the date reported, not played: a score in a Saturday-morning paper means a Friday (or earlier) game.
- 2026-10-20 name merges (`merge_same_school.py`): Southeast Missouri St -> SE Missouri St (1 dup, 2 renamed); Central Connecticut St -> Central Conn St (16 dups); Bridgewater St -> Bridgewater St MA (26 renamed; 2022 Southern Virginia game 426965 was Bridgewater VA, moved first); Clarke -> Clarke IA (62 renamed, no overlap); typos Florida Int'll (Camellia Bowl 2019) and Coloradod St (2021) merged. Old College_Team_Names rows (Bridgewater St, Clarke, etc.) now have no games -- refresh the game counts.
- 2026-10-21 round 5 (`split_name_collisions.py`, ROUND = 5; unmatched games STAY): 'Nichols' 1976-99 Southland games = 25 duplicates of Nicholls St rows, moved (rule stops at 2000: Nichols College's Bridgewater VA and Gallaudet games are real). 'Loyola' split by Access_ID against Wikipedia season schedules: 98 -> Loyola Marymount (+2 duplicate Hardin-Simmons rows 1938/1940 moved), 17 -> Loyola Baltimore (Northeast 1924-33), 15 -> Loyola Chicago (Midwest 1910-30), 95 New Orleans games (1912-39) stay as 'Loyola'; 16 CHECK left unchanged (Temple 1896-1908, Detroit 1896/1900, Denver 1907, Colorado Mines 1908-09, American Int'l/Hofstra 1950, Central Conn St 1952 -- perhaps Loyola Montreal, 1970-71 club games vs Duquesne/Case Western/Chicago).
- 2026-10-21 Loyola Marymount clean-up (round-3 leftovers): Cal Poly SLO 1922/1927 exact duplicates moved (346524, 347543; kept 176534, 241916); 1931 Santa Clara: 356643 = LMU 0-6 Nov 6 (LMU home), 356644 = Loyola New Orleans 7-13 Nov 26 at Loyola Stadium.
- Loyola follow-ups: score checks Baylor-LMU 1937 (29598: table 2-13, schedule Baylor 27-13 at Beaumont), South Dakota St-Loyola Chicago 1929 (325932: table 14-6, schedule 21-7), Texas Tech-Loyola NO 1936 (28979: 14-0 vs 13-0), Iowa St 1930 (25046: 13-7 vs 14-7); 'Birmingham' 1934 (262385) duplicates Birmingham-Southern (235790); state fixes Loyola Chicago MS -> IL, Centenary NJ -> LA.
- 2026-10-20 checked, no change: Anderson-Mt St Joseph 2019 (two real games: Sep 21 non-conference 34-7, Nov 9 conference 76-46); Anderson 78-43 Indianapolis 1969 (team averaged 45.5 points).

### Still to do

- Overlaps: Trinity vs Trinity TX (1913-2004), Lewis & Clark -> Lewis & Clark OR (2016), Cal Poly SLO 1970-71 (16-17 games; Cal Poly-Pomona mixed in?).
- Score checks from residuals: St Thomas MN 1956 (34-132, 2 games on file), Samford 1919 (15 games, two teams merged?), Cynthiana HS-Eastern Kentucky 1914, Oberlin-Mount Union 1994, Pacific OR-Willamette 1947 (one may be Pacific CA), Dayton 161-0 Central Michigan 1923, Henderson St 0-128 Hendrix 1919.
- Single games: Marshall-Stephen F. Austin 1923 (now East Texas Baptist -- check), St Mary's CA-Eastern Kentucky 1924, Clark Atlanta-Portland St 1950, Trinity-Doane 1921, Boston/Dartmouth-Manhattan 1985/87.
- Round 4 (committed 2026-10-20): `split_name_collisions.py` (ROUND = 4) -> `apply_name_collisions.py --commit`. 485 renamed, 13 duplicates moved (games already under the right name: Miami OH-Marshall x8, Union TN-Birmingham-Southern 1929/30, Anderson Training School-Sewanee 1910 (kept 329207), and the two 2026 rows below), 2 dates fixed, team name Detroit Independents (Club) added. Kept row 329207 still dated 1910-10-01 -> set to 1910-10-08. Next: duplicate check on the new names, then the next full run.
  - `Anderson` 1947-2022 -> Anderson IN (396); 1910 Sewanee game 14670 -> Anderson Training School (date -> Oct 8).
  - `Detroit MercyAC` -> `Detroit Athletic Club (MI)` (10; the name the 1906 newspaper split already uses, so DAC has one name); 1883 Michigan game 2431 -> Detroit Independents (new Club; date -> May 12; DAC founded 1887).
  - `Miami` -> Miami OH (Marshall 1933-57) / Miami FL (1929-32 Southern opponents, San Diego St 1978/89/91, Bethune-Cookman 2025); 2026 Central Michigan 445238 duplicates Wolfe's Miami FL row 900000001 -> moved.
  - `Union` -> Union NY (Middlebury, WPI), Union TN (Birmingham-Southern, North Alabama to 1952), Union KY (West Alabama 1995/97); 2026 Susquehanna 444329 duplicates Wolfe's Union NY row 900000000 -> moved.
  - The bare 2026 Miami/Union rows came from the Access data, not Wolfe (Wolfe uses Miami FL/OH, Union NY/KY), so the weekly load needs no change.
- Name fixes: all done 2026-10-20 (see Fixes done).
- From the 2026-10-21 run: 'Charleston Southern' 1906 (school founded 1964 -> College of Charleston?); Delaware Valley state DE -> PA; 'Nichols' vs Louisiana-Monroe 1996 -> Nicholls St; 'Loyola' (state LA) vs Johns Hopkins 1924 -> Loyola MD, Hofstra-Loyola 1950 to check; 'Washington U.' state WA (is Washington U. in St. Louis, MO); Mississippi College-Hardin-Simmons 1958 (round-3 move to check); Dayton 1906 still moves as a block.
  - Note: `College_Scores.Margin` is a stored column -- any score fix must also set `Margin = Home_Score - Visitor_Score`.
- Refresh `College_Team_Names` game counts and seasons (stale after the merges).
- Scores to check: Cincinnati-Miami OH 1906 (paper 6-0, table 0-0); M.A.C.-Kalamazoo 1906 date (paper Oct 13, table Oct 20).

---

## 5. Filling gaps (bridging islands, missing games)

- Bridging games matter most: a game that links a weakly connected cluster to the main network (e.g. Notre Dame-Hillsdale 1906 for the Michigan cluster, Ohio State-Wittenberg 1906 for Dayton). Games inside a cluster do not move its level.
- Rough guide: 1 link = cluster level uncertain by ~15 points, 4 links ~7, 9 links ~5.
- Sources: school record books / media guides (D-II, D-III, NAIA, all eras); Monday newspaper score lists for pre-1950 (pilot: Lansing State Journal + Dayton Herald, every Monday Sep-Nov 1906); d2football.com / d3football.com for recent seasons.
- Load college games only, tagged with Source, through the name matcher; flag conflicts, don't overwrite. Then rerun `island_worklist.py` for that season and compare link counts.
- Structural islands (NESCAC conference-only schedules, segregation-era HBCU networks, 1870s) have no missing games to find; note them on the site.

---

## 5b. Newspaper seasons -> both tables (routine, proven on 1906)

1. Usual HS newspaper workflow: `custom_extractor_prepper.py`, `master_scores_importer.py`, name-correction loop (`apply_corrections.py`, Gemini resolver, `autofill_from_ai.py`, `flag_unresolved_as_ignore.py`, importer again), `batch_queue_manager.py` (option 2 -> note the BatchID), HS duplicate removal for the states involved. College names must be standardized to the HS convention ("University of Michigan (MI)", "Albion College (MI)") -- colleges left unresolved are not split out.
2. Baseline: `python island_worklist.py` (only reads College_Scores; fine to run any time before the commit).
3. `python newspaper_college_split.py --season <year> --batch <id>` (preview). Review `newspaper_split/newspaper_college_names.csv`; put decisions in `newspaper_college_map.csv` (HS_Name, College_Name; `HS` = not a college). Rerun until 0 REVIEW. Check CONFLICT games (usually OCR misreads in the paper: dropped/added digits, 0 read as 4 or 5).
4. `python newspaper_college_split.py --season <year> --batch <id> --commit --fix-dates` (MOVE both-college games, COPY one-college games, skip existing, fill Aug-1 dates; deletes use the Season index).
5. Check the season's top 25 for names that slipped through (a school appearing twice under two names). Fix with `fix_newspaper_names.py --season <year>` (edit its RENAMES list), preview, commit -- it renames newspaper rows, moves the exposed duplicates, cleans team names and updates the map file.
6. `python island_worklist.py` (compare), rerate the season for college (`--league 2 --begin <year> --end <year> --week 52 --yes --no-snapshot`) and for HS.

1906 result: ~600 newspaper lines -> 122 new college games (after 26 duplicates exposed by name fixes), 128 existing games confirmed, 11 dates filled; Michigan St (1 link) and Dayton (hung on Wittenberg) left the weak list. Names that needed explicit mapping: US Military/Naval Academy -> Army/Navy (the "Academy" rule treats them as prep), Carlisle Indians -> Carlisle Indian School, Washington & Jefferson College -> Wash & Jeff, Cornell University (NY) -> Cornell NY, Case School -> Case Western Reserve, Western Reserve University -> Western Reserve (new college).

## 6. Coaches

Goal: a coach for every team-season at every level, to rate coaches by program rating before / during / after (value added) and by straight average (min 10 seasons).

Build order: `build_coach_seasons.py` (Access tenures) -> `fetch_current_coaches.py` + `build_current_coach_fill.py` (Wikipedia current lists) -> `fetch_program_coach_history.py` (per-program Wikipedia tables; resumable, `--fresh`) -> `build_coach_seasons_combined.py` -> `build_coach_ids.py` -> load with `load_access_export.py coachseasons coaches`.

Status: 47,481 coach-seasons, 7,665 coach IDs. Coverage of team-seasons: FBS 97-100%, FCS 67-95%, D-II ~50%, D-III 38-61%, NAIA 24-51%. Next: bullet-list coach pages, carousel pages for 2024-26 changes (collegefootballpoll.com, FootballScoop, d2football.com, d3football.com), two-coach seasons, coach ratings after convergence.

---

## 7. College site

Pages (static, in `docs/pages/public/college/`): `index.html` (College home: links, top 10, recent champions), `current-season.html`, `all-time-teams.html`, `all-time-programs.html`, `national-champions.html`, `programs.html` (search list), `program.html?team=<slug>` (one page serves every program: season-by-season ratings, record, coach, and each season's games). Shared script `docs/js/college/college.js` (search, filters, sorting, paging). Linked from the HS home page ("College Football" card).

Data: `python generate_college_site.py` writes `docs/data/college/` (current-season, all-time-teams, all-time-programs, national-champions, programs-index JSON, plus `programs/<slug>.json` per program). Run it after every full rating run and after the weekly 2026 run, then commit and publish. `--no-games` leaves game lists out of the program files; `--top-teams N` sets the all-time list length (default 2000).

Rules: season ranks count only Kind = College teams with games >= max(5, 60% of a full schedule), a full schedule being the 75th percentile of college teams' games that season (capped at that, for the 1870s). A Note (from `island_worklist.csv`; run `island_worklist.py` first) marks detached, weakly linked (3 or fewer connecting games) or one-opponent seasons. Program files are rewritten only when they change. McKnight's champion = highest rating each season, with runner-up and gap. Programs list = 10+ ranked seasons (page filter defaults to 25). Levels come from `Division_History` (1A = FBS, 1AA = FCS, II, III, NAIA; before 1937 "College").

Coaches (added 2026-10-18): `coaches.html` (all head coaches; Avg Rating and Value Added, min 10 rated seasons by default) and `coach.html?id=<Coach_ID>` (tenures with before/after baselines, season by season). Coach names link from program, current-season, all-time and champion pages. Data: `coaches-index.json` + `coaches/<Coach_ID>.json`, written by `generate_college_site.py`. Avg Rating = mean rating of seasons as sole head coach in completed, ranked seasons. Value Added = per tenure, school's average under him minus its average in the 5 ranked seasons before and 5 after (other coaches); career = season-weighted mean of tenures with a 2+ season baseline. Titles = seasons his team finished #1.

Greatest Rivalries and Greatest Games (added 2026-10-19): the HS method with an era-neutral quality measure. A game counts when both teams are in the top 25% of that season's ranked college teams (and average top-30% over that season and the 4 before, 2+ seasons) and the margin is 8 or less. Game score = average of the two season percentiles (100 = #1) x closeness (1 pt 1.00, 2-3 0.90, tie 0.85, 4-7 0.75, 8 0.60). Rivalries: pairs with 5+ counted games, ranked by total, top 100, with all-time series (`greatest-rivalries.json`). Games: all counted games, best first, top 1000, with ranks and a post-season flag (after Dec 7) (`greatest-games.json`). Thresholds are constants RIV_* / GAMES_TOP at the bottom of `generate_college_site.py`.

Games of the Week (added 2026-10-21, recalibrated same day): `games-of-the-week.html`, data `upcoming-games.json` written by `generate_college_site.py` from `College_Future_Games` for today + 6 days (`--gow-start`, `--gow-days`). Game Index = average team quality x closeness. Quality = 100 x (1 - ln(rank)/ln(N)) -- log rank, so the top of the table spreads out (a percentile version put Miami OH-Central Michigan, #113 v #123, at #2). Closeness = 1 - projected margin/30, games over 10 points dropped. All list = national rank (top 40); level tabs (FBS, FCS, D-II, D-III, NAIA) = same-level games ranked by rank within the level (top 15 each). Home field measured each run from 2004-25 college-vs-college games (2.3 pts), none at neutral sites. Constants GOW_* in the script -- calibrate against David's sense of the week's best games (first check, week of 10/21: Houston-Utah, Ole Miss-Texas = top 2). Run the generator after Sunday's weekly update.

Still to come: media champions column, conference strength, cross-level comparison, upsets, streaks, bowl and playoff history.

## 8. One-time import (done, for reference)

The Access database (`CFB 2023_09_03.accdb`, 32-bit, no ODBC driver) was read with `access-parser`, exported to `access_export/` (git-ignored), loaded with `load_access_export.py`, names cleaned (`build_name_fixes.py`, `split_ambiguous_names.py`, `find_duplicates.py`, `build_dup_actions.py`), teams built (`build_team_profile.py`, `match_hs_names.py`, `build_team_names.py`), then moved into `College_Scores` (280,222 games). No further Access imports: Wolfe's pages replace the weekly Access update.
