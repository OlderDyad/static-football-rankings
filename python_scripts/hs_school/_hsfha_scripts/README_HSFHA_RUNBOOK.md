# HSFHA state compare — runbook (Claude, 2026-11-10)

David and Loren Maxwell (hsfha.org) have a data-sharing agreement. HSFHA covers AL, AR, FL, GA, LA, MS, NC, SC, TN.

## 1. Pull (Claude's in-app browser; plain HTTP gets a 403 from Cloudflare)
Open https://hsfha.org/w/Special:<ST>/schools and run this JS in the page.
The school list comes from the page's own `method=index` request, with length=5000.
For each school, fetch:
`/wiki/extensions/SportsArchive/MVC/controller/api.php?section=<ST>&model=games&method=games&school_code=<code>&season_code=&game_date=&game_week=&undated=&scope=<Q-code>`
(Q-codes: TN Q1509, NC Q1454, AR Q1612, LA Q1588, MS Q1494.) Keep one row per game id.
Columns: GameID,Season,Date,TeamCode,Team,TeamScore,OppCode,Opp,OppScore,GameType,Played,Location,Exhibition,TeamSite.
Download it as `hsfha_<ST>_games.csv` + `hsfha_<ST>_schools.csv`. David moves the files into `hs_school\<ST>\`.

## 2. Scripts (`_hsfha_scripts\<st>\`, copied per state with paths changed)
1. Dump our games: `query <ST> <st>_dump.sql` (copy of TN\queries\tn_dump.sql with the state changed).
2. Build the name map and match games (rm /tmp/<st>_hsfha_*.pkl first):
   - hsfha_map.py → hsfha_match.py → hsfha_names.py → aliases.py → hsfha_match.py again
   - These produce the code→name map, the match (season + oriented score + date ±10 days), the SPLITS/ALIASES lists, and the A/B alias candidates.
3. Make the move lists:
   - plan.py → plan2.py: per-game move lists `hsfha_mv_NN.csv` + move-team lines. Review them by hand; drop the lineage pairs.
   - lineage.py / lin2.py: consolidation splits, under David's rule.
4. Write alias rules (curated by hand) into `<ST>_Alias_Rules.csv`. ALWAYS run the chain/cycle check after every edit.
5. Run one job: moves, remaps, mapcheck --commit, consolidate, dedup, review-pairs. Then `commit <ST>`.
6. Fix dates and scores:
   - Re-dump, re-match, then dates.py + fardates.py → set-dates (estimated sources only).
   - Scores: set-scores, hsfdatabase/no-source rows only.
7. Same-score: write decisions from the match (keep the copy HSFHA has) into `<ST>_same_score_decisions.csv`, then `same-score-fix --commit`.
8. Import: missing.py → missing2.py → `import-games <ST> --file hsfha_import_<ST>.csv` (preview, then --commit).
9. Run the checks (season_date, forfeits, college_check) and set the tracker steps.
10. Write Loren's package with loren.py into `J:\...\Shared_Loren_Maxwell\<State>\`, then write `<ST>_Cover_Note.md`.

## David's rules
- A rename with the same attendance area = one name (the latest name).
- A consolidation or merger = split by year.
- Co-ops are split by year.
- City names are spelled out.
- For score conflicts:
  - hsfdatabase or no-source row → take HSFHA's score.
  - newspaper or MaxPreps row → keep ours and list it for Loren.
