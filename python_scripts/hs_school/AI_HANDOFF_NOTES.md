# AI Handoff Notes (Claude <-> Gemini) — HS data cleanup

David switches between Claude and Gemini when one chat hits its weekly limit.
Whoever picks up: read this file first, then append a dated entry at the bottom when you stop.
Full history and per-state notes: Claude project doc `claude/HS_Data_Quality_Plan.md` (David can paste it if needed).

## Standing rules (David's decisions — please follow)
- **Co-ops split by year.** Use the co-op name (e.g. "Holbrook-Avon (MA)") for co-op seasons, the school name otherwise.
  Do NOT write alias rules that merge a co-op name into a single school. Use `move-team ... --seasons A-B` instead.
- **Replacement schools are separate.** A regional or new school that replaced an older town school gets its own name from its opening year
  (e.g. Whitman (MA) 1900-1959, Whitman-Hanson Regional (MA) 1960+).
- **Renamed, continuous schools** carry the current name for their whole history (e.g. Forrest -> Westside).
- **City names spelled out**, no abbreviations ("Saint Petersburg", not "St. Petersburg"). Insert any new name into HS_Team_Names first.
- Archive bad rows, never just delete; every change must be logged (hs_cleanup.py does this).
- Refer to commands and scripts by name, not step numbers. Put any SQL for David in the chat for copy/paste.
- Check in with David before moving to the next state; otherwise work on your own and only ask about big or unclear questions.

## hs_cleanup.py gotchas
- Jobs are `_jobs\NN_name.job` (one command per line), run by `python hs_cleanup.py watch`; logs go to `_jobs\done\NN_name.log`.
  Files in `_jobs\pending\` are NOT run.
- The watcher picks up a job within ~5 s, so **edit the rules file BEFORE writing the job**.
- `consolidate ST` **requires `--reason "..."`**; without it the job stops (exit 2) and every later line is skipped.
- Quote multi-word arguments: `step NH 3.1 "in progress" "note"` (an unquoted `in progress` fails).
- Before any consolidate, check `<ST>_Alias_Rules.csv` for chains (A->B, B->C) and cycles (A->B, B->A).
  A cycle flipped about 3,000 FL games once.
- `--ids` takes a file name relative to the state folder, not an absolute path.
- move-team output CSVs are timestamped to the minute, so several moves in one minute overwrite each other.
  Use HS_Scores_Change_Log to review them.
- college_check matches on score only. Archive a college copy only when the team names match too.

## 2026-11-10 — Claude: review of Gemini's FL / MA / CT / NH / RI work (jobs 39-64)
Most of the work was good: FL Saint Petersburg, MA remaps, moves and archives, and the CT/NH/RI remaps and moves all checked out.
Two problems, now fixed:
1. **Co-op merges in the alias rules.** The MA/CT/NH/RI rules merged co-op names into single schools.
   - Rules set back to identity (backups in `_claude_backup_2026-11-10\`).
   - MA co-op seasons moved back (job 66): Holbrook-Avon 1998-2020, Manchester Essex-Rockport 1997-2020, Ayer Shirley-Bromfield 2017-20,
     Maynard-Bromfield 2011-16, Millis-Hopedale 2010-18, Palmer-Monson 2016-23, Sutton-Douglas 2013-20, Worcester Holy Name-St. Mary's 2004-15,
     West Roxbury-Urban Science Academy 2013-18, Brighton-Green Academy-Lyon Pilot 2013-20, Dorchester Burke-Community Academy 2013-16,
     Commerce-Springfield Renaissance 2013-19, Springfield Renaissance-Commerce 2021, Drury-Mount Greylock 2019-24,
     Hatfield Smith Academy-Smith Vo-Tech 2013-20, West Boylston (MA) 1970-2003 (out of West Boylston-Tahanto).
   - 3 co-op URLs remapped: Drury-Mount Greylock (MA), Griswold-Wheeler (CT), Central Falls-Blackstone Valley Prep-Achievement First (RI).
2. **Job 62 failed at `consolidate MA`** (no `--reason`), so CT/NH/RI were never consolidated. Claude ran it 2026-11-10 (jobs 66-75). Archived:

   | | dedup | review pairs | same-score | college |
   |---|---|---|---|---|
   | CT | 450 | 198 | 326 | 2 |
   | NH | 178 | 57 | 19 | 0 |
   | RI | 62 | 35 | 20 | 1 |
   | MA (extra) | 131 | 42 | 2 | 0 |

Also on 2026-11-10:
- **Whitman split:** 239 games 1900-1959 moved from Whitman-Hanson Regional (MA) to Whitman (MA); the MA rule is now identity (job 78).
- **NH season fix:** the Andover-Exeter 1882-11-08 game had Season 1982; David fixed it by SQL.
- **2-0 games:** CT 4, NH 2, RI 1 have no forfeit flag. Left as-is; they may be real safeties.
- Tracker steps are updated for MA/CT/NH/RI (`status ST` shows them).

Still open in New England (David's call):
- Yarmouth is merged into Dennis-Yarmouth; split it if a pre-regional year is found.
- The Hartford Sports & Medical Sciences co-op URL is mapped to the school name.
- About 185 same-score pairs are undecided.
- New England needs a re-rate.

Also open, older:
- FL "St." cities: St. Augustine, St. Cloud, St. Leo, St. Lucie West.
- FL importer "St" bug names: Strawberry Crest, Victory Charter, Rickards.
- Undecided same-score pairs in KS, AZ, MO and FL.
- Re-rate batch 2.

Next state on the road map: **NC**, then OK, TN, OR, IA, then OH, MI, IL. Ask David before starting it.

<!-- Append new entries below: "## YYYY-MM-DD — <AI name>: <what you did / what is open>" -->

## 2026-11-10 — Claude: Tennessee started (jobs 79-91)
- TN was already deduped (dedup only 7-12 rows). The mess is names and dates, not copies.
- **2024 MaxPreps import made short/mascot names.** Examples: Watertown Purple, Coalfield Yellow, Jackson North, Nashville Overton, Greeneville Greene, Knoxville Tennessee School (= TSD), Nashville Tennessee (= Tennessee Heat).
  21 rules were added to `TN_Alias_Rules.csv` (backup in `_claude_backup_2026-11-10\`), and 23 URLs were remapped. mapcheck fixed 7.
  The same importer bug shows in other states' deaf schools ("Faribault Minnesota St. ate", "Talladega Alabama School"), so it needs a national check later.
- Memphis B.T. Washington / Booker T → Memphis Washington (TN).
- **Halls three-way split, by opponent geography** (HS_Team_Names Latitude/Longitude; script in the device VM `~/tn/halls3.py`):
  - Knoxville Halls → Halls (TN) (Lauderdale Co., West TN): 518 games.
  - Knoxville Halls → Harlan Grays Knob Hall (KY): 66 games. Halls (TN) → Harlan Grays Knob Hall (KY): 65 games. These are Harlan-area KY league games, ≤1963.
  - Halls (TN) → Knoxville Halls: 4 games.
- Geocodes caution: many teams share a city-centroid fallback (for example lon -87.624421 = Chicago, -86.774298 = Nashville). Treat any coordinate shared by 4 or more teams as unknown.
- **Double-booked days:** about 12,700 pairs, about 75% hsfdatabase.com/tennessee. Its dates are estimated Fridays, so both games are usually real.
  Open question for David: treat hsfdatabase as an estimated-date source.
- Open: same-score preview has 960 pairs; rerun it after the moves before committing.
  Memphis Academy of Science & Engineering URL is mapped to Memphis Academy of Health Sciences (different schools?).

## 2026-11-10 (later) — Claude: Tennessee vs HSFHA-TN (hsfha.org), jobs 92-103
- David and Loren (hsfha.org) have a data-sharing agreement.
- **The pull:** all 729 TN schools from the hsfha.org games API, in the in-app browser (plain HTTP gets a 403 from Cloudflare).
  Saved as `TN\hsfha_TN_games.csv` (154,407 games) and `TN\hsfha_TN_schools.csv`.
  The match scripts live in the device VM at `~/tn/` (hsfha_map.py, hsfha_match.py, hsfha_names.py, aliases.py, plan.py/plan2.py, dates.py). They are not in the repo.
- **Match method:** season + score pair (oriented) + date within ±10 days.
  - Each HSFHA school code is mapped to our name by votes (`TN\hsfha_code_map.csv`).
  - A one-side match (only one team's name agrees) marks the other name as wrong for that game.
- **hs_cleanup.py changes:**
  - hsfdatabase is now an estimated-date source.
  - New command: `set-dates ST --file <ID,NewDate,Note csv> --reason ... [--commit]`. It logs to HS_Scores_Change_Log.
- **Applied:**
  - 40 per-game move lists (`TN\hsfha_mv_NN.csv`, about 1,300 games). Examples: Nashville/Knoxville West, East and Central; Chattanooga/Nashville Howard; Chapel Hill (NC) → Chapel Hill Forrest; Dayton (KY) → Rhea Central; Fulton City (KY) → Knoxville Fulton; Tennessee Industrial School vs TMI.
  - 75 alias rules, including Harrison-Chilhowee → King's Academy, Southern Baptist → Southaven Northpoint Christian (MS), and Tennessee Industrial School → Tennessee Preparatory School.
  - TPI → Sweetwater TMI: 88 games.
  - Dates: 15,993 hsfdatabase and 4,430 no-source dates replaced by HSFHA dates. They were mostly ±7 days off (wrong week).
  - Archived: dedup 1,957 + 27; review pairs 745 + 13; same-score 409. Same-score used HSFHA-based decisions in `TN\TN_same_score_decisions.csv` (362 rows).
- **Held:**
  - 2 moves in `TN\hsfha_moves_held.job` (Peabody Demonstration, Trezevant town). They need new HS_Team_Names rows first.
  - MAHS/MASE split: needs a "Memphis Academy of Science and Engineering (TN)" name.
  - Lineage splits (town school → county consolidation): waiting for David.
    His rule: a rename with the same attendance area = one name (latest); a consolidation = split.
- **Unmatched:** about 23,800 of our TN games have no HSFHA match. Not yet reviewed.

## 2026-11-10 (evening) — Claude: TN lineage splits done (jobs 104-106)
- David's rule: a renamed school drawing from essentially the same area = one name (the latest name). Otherwise (consolidation or merger) = split by year.
- Split by year (job 105): Church Hill, Winchester, Dickson, Rhea Central, McMinnville Central, Lynnville, Martin, Copperhill, Ashland City, Tiptonville, Englewood, Pearl, Selmer, Newbern, Wartrace, St. Andrews Academy, Jackson Old Hickory Academy, Fayetteville Central.
  Also Gatlinburg-Pittman 1962+, Fayette Academy (164), MASE (72, URL remapped), Peabody Demonstration (54), Trezevant (34).
- Kept as one name: Rutledge→Grainger, Byars-Hall→Covington, Frayser→MLK Prep, Cumberland County.
- Rules for the split names are identity in TN_Alias_Rules.csv. Do not re-merge them.
- Next: checks (season_date, forfeits, college_check), then review the ~23,800 TN games with no HSFHA match, then re-rate TN.

## 2026-11-10 (night) — Claude: TN unmatched games + HSFHA import (jobs 109-113)
- 14,353 more estimated dates (hsfdatabase/blank/yearbook) were set from HSFHA (`hsfha_dates_far.csv`). Rule: same teams + same score in the same season, with the date more than 10 days off.
- New hs_cleanup.py command: `import-games ST --file <Season,Date,Home,Home_Score,Visitor,Visitor_Score,Neutral,Location,Source> --reason ... [--commit]`.
  It skips a row when a name is not in HS_Team_Names, when the teams already meet that season, or when a team already has a game within ±1 day. Inserts are logged as ROW_ADDED.
- Imported 24,161 HSFHA-TN games (BatchID 196, Source "hsfha.org HSFHA-TN game <id>"). File: `TN\hsfha_import_TN.csv`; skipped rows are in `TN_import_skipped_*.csv`.
  Home/away is inferred from the game city; when unclear, the HSFHA perspective team is Home.
- Same-score fix afterwards archived 66. `TN\hsfha_internal_dups_for_Loren.csv` lists 13 duplicates inside HSFHA itself.
- Double-booked TN days fell from about 12,700 to 1,295.
- Open: `TN\TN_score_disagreements.csv` (5,250 rows, our score differs from HSFHA's) needs a policy from David.
  `TN\TN_unmatched_classified.csv` has the rest (BOTH_COVERED_NO_GAME 964 = possible phantom games).
- David will re-rate after the 2026 season ends (late Dec / early Jan).

## 2026-11-10 (late) — Claude: TN scores + package for Loren (jobs 114-118)
- New hs_cleanup.py command: `set-scores ST --file <ID,Home_Score,Visitor_Score,Note> --reason ... [--commit]`. It is logged as FieldChanged 'Score'.
- David's rule (2026-11-10): where our score differs from HSFHA's, take the HSFHA score for hsfdatabase and no-source rows. Keep ours for newspaper and MaxPreps rows and report them to Loren.
  1,580 TN scores were changed; the dedup that followed archived 423 and review pairs 460.
- **Loren package convention:** `J:\Users\demck\Google Drive\Shared_Loren_Maxwell\<State>\` holding:
  - <ST>-Scores-Full.csv
  - <ST>-Team-Names.csv
  - <ST>-HSFHA-Score-Differences.csv
  - <ST>-Games-Not-On-HSFHA.csv
  - <ST>-HSFHA-Possible-Duplicates.csv
  - <ST>-School-Name-Map.csv
  - <ST>_Cover_Note.md
  The Tennessee package is done.
- David wants the same compare + package for the other HSFHA Southeastern states (AL, AR, FL, GA, LA, MS, NC, SC) as each is cleaned. He also agreed to share Texas after its cleanup.

## 2026-11-10 (late) — Claude: North Carolina done (jobs 119-134)
- HSFHA-NC pull: 146,239 games from 844 schools (`NC\hsfha_NC_games.csv`). This pull has a TeamSite column (h/a/n), which the import uses for home/away.
  Scripts are in the device VM at `~/nc/` (copies of `~/tn/` with paths changed).
- **Applied:**
  - About 70 alias rules, 14 URL remaps.
  - About 750 per-game school fixes, plus 5 consolidation splits by year: Grainger (Kinston) to 1969 (it lands as "Kinston Jesse W. Grainger (NC)"), Marshall to 1972, Ahoskie to 1987, Sylva-Webster to 1987, Candler to 1954.
  - 252 dates and 2 scores set.
  - Same-score 264 archived (HSFHA decisions).
  - 10,078 HSFHA games imported (BatchID 197).
  - Dedup 850, review pairs 145, college copies 3.
- **INCIDENT, caught:** the NC rules file had a cycle, Gastonia Mt. Zion ↔ Gastonia Mount Zion. The result was harmless (18 games ended up under Mount Zion). It is fixed; Mount Zion is now identity.
  Lesson: always run the chain/cycle check after EVERY rules-file edit, not only some.
- **Case-only renames do nothing.** SQL Server collation is case-insensitive, so "SouthWest" vs "Southwest" or "GRACE" vs "Grace" can't be fixed by consolidate.
- **Left as-is:** Cabarrus/Cannon-Concord Academy co-op names, Northampton County East/West, Southeast Halifax (HSFHA: Southeast Collegiate Prep), Carolina Pride/Bearcats, Riverside-Martin.
- The Loren package is in `Shared_Loren_Maxwell\North Carolina\`. It has no possible-duplicates file (none found).

## 2026-11-10 (evening) — Claude: Oklahoma done (jobs 135-145)
- No HSFHA coverage. Used opponent geography (~/ok/geo2.py, scan.py) and exact-name twins across states.
- **Wrong-state twins:**
  - Moved per game: Joiner Shawnee (AR) → Shawnee (OK) 69; Kiowa (KS) → Kiowa (OK) 60 (SE Oklahoma opponents only); Pawnee (OK) → Grover Pawnee (CO) 55; Ada (OK) → Ada (KS) 17; Chelsea (OK) → Chesnee (SC) 17; plus about 35 small moves.
  - About 28 "(OK)" names for out-of-state towns merged by rule (Fort Smith (OK) → Fort Smith (AR), and so on).
- **South Coffeyville Oklahoma Union held two schools.** 321 games moved to South Coffeyville (OK) by clustering opponents with date conflicts (~/ok/socu.py).
- Northwest Classen games before 1955 → Classen (167). Tulsa (OK) games before 1935 → Tulsa Central (66).
- **hs_cleanup.py:** iwasatthegame is now an estimated-date source (all Fridays; 27% of its games were double-booked).
  Double-booked OK days fell from 5,997 to 1,992.
- **Archived:** dedup 504, review pairs 37, same-score 273, college 1.
- **Open:**
  - 254 same-score pairs undecided.
  - Classen vs Northwest Classen 1955-74 may still be mixed.
  - Loren's Oklahoma folder still holds the September export; refresh it only if David asks.

## 2026-11-11 — Claude: STATUS AT HANDOFF (Claude near weekly limit)
- **Runbook:** `_hsfha_scripts\README_HSFHA_RUNBOOK.md`. Per-state scripts are copied into `_hsfha_scripts\tn|nc|ar|ok\`.
- **Done:** TN, NC, OK (+ Loren packages for TN, NC, and the OK refresh). Re-rate of TN/NC/OK waits for the end of the 2026 season.
- **ARKANSAS (in progress):**
  - The match is done. Rules file edited (backup in `_claude_backup_2026-11-10`).
  - Job `_jobs\pending\150_ar_round1.job` is ready. It needs David to run this SQL first:
    `INSERT INTO dbo.HS_Team_Names (Team_Name, State) VALUES ('Des Arc (AR)','AR'),('Amity (AR)','AR'),('Little Rock Southwest (AR)','AR'),('West Helena Woodruff (AR)','AR');`
    Then move the job from `pending\` into `_jobs\`.
  - Remaining after that: steps 6-10 of the runbook. The same-score preview has 592 pairs, to be decided from the match.
  - Kept separate on purpose (consolidations): Glenwood/Centerpoint, Ola/Two Rivers, Yellville/Yellville-Summit, Wilson/Rivercrest, Helena/HWH Central, Maumelle/Oak Grove, Marianna/Lee, Camden/Camden Fairview.
- **LOUISIANA:** HSFHA pull done; files are in `hs_school\LA\`. Start at runbook step 1 (rules file, addstate, dump).
- **MISSISSIPPI:** HSFHA pull done 2026-11-11; files are in `hs_school\MS\`. Start at runbook step 1.
- **Next after the HSFHA states:** AL, GA, SC, FL compare; then OR, IA, OH, MI, IL.
- 2026-11-11 update: the Arkansas round-1 job (150) RAN OK: 21 per-game move groups, 5 lineage moves (Amity, LR Southwest, West Helena Woodruff, Hartman, Palestine), 5 remaps, mapcheck, consolidate. Job 151 committed dedup + review pairs.
  Arkansas next: re-dump (`query AR ar_dump.sql`), then runbook steps 6-10 (dates/scores, same-score decisions for 592 pairs, import, checks, Loren package).
- 2026-11-11 later — **ARKANSAS DONE** (jobs 152-157):
  - 243 dates and 3 scores set from HSFHA.
  - Same-score 348 archived.
  - 14,374 HSFHA games imported (BatchID 198).
  - Dedup and review pairs committed; college copy 1.
  - Loren package written to `Shared_Loren_Maxwell\Arkansas\` (with cover note).
  Next: LA, then MS (files in place).
- 2026-11-11 — **LOUISIANA round 1 done** (jobs 158-165):
  - About 65 alias rules (renames to the latest name) and 11 wrong-state groups moved.
  - 8 remaps. Dedup 428, review pairs 26, same-score 739 (HSFHA decisions). 530 dates set; college copies 2.
  - HELD:
    - About 2,000 HSFHA-suggested per-game moves between LA schools (`LA\hsfha_LA_auto_moves_REVIEW.txt`). HSFHA's LA data is less clean, and some suggestions look wrong (Shreveport Huntington vs Ferriday Huntington Academy 159; Jesuit/Loyola crossing; Eunice → Lafayette Judice).
    - The HSFHA-LA import and Loren's LA package, until those are reviewed.
    - The New Orleans Douglass/F.T. Nicholls/KIPP Renaissance lineage.
  - Next: review the held moves, then the import, then Loren's package; after that, MISSISSIPPI (files in place).
- 2026-11-11 later — **LOUISIANA DONE** (jobs 166-171):
  - 29 reviewed per-game move groups applied (~1,300 games). Each was checked by opponent geography and same-date double-bookings (`~/la/evalmv.py`, copied to `_hsfha_scripts\la\`).
  - Walker (LA) pre-2013 games went to O.P. Walker, not Landry-Walker (merger rule).
  - NOT applied: Youngsville Southside → Monroe Southside (28): "Monroe Southside (LA)" is not in HS_Team_Names (insert it, then rerun la_rev_mv_13.csv).
  - Also NOT applied: Baker Central Private/Baker, St. Joseph Tensas/Tensas Academy, Gonzales East Ascension/Ascension, Brother Martin/St. Martin's (geography can't tell them apart).
  - Imported 8,397 HSFHA games (BatchID 199).
  - Loren LA folder refreshed (Sept files kept in `_previous_2026-09`) plus `LA_Update_Note_2026-11.md`.
  - Next: MISSISSIPPI (files in place).
- 2026-11-11 — **MISSISSIPPI DONE** (jobs 173-182):
  - About 130 long-pending rules + 45 HSFHA merges.
  - AL-labelled MS schools moved (Rosedale 442, Decatur 400, Macon Central Academy 333, Macon 160).
  - Dedup about 2,500. Same-score 6,886: mostly ahsfhs games recorded twice under two lineage names. Kept the name with more history; HSFHA lumps these (Laurel/Watkins, Belzoni/Humphreys Co., Pinola/Simpson Central…). Our DB still keeps the separate names.
  - 338 dates, 5 scores; 2,208 HSFHA games imported (BatchID 200).
  - Loren package written to `Shared_Loren_Maxwell\Mississippi\`.
  - Next HSFHA states: AL, GA, SC, then the FL compare.

## 2026-11-11 (afternoon) — Claude: ALABAMA DONE (jobs 183-191)
- HSFHA-AL pull: 871 schools, 206,647 games (Q173). Scripts: `_hsfha_scripts\al\` (pairs.txt = curated alias pairs; dbl.py = double-booking check per alias pair; ssdec.py = same-score decisions from the match).
- Round 1 (job 186): 15 per-game moves, York Sumter Central <=2010 -> York Sumter County (new name), 15 remaps, mapcheck, ~115 merges in AL_Alias_Rules.csv.
  - Renames to latest name (David's rule): Jasper Walker->Jasper, Montgomery Lee->Montgomery Percy Julian, Montgomery Jefferson Davis->Montgomery JAG, Fairfax Valley->Valley, Erwin->Birmingham Center Point, Toulminville->Mobile LeFlore, Lyman Ward->Camp Hill Southern Prep Academy.
  - Integration-era same-town merges treated as one name: Parrish Selma->Selma, Hicks Memorial->Autaugaville, Wilcox County->Camden Wilcox Central (least certain).
  - NOT merged (both names play different games on the same dates): DeKalb County/Fort Payne, Jackson County/Scottsboro, Alexander City/Benjamin Russell, Shades Cahaba/Shades Valley, Bankhead/Cordova, Jefferson County/Tarrant, Troy/Charles Henderson, Semmes/Mary Montgomery, Central Mobile, Darden, Birmingham Phillips, Mobile McGill.
  - "Huntsville A.L. Johnson" was really Thomaston A.L. Johnson (new name); 129 games went to Huntsville J.O. Johnson.
- Same-score: first run ignored the decisions file (relative --decisions path is NOT resolved to the state folder; omit --decisions to use the default <ST>\<ST>_same_score_decisions.csv). 225 wrong archives restored by David's SQL (BULK INSERT of AL_ss_restore_ids.txt); rerun archived 892.
- Imported 14,447 HSFHA games (BatchID 201). Loren package in Shared_Loren_Maxwell\Alabama (with AL_Cover_Note.md).
- Open: Dothan split at 2019 (needs a name for the 1912-2018 Dothan HS; asked David). 541 undecided same-score pairs. forfeits 22 rows, college_check output not reviewed.

## 2026-11-11 (late afternoon) — Claude: GEORGIA DONE (jobs 192-198)
- HSFHA-GA pull: 1,046 schools, 175,071 games (Q1428). Scripts in `_hsfha_scripts\ga\`.
- Round 1 (job 194): ~125 merges, 11 move groups, era splits (Macon Lanier, Atlanta Archer, Old Rome, Hapeville [new name]), Nathanael Greene out of Monsignor Donovan, 18 remaps. New names: Hapeville (GA), Duluth Notre Dame (GA).
- Left split (county consolidation / unsure): Jesup/Wayne County, Donalsonville/Seminole County, Americus/Americus-Sumter, Sparks-Adel/Cook, Blakely/Blakely-Union, Stewart/Stewart-Quitman, Mitchell-Baker+Camilla/Mitchell County, Gray/Jones County, Conyers/Rockdale County, Murphy/Crim, Richmond County/ARC, College Park GMA.
- Same-score 691 by HSFHA decisions (default decisions path). 36 dates, 4 scores, 11,866 imports (BatchID 202). Loren package in Shared_Loren_Maxwell\Georgia.

## 2026-11-11 (evening) — Claude: SOUTH CAROLINA DONE (jobs 199-205)
- HSFHA-SC pull: 699 schools, 113,069 games (Q1456). Scripts in `_hsfha_scripts\sc\`.
- Old wrong rule fixed: "Saint Matthews Calhoun County" was merged into Calhoun Academy; new name Saint Matthews Calhoun County (SC); 398 games moved back.
- Round 1 (job 201): NC-labeled SC twins moved back, Wade Hampton (Hampton) split from Greenville Wade Hampton, St. John's (Darlington)/McClenaghan/Winyah/Mt Zion Institute/Edmunds split out, ~53 merges, 16 remaps.
- scfootballhistory.com dates are week-based and usually +7 or +14 days vs HSFHA (24k matched at exactly 7 days). 31,148 replaced by HSFHA dates (job 203). scfootballhistory rows NOT on HSFHA still carry those dates — consider adding scfootballhistory to the estimated-date sources in hs_cleanup.py.
- 12,519 imports (BatchID 203). Loren package in Shared_Loren_Maxwell\South Carolina.
- Open: HSFHA era splits not done (Ridgeland -1985/2007-2011, Bluffton 1959-1970, McColl, Blythewood -1968, Hardeeville, Fountain Inn) — need old-school names.
- 2026-11-11: Dothan split (David named it): Dothan (AL) seasons <=2018 -> "Dothan Old (AL)" (1,041 games; job 206). Dothan (AL) = the 2019 Dothan + Northview consolidation.
- David 2026-11-11: Parrish->Selma, Hicks Memorial->Autaugaville, Wilcox County->Wilcox Central stay merged (same-town integration mergers draw from the same geography; the Black schools Hudson / Camden Academy keep their own names ending at the merger).

## 2026-11-11 (night) — Claude: FLORIDA HSFHA COMPARE DONE (jobs 207-213)
- HSFHA-FL pull: 932 schools, 123,527 games (Q812). Most of it came from David's data originally; match 116,800 of 129,900.
- Round 1 (job 209): 53 merges, Dover Strawberry Crest (new name) 177 games out of Dover Specially Fit Academy, East Gadsden 2003-16 -> Quincy East Gadsden, 14 remaps.
- Not merged (both names play the same dates): Boca Raton Community / Boca Raton, Chaminade / Chaminade-Madonna, Leon County / Tallahassee Leon, Miami Lakes / Hialeah-Miami Lakes, Robert E. Lee -> Riverside, Pinellas County Seminole.
- 122 dates, 48 scores, same-score 53, 755 imports (BatchID 204). Loren package in Shared_Loren_Maxwell\Florida.
- Still open: Kissimmee Victory Charter and Tallahassee Rickards MaxPreps URLs (no name).

## 2026-11-11 (night) — Claude: OREGON round 1 (jobs 214-219)
- 74,600 games; 57% from beasport.com all-time scores (ALL dated Fridays = estimated dates). beasport + scfootballhistory added to the estimated-date sources in hs_cleanup.py (backup _claude_backup_2026-11-11\hs_cleanup_pre_beasport.py).
- beasport team pages repeat each school's history under old and new names; merged renames to the latest name and deduped 1,134 + 217 review pairs + 234 same-score.
- 361 Portland Jefferson games moved out of Jefferson (OR) (Portland-league opponents; pre-1950 Portland-area opponents).
- OPEN: Medford lineage (North Medford and South Medford both carry Medford High 1907-1985 history) - asked David. Also co-ops (Weston-McEwen-Griswold, McLoughlin-Griswold, Coquille-Pacific, Washington-Monroe) not split.
- Medford done (job 220-221): South Medford <=1985 -> North Medford (David: old Medford High = North Medford).

## 2026-11-12 — Claude: IOWA round 1 (jobs 222-226)
- 135,700 games; MaxPreps + yearbooks; no estimated-date archive site. Main problem: whole-grade-sharing / consolidation names (Central Lyon vs Central Lyon-George-Little Rock, Waverly vs Waverly-Shell Rock, CAL vs CAL-Dows...) carrying the same game twice.
- 21 rules (2024 MaxPreps drift + same-school spellings), 11 remaps, dedup 511, review pairs 7.
- Same-score 1,760 archived: tool rules + "era" decisions (IA_same_score_decisions.csv: keep the name that has >=3 other games in that season +/-1, the other doesn't); 793 undecided (both or neither name active).
- Not done: co-op / consolidation splits by year (left as separate names); Cedar Rapids Jefferson vs Jefferson (IA) small twin; "Modamin West Harrison" typo / Mondamin URL.

## 2026-11-12 — Claude: OHIO round 1 (jobs 228-233)
- 248,700 games (MaxPreps 81k, classmates yearbooks 17k, Akron Beacon Journal 11k...). 26 rules (2024 MaxPreps short names + city variants), Lima Central 2024+ -> Lima Catholic Central (old Lima Central = the public school before 1960), 28 remaps, dedup 527, review pairs 48, same-score 1,789 (tool + era decisions), 856 undecided.
- Not merged (both names have different games the same dates): Columbus Grandview Heights / Grandview Heights, Stark County Hartville Lake / Uniontown Lake; Chillicothe vs South Charleston Southeastern; Berlin Center vs Collins Western Reserve (two schools).

## 2026-11-12 — Claude: MICHIGAN round 1 (jobs 234-239)
- 209,900 games; 57% from michigan-football.com (99% Fridays = estimated dates) -> added to the estimated-date sources in hs_cleanup.py.
- 30 rules (2024 MaxPreps short names, same-school variants, renames to latest), 31 remaps (13 ProperNames did not exist), mapcheck 62, dedup 730, review pairs 19, same-score 1,275 (tool + era), 529 undecided.
- Left: Southfield / Southfield Arts & Tech, Unionville-Sebewaing, Elkton-Pigeon-Bay (consolidations, era rule only); Saginaw United (2024 Arthur Hill + Saginaw HS merger) separate; 4 one-game "...\nHomecoming" names with a newline; Westland Glenn URL (no name).

## 2026-11-12 — Claude: ILLINOIS round 1 (jobs 240-245)
- 201,900 games. www.ihsa.org rows (21k) are all Fridays = estimated dates -> added to hs_cleanup.py estimated-date sources (with michigan-football.com, beasport, scfootballhistory).
- 31 rules (2024 MaxPreps short names, same-school variants, renames to latest: Lincoln-Way -> Lincoln-Way Central, Gordon Tech -> DePaul College Prep, Marine Military -> Marine Leadership), 42 remaps (20 ProperNames did not exist), mapcheck 34, dedup 582, review pairs 14, same-score 2,232 (tool + era), 1,359 undecided (many co-op names).
- Not done: IL co-op names ("X Coop", multi-school co-ops) - not split by year; MaxPreps URLs left unmapped: Morgan Park (public HS, no name), Saint Ignatius, IC Catholic, Flora, Hamilton-Warsaw, Alden-Hebron, West Carroll, West Central, Perspectives.
- ALL PLANNED STATES DONE (HSFHA: TN NC AR LA MS AL GA SC FL; plus OK OR IA OH MI IL). Re-rate after the 2026 season.

## 2026-11-12 — Claude: MAINE + VERMONT round 1 (jobs 247-250)
- ME 25,000 games: 10 rules (incl. the long-pending Kittery Traip -> Kittery Traip Academy; Auburn Little -> Auburn Edward Little; Belfast Crosby -> Belfast Area), 11 remaps, dedup 189, review pairs 17, same-score 34.
- VT 9,400 games: Mount Mansfield Union, BFA Fairfax-Lamoille co-op URL, Mount Anthony / Mt. Abraham-Vergennes URLs; dedup 29, review pairs 2, same-score 34.
- Next per David's order: AK, HI, DC, DE, NV (small), then WA, ID, MT, ND, SD, MN, WI; then KY, WV, VA, MD, IN, NY; then PA, NJ, TX; CA.

## 2026-11-12 — Claude: AK, HI, DC, DE, NV round 1 (jobs 251-254)
- All small and fairly clean. AK 4,500 games (dedup 7, same-score 11), HI 10,900 (Kamehameha/Kapalama -> Honolulu Kamehameha-Kapalama, 'Iolani; dedup 61, same-score 15), DC 6,900 (Wilson -> Jackson-Reed; dedup 15, same-score 9), DE 13,200 (FCA Bucks, Mount Pleasant URL; same-score 8), NV 14,500 (Dayton Dust, The Meadows, Agassi Prep -> Democracy Prep Agassi Campus; dedup 46, same-score 17).
- Left: HI Pukalani Kamehameha Maui vs King Kekaulike same-score pairs (two schools), DC Chavez/Parkside and Kingsman/Options pairs, Tafuna American Samoa and a Mississauga school mapped under HI/AK URLs.
- Next per David's order: WA, ID, MT, ND, SD, MN, WI.

## 2026-11-12 — Claude: WA ID MT ND SD MN WI first pass (jobs 255-256), stopped near token limit
- Only the automatic pass ran: mapcheck --commit, dedup, review pairs, same-score (tool rules) committed. Same-score archived WA 396, ID 99, MT 209, ND 420, SD 734, MN 729, WI 380; dedup and review pairs were small.
- NOT done yet for these 7: name review (2024 MaxPreps drift reports are in each <ST>\<ST>_drift_*.csv), URL remaps, alias rules, undecided same-score pairs (era decisions), estimated-date source check.
- Next: name rounds for these 7, then KY WV VA MD IN NY, then PA NJ TX, CA.
- 2026-11-12 (later): name rounds done for WA MT ND SD MN WI (jobs 257-265): 2024 MaxPreps short names, renames to latest (SD Red Cloud -> Mahpiya Luta, WI Madison Memorial -> Vel Phillips Memorial), SD/MN round 2 same-school variants, MN Lakeville <=2004 -> Lakeville North; 34 URL remaps; era same-score decisions (WA 135, ID 24, MT 90, ND 140, SD 434, MN 583, WI 170 archived).
- OPEN: ND co-op vs member names (2,270 undecided same-score pairs: Minot/Minot-Dakota Memorial, Wyndmere-Lidgerwood, Towner-Granville-Upham...) need co-op splits by year; similar but smaller in SD/MN/WI. ID had no name issues.
- Next: KY WV VA MD IN NY, then PA NJ TX, CA.

## 2026-11-12 (midday) — Claude: KY WV VA MD IN NY round 1+2 (jobs 266-270)
- 2024 MaxPreps short names merged (KY 4, WV 5, VA 9, IN 10, NY 14), 41 URL remaps, mapcheck; round 2 same-school variants / renames to latest (see tracker 1.1 notes); Bloomington (IN) <=1971 -> Bloomington South.
- Big duplicate counts came from the same game under a school's two lineage names: dedup WV 1,270 / VA 1,544 / IN 1,547; same-score (tool + era) KY 1,491, WV 1,004, VA 2,156, IN 1,211, NY 1,711.
- OPEN: undecided same-score pairs are mostly town -> county consolidations (KY Harlan/Harlan County, Louisa/Lawrence County; WV Hinton/Summers County, Weston/Lewis County, Montgomery/Valley; VA Hillsville/Carroll County ...): need consolidation years (split by year) per David's rule.
- Next: PA, NJ, TX (estimated-date archive sources: digital.libraries.psu.edu, texashighschoolfootballhistory, lonestarfootball), then CA.

## 2026-11-12 (afternoon) — Claude: PENNSYLVANIA round 1 (jobs 271-275)
- 333,000 games, 71% from digital.libraries.psu.edu (all Fridays, estimated). Many schools appear on two PSU team pages under two names -> merged after an opponent-overlap check (ovl.py in ~/pa: share of A's season+opponent pairs also in B).
- 32 rules, 26 remaps, 3 era splits (East Stroudsburg, Downingtown, Council Rock), dedup 1,725, review pairs 3,396, same-score 2,122; 1,673 undecided.
- Next: NJ, TX, then CA.

## 2026-11-12 (afternoon) — Claude: NEW JERSEY round 1 (jobs 276-279)
- 161,500 games, 70% from digital.libraries.psu.edu (estimated dates). 14 rules (MaxPreps short names, PSU same-school pairs checked with ovl.py, renames to latest: Woodrow Wilson -> Camden Eastside, East Paterson -> Elmwood Park), 14 remaps (7 ProperNames did not exist), dedup 496, review pairs 1,172, same-score (tool + era).
- Odd mass same-score pairs for Park Ridge/Pleasantville (171), Keyport/Pennsville Memorial (164), East Orange/Paramus (156): one PSU block probably carries the wrong team on a whole page - look before trusting either copy.

## 2026-11-12 (afternoon) — Claude: TEXAS round 1 (jobs 280-285)
- 500,000 games (MaxPreps 157k; lonestarfootball 22k + texashighschoolfootballhistory 25k, all Fridays, already estimated-date sources).
- 39 rules: 23 MaxPreps short names; renames to latest (Houston Reagan -> Heights, Jefferson Davis -> Northside, Tyler Lee -> Legacy, Houston Lee -> Wisdom, Austin Reagan -> Northeast Early College, Austin Lanier -> Navarro, Brownsville -> Hanna); variants (Clear Creek -> League City, Reicher Catholic, Quinlan Ford, North Dallas, Kerrville Tivy, Spring Klein, Concordia Lutheran -> Tomball). 27 remaps, mapcheck 128, dedup 754, review pairs 1,145, same-score 1,644; 1,178 undecided.
- Left: Wichita Falls / Wichita Falls Legacy (2024 consolidation), Three Way / Maple Three Way, Baytown vs Houston Sterling, Sam Houston variants. Loren gets the TX data after cleanup (David's agreement) - not sent yet.
- Next: CA.

## 2026-11-12 (afternoon) — Claude: CALIFORNIA round 1 (jobs 286-290). ALL 50 STATES + DC HAVE HAD A FIRST PASS.
- 345,000 games (MaxPreps 121k, classmates yearbooks 15k, partletonsports 14k (Fridays), calpreps 14k, Kevin Askeland NorCal collection 13k).
- 54 rules (43 MaxPreps short names; renames to latest: University of San Diego High -> Cathedral Catholic, Chatsworth/Granada Hills -> Charter, Sepulveda Monroe -> North Hills Monroe, Riverside Rubidoux -> Jurupa Valley), 48 remaps, mapcheck 40, dedup 886, review pairs 52, same-score 2,409; 1,146 undecided.
- Not merged (low opponent overlap = probably two schools): Mission Bay / San Diego Mission Bay, Hilltop / Chula Vista Hilltop, Midway Baptist, Garfield / LA Garfield, Atherton Menlo (Menlo School vs Menlo-Atherton), Placentia vs Valencia.
- Second-pass work everywhere: undecided same-score pairs (co-ops and town->county consolidations need split years), project plan doc update, re-rate after the season, Loren TX package.

## 2026-11-12 (late) — Claude: CO-OP / CONSOLIDATION ROUND (jobs 291-307). Scripts + per-state configs in _coop_scripts\
- ND (jobs 291-293): northdakotahsfootball.altervista uses member-town names, MaxPreps uses co-op names. 2,107 same-score pairs -> keep MaxPreps row; 84 member->co-op moves (member-name altervista games in seasons where MaxPreps shows the co-op); dedup 1,215. Jamestown-Medina-Montpelier <=2003 -> Jamestown; Fargo (ND) <=1964 -> Fargo Central; Dickinson Trinity (ND) -> Dickinson Trinity Old HS. ND undecided same-score 2,270 -> 133.
- Other states (coop.py + <ST>_cfg.py): WRONG = opponent name misread in one paper (keep the other row, judged by the opponents' geography, e.g. SD Gary -> Gayville-Volin, Ramona-Rutland -> Rapid City Stevens; IL Chicago Parker -> Paris, Avon -> Aurora West...). ALIAS = same school, later name stays (rules file + consolidate). COOP = member vs co-op name in the same season: one name per season (majority). PREF = town vs consolidated county school: town name kept up to the consolidation year (KY Louisa/Harlan/Danville..., WV Hinton<=1993, Weston<=1967, Montgomery, Smithers Valley; VA Hillsville, Victoria, Pulaski, Emporia, Shawsville, Osbourn<=1974...).
- SAFETY RULE added after SD ran: a season's games are renamed only if >=80% of them match a game under the other name (same opponent, +-3 days); otherwise only the matching (duplicate) games are renamed. SD job 294 ran before this rule; job 299 moves 372 SD games back. MN job 295 stopped at its first move on purpose (ids files pulled); MN redone as job 300.
- Not touched (need David or research): MN Ruthton/Tyler co-op naming, Welcome vs Wellcome Memorial, Lake Benton/Lincoln HI; SD Pierre Old HS vs T.F. Riggs; ND Dickinson Trinity Old HS vs Trinity-New England (1975-89); KY Ashland Blazer vs Boyd County; WV Monroe County Union/Union; VA Arlington Washington-Liberty vs Montross Washington & Lee, Normal Community vs University High (IL), Duluth Central/Denfeld, Calumet City TF vs Thornton.
- WRONG names probably also mislabel games that had no duplicate (e.g. IL "Chicago Parker" games vs Robinson/Casey). Next: scan each WRONG name's other games for the right school's usual opponents.
- Results (jobs 299-307, all OK): undecided same-score pairs SD 612->237, MN 572->264, WI 297->93, IA 793->304, IL 1359->493, KY 1023->337, WV 2377->257, VA 2846->616, OR 191->130.
- NOT RUN (target name missing in HS_Team_Names): Corydon, Dunlap, Leon, Tabor (IA), Northfield Township Glenbrook (IL) -> job pending\308_ia_il_newnames.job after David inserts the names.
- Job 309: 120 non-duplicate games under misread names moved to the right school (only where the right school played that opponent 4+ times within 5 years, no MaxPreps rows; IL Chicago Washington/Washington and Mount Carmel left alone because they go both ways). Review lists: <ST>\<ST>_wrong_name_suspects.csv.

## 2026-11-13 — Claude: ROUND 2 on the biggest undecided lists (jobs 310-319)
- VA r2 (310), PA (311), TX (312), CA (313), NJ (314), NY (315), OH (316), IN (317), MI (318), AL (319). Configs in _coop_scripts\<ST>_cfg.py (coop_c3.py, ids files coop_ids\<ST>_c3_*).
- Big finds: NJ PSU pages mislabel opponents (Pleasantville = Park Ridge, Paramus = East Orange, Keyport = Pennsville Memorial: 564 pair decisions); PA PSU pages carry two names per school (Homestead/Munhall Homestead, Malvern School, Levittown Truman...); IN almanac vs newspaper names for consolidated schools (Hammond <=2020, Brazil <=1966, Bedford <=1974, Bloomington 1972+ -> Bloomington South); MI 2024-25 MHSAA vs MaxPreps names (aliased to the MaxPreps names).
- Left alone (unclear): PA Scranton/Scranton Tech, Central York/York High, Ellwood City vs Taylor Riverside; NJ Demarest vs Old Tappan Northern Valley, Franklin Borough/Sussex County Franklin; NY Webster Schroeder/Thomas, Bronx John Jay, LaSalle Academy vs Oakdale La Salle; CA Atherton Menlo vs Menlo School, Mater Dei Catholic vs Marian Catholic; OH Lima Central Catholic vs Lima Central, Delaware Hayes/Willis, Fairview (Sherwood/Dayton/Fairview Park); IN Evansville Reitz vs Reitz Memorial, Fort Wayne North Side vs Northrop; AL Tarrant vs Jefferson County, DeKalb County/Fort Payne, Jackson County/Scottsboro; MI Ann Arbor Pioneer vs University High.
