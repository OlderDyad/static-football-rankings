# HS / College Name Detangling

Started 2026-10-29. Purpose: find and fix games where a COLLEGE team and a HIGH SCHOOL team share a name
(e.g. "Saint Louis University (MO)" = SLUH the high school, and Saint Louis University the college), so that
games are filed under the wrong team in HS_Scores and/or College_Scores. Secondary goal: once clean, use the
teams rated in BOTH systems to measure (and later anchor) the offset between the college and HS rating scales.

Rules (same as the college workflow): preview first, commit second; scripts in python_scripts/ (preview by
default, --commit to apply); fixes by Access_ID / ID; never just delete -- move to the Duplicates table with a
reason; SQL is given in the chat for copy/paste. College and HS rating runs must never overlap.

## 1. How the two systems are linked

- `College_Team_Names.HS_Team_Name` = the name the college has in the HS tables (HS_Scores / HS_Rankings).
- Routing rule: a game goes to College_Scores when at least one team is a college varsity, and to HS_Scores
  when at least one team is a high school varsity; college vs HS = both tables.
- Rating tables: `College_Rankings` and `HS_Rankings` (Season, Week, Home, Avg_Of_Avg_Of_Home_Modified_Score;
  final week = MAX(Week) per season).

## 2. The measurement that started this (2026-10-29)

gap = college rating - HS rating, for every college rated in both tables in the same season.
Because each table's zero is its own average team, the gap measures the distance between the two scales.

Result by era (before any cleaning): 1894-1910 about -15 to -35; 1911-1919 about -41 to -47 (a real ~15-point
shift, 15-22 teams per year); 1920-1990 about -5 to -20 (mean about -13); sd about 25 throughout.

Query (season summary; add `ORDER BY` / filters as needed):

```sql
WITH c AS (
  SELECT r.Season, r.Home AS College, n.HS_Team_Name, r.Avg_Of_Avg_Of_Home_Modified_Score AS College_Rating
  FROM dbo.College_Rankings r
  JOIN (SELECT Season, MAX(Week) AS W FROM dbo.College_Rankings GROUP BY Season) w ON w.Season = r.Season AND w.W = r.Week
  JOIN dbo.College_Team_Names n ON n.Team_Name = r.Home
  WHERE n.HS_Team_Name IS NOT NULL AND n.Kind = 'College'),
h AS (
  SELECT r.Season, r.Home AS HS_Name, r.Avg_Of_Avg_Of_Home_Modified_Score AS HS_Rating
  FROM dbo.HS_Rankings r
  JOIN (SELECT Season, MAX(Week) AS W FROM dbo.HS_Rankings GROUP BY Season) w ON w.Season = r.Season AND w.W = r.Week)
SELECT c.Season, COUNT(*) AS teams_in_both,
       CAST(AVG(c.College_Rating - h.HS_Rating) AS decimal(6,1)) AS avg_gap,
       CAST(STDEV(c.College_Rating - h.HS_Rating) AS decimal(6,1)) AS sd_gap
FROM c JOIN h ON h.Season = c.Season AND h.HS_Name = c.HS_Team_Name
GROUP BY c.Season ORDER BY c.Season;
```

## 3. Known / suspected collisions (from the outlier list, 2026-10-29)

Same-name HIGH SCHOOLS (the HS table's team is a different school):
- Saint Louis University (MO) -- SLUH (St. Louis University High School). Fix: rename the HS team (add "High").
- Memphis University (TN) -- Memphis University School (MUS), a high school. 1916, 1917, 1962, 2003, 2024-26 rows.
- Boston College (MA) -- Boston College High School. 2024-26 rows (+31 to +68 gap).
- Likely the same pattern in other university towns: check Temple University (PA) (Temple's prep / HS
  department, 1904-1932 rows swing both ways), Loyola College (LA) (1923), Jefferson College (LA) (1920),
  Pittsburgh College (PA) (1908: in the newspaper map "Pittsburgh College" = Pitt; Pittsburgh Catholic
  College = Duquesne -- check), York University (NE), Spokane University (WA), Marquette University (WI) (1931).

College JV / B teams in the HS table under the varsity name (gap steady about -30, 2003-2010):
- Rowan, The College of New Jersey, Montclair St, Kean, William Paterson, La Salle, Muhlenberg, Buffalo St,
  Morrisville St. The HS table's games are probably the colleges' JV schedules against high schools / prep
  schools; they should sit under "<College> JV", not the varsity name.

Single teams with |gap - season average| > 60 (1903-1958): about 90 rows; each is either a collision, a
mis-filed game, or a college whose HS-side rating rests on 1-2 games. List with the outlier query (section 2
query + `ABS(gap - season_avg) > 60`).

## 4. Proposed workflow

1. Inventory: every HS_Team_Name that is ALSO used by a team playing a mostly-HS schedule (opponent Kind mix
   by season) -> candidate collisions. Start with the list in section 3.
2. Per name: list its HS_Scores games by season with opponents; decide by opponent type / era which games are
   the college and which the high school (as done for Wayne St, Trinity, Bethel in College_Scores).
3. Move whichever side has FEWER games. Usually that is the college: the HS name is locked
   (trg_LockTeamIdentity), carries the school's MaxPreps link/metadata, and MaxPreps keeps writing to it.
   College-vs-college rows leave HS_Scores (archived as duplicates of the College_Scores row, or copied
   first if missing); college-vs-HS rows are renamed to the college's own HS name ("<School> College (ST)")
   and copied to College_Scores if missing. Move college JV games to "<College> JV".
4. Re-run the gap query; then weight by games on the HS side and fit an era offset.
5. Decide on anchoring: simple era offset, seeding thin early college seasons from the HS scale, or a joint
   1890-1925 rating run.

## 5. Tool

`python_scripts/college/hs_college_detangle.py` + a plan CSV (one row per HS_Scores game, by HS_Scores.ID):
Action DUP (archive to HS_Scores_Duplicate_Archive with KeptID = College_Scores.ID, change log, delete;
Dispute=1 sets College_Scores.Score_Disputed), RENAME, RENAME+COPY (also inserts into College_Scores),
CHECK (listed only). `--link "College=HS name"` sets College_Team_Names.HS_Team_Name. Preview by default,
`--commit` = one transaction with count checks. Every name also needs: newspaper_college_map.csv line(s)
(map is GLOBAL -- the HS school -> `HS`, the new college HS name -> college name) and a row in
excel_files/State_Aliases_ProperNames/<ST>_Alias_Rules.csv (then consolidation_workflow_latin.py).

## 6. Log

### Saint Louis University (MO) -- 2026-10-29
- HS name `Saint Louis University (MO)` (HS_Team_Names ID 67710) = SLUH, 1899-2023, ~1,000 games: STAYS.
- College HS name: `Saint Louis University College (MO)` (College_Team_Names `St Louis`; old link
  `St louis (MO)` had 0 games). SLU college football ended after 1949.
- Plan `hs_college_detangle_plan.csv`: 14 DUP (1934 IWU, 1939/40/41 Drake, 1940 Mines, 1945 IWU, 1947
  Marquette x2 [filed as Alton Marquette Catholic and Milwaukee Marquette University High], 1947 Drake
  [paper 41-13 vs 41-12 -> Score_Disputed], 1947 Detroit, 1948/49 Wichita, 1949 Davidson, 1949 Duquesne);
  RENAME 1906 Mexico Military Academy (already in College_Scores 900000357); RENAME+COPY 1899 Western
  Military Academy 17-5 (David: college); CHECK 1932 "Loyola Chicago 19-6" Oct 22 (Loyola Chicago had no
  team after 1930; College_Scores has Loyola NO 19-0 Nov 5).
- Map: `Saint Louis University (MO)` -> HS; `Saint Louis University College (MO)` -> St Louis.
  MO alias rule added for the college name. `St. Louis University (MO)` still aliases to SLUH -- pre-1950
  newspaper imports need review for college scores (both schools print as "St. Louis U.").
- Status: COMMITTED 2026-10-29 (zero-row check clean). Still to do: HS rerate 1899, 1906, 1934,
  1939-41, 1945, 1947-49; college rerate 1899 (and 1947 for the flag only). Never overlap the runs.
- Left for later: 1945 SLU-Illinois Wesleyan date (paper Oct 6, College_Scores Oct 20); College_Scores
  900008147 (Mines 0-32, 1945-10-23) duplicates 33907 (Oct 6); `Saint Louis University Fresh (MO)` 1914-21
  (4 games, SLU or SLUH freshmen?); `Saint Louis University City (MO)` 2021-26 (44 games) = University City HS?
- SLUH's own duplicates (HS dedup, not this workstream): 1942 CBC 13-7 / 27-0; 1950 Decatur (IL)/(MO)/no
  state; 1951-52 Decatur (MO) copies; 1965/1967 Saint Louis Assumption vs East St. Louis Assumption; 1971
  nearly every game twice; 1977 Jefferson City x3; 1982 McCluer x3.

### Memphis University (TN) -- 2026-10-29
- `Memphis University (TN)` (ID 36346) = Memphis University School (MUS), all HS opponents 1900-2026: no
  college games in HS_Scores. Problem was the LINK: College_Team_Names `Memphis`.HS_Team_Name pointed at it
  (-> the 2024-26 +41..+52 gap outliers). New college HS name: `University of Memphis (TN)`; also link
  College_Team_Names `Memphis University School` (HS/Prep) -> `Memphis University School (TN)`.
- newspaper_college_map.csv: `Memphis University (TN)` -> HS (was -> Memphis, from batch 195 on 2026-10-23);
  `University of Memphis (TN)` -> Memphis. College_Scores 'Memphis' 1907-09/1950/52/71 checked: all Access
  rows, nothing from the newspaper split -> no College_Scores cleanup.
- MUS is split: `Memphis University (TN)` 1900-2003 + 2024-26 (MaxPreps), `Memphis University School (TN)`
  (ID 42629) 2004-23 (MaxPreps) + scattered older rows. Overlap seasons 1923, 1957-68, 1999 -> duplicates
  expected. David 2026-10-29: merge INTO `Memphis University School (TN)` (TN_Alias_Rules.csv edited;
  MaxPreps row HS_Team_MaxPreps 9059 -> Team_ID 42629). Paper dates trail hsfdatabase dates by 2-4 weeks,
  so the v4 dedup (10 days) misses them: 31 exact duplicates archived by ID first with
  `hs_college_detangle.py --plan hs_college_detangle_plan_memphis.csv` (new action HSDUP, Keep_HS_ID).
  DONE 2026-10-29: 31 archived; MaxPreps 9059 -> 42629; consolidation run, 0 rows left under old name,
  only 1990 >13 games (16, real). Remaining: HS rerate 1957-68, 1999, 2024-26; the 7 conflicts below.
- MUS conflicts to check (both rows kept for now): 1960 FBA 0-28 / 0-27; 1960 Whitehaven 13-0 (10/14) +
  13-6 (10/28) vs paper 13-0 (10/29); 1963 Oakhaven 13-9 / 13-0; 1963 Collierville 27-7 / 27-6; 1965
  Whitehaven 7-7 / 9-7; 1965 Westwood 13-32 / 32-13; 1968 Bartlett 35-0 / 35-6.
- TN alias leftovers seen here: `Millington (TN)` (136, unresolved) = Millington Central; `Bolivar` (no
  state) 1967 = Bolivar Central; `Nashville East (TN)` 1966 7-0 in a Knoxville paper = Memphis East;
  `Memphis Mitchell` + `Mitchell Road` 1968 54-20 same game. NEW COLLISION SUSPECT: `Sewanee (TN)` (50
  games, unresolved) -- Sewanee Military Academy vs the University of the South.

### Boston College (MA) -- 2026-10-29
- Reverse of Memphis: the college keeps `Boston College (MA)` (ID 3488; College_Team_Names link already
  correct). BC High = `Boston College High (MA)` (ID 1663). MaxPreps link HS_Team_MaxPreps for BC High was
  on 3488, so 2024-26 MaxPreps games landed under the college name (-> 2024-26 gap outliers).
- Plan `hs_college_detangle_plan_bc.csv`: 3 DUP (1949 Wake Forest 36233, 1952 Drake 38153, 1963 Detroit
  43747 -- all in College_Scores from Access); 28 RENAME -> Boston College High (MA): 27 MaxPreps 2024-26
  (no overlap with BC High rows) + 1960 Miami Senior (FL) 10-7. MaxPreps row -> Team_ID 1663.
- Map: added `Boston College High (MA)` -> HS.
- DONE 2026-10-29: plan committed (3 archived, 28 renamed), 0 HS games left under `Boston College (MA)`,
  MaxPreps row 1497 -> Team_ID 1663. Remaining: HS rerate 1949, 1952, 1960, 1963, 2024-26.

## 7. Next up
- College JV schedules filed under the varsity name, 2003-10 (Rowan, TCNJ, Montclair St, Kean, William
  Paterson, La Salle, Muhlenberg, Buffalo St) -> rename to `<College> JV (ST)`.
- Early-era suspects: Temple (prep dept), Loyola College (LA), Jefferson College (LA), Pittsburgh College,
  Spokane University, York University (NE), Marquette 1931; `Sewanee (TN)`.

### TCNJ / NJAC -30 gap -- Saylor phantom games (2026-10-29)
- The steady -30 for Rowan, Montclair St, Kean, William Paterson, La Salle, Muhlenberg, Buffalo St 2003-10
  is NOT college JV: each has one HS_Scores game a year, all vs `The College of New Jersey (NJ)`, so they
  inherit TCNJ's HS-side level. TCNJ's HS anchor was a phantom: Saylor sheet layout = one row per season,
  3 columns per opponent (W/L/T, PF, PA), last 4 columns = season W, L, T, Rate. On two sheets the season
  W-L was imported as a game vs the last opponent block:
  - saylor/id/5401 Peddie "vs TCNJ" 1886-2004 (123 rows; 120 phantom, real: 1922 6-6, 1926 14-12, 1927 6-6)
  - saylor/id/4319 North Hills "vs Fairfield (OH)" 1937-2003 (68 rows; 67 phantom, real: 1989 25-6)
  Kearny sheet (5097) checked: not affected. Pair scan found no other post-1912 runs (pre-1912 4/5 scores
  are normal: TD = 5 points 1898-1911).
- Plan `hs_college_detangle_plan_saylor.csv`: 187 JUNK (new action: archived, KeptID = own ID).
  COMMITTED 2026-10-29 (4 real games left, as planned). Next: full HS historical run, then gap query.
- TCNJ other leftovers: Saylor 5613/5388 college opponents filed as HS names -- `Union (NJ)` 1999-2001
  (Union College NY?), `Jersey City Lincoln (NJ)` 1958-59 (Jersey City St?), `West Orange Seton Hall Prep
  (NJ)` 1975-80 (Seton Hall Univ club?), `Franklin Lakes Ramapo (NJ)` 1980-92 (Ramapo College),
  `Bordentown Reform School (NJ)` 1955; bad state codes: Central Connecticut (NY), Southern Virginia (NJ),
  Merchant Marine (MD), Coast Guard (NJ), Army JV (PA).

## 8. Re-rate plan (2026-10-29)
`python_scripts/run_hs_rerate_nights.ps1 -List` shows the nights; `-Night N` runs one (stops on first
failure, log `hs_rerate_nights.log`). Nights 1-5 = seasons with real changes (MUS 1957-68 + 2024-25, SLU,
BC, college 1899); nights 6-21 = remaining Saylor-phantom seasons 1886-2004 (skip if a full historical HS
run is planned). Never overlap with the daily college run, the Sunday college run or the Wednesday HS run.
