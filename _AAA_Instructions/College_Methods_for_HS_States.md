# College data-quality methods -> HS, state by state

Handoff from the college chat (Oct 27 - Nov 4, 2026) to "State onboarding and data-quality cleanup".
Full college detail: College_Football_Workflow.md. Scripts: python_scripts/college/.
Conventions carry over unchanged: preview first, --commit second; bad rows MOVE to a duplicates
table with a Reason (never just delete); score conflicts default-and-flag; SQL pasted in chat;
HS and college rating runs never overlap.

## What found the most errors (in order of payoff)

| # | Check | What it caught in college | Script / query |
|---|---|---|---|
| 1 | **Double-booked dates**: a team with two games within 2 days | ~4,400 games stored twice under two opponent names (aliases, wrong same-name school) | SQL in chat 2026-11-03; `fix_cross_name_dups.py` |
| 2 | **Alias finder**: names with many seasons but <= 2.5 games/season | ~60 second names (Sawanee = 892 duplicate Sewanee games) | SQL in chat 2026-10-30 |
| 3 | **Split by opponent state**: one name holding two schools | Dickinson PA/ND, Bethel MN/KS/TN, Wayne St MI/NE, Lincoln MO/PA/IL, Monmouth IL/NJ | UPDATE to a temp name by opponent State, then `merge_same_school.py` |
| 4 | **Compare with an outside source, block by block** | Austin Peay: 220 games with both scores reversed in one source block | `audit_vs_winsipedia_cache.py`, `check_residual_games.py` |
| 5 | **Dropped digits**: impossible/rare scores (1; 4/5 after 1912) | ~110 scores that kept only the first digit (Fordham 2-7 = 20-7) | `check_dropped_digits.py` |
| 6 | **Season vs date**: fall games filed in the wrong Season; placeholder years | 627 fall-2021 games filed as 2020; 168 rows dated 1884 | one SQL query |
| 7 | **Forfeits**: 1-0 / 0-1 marked Forfeit = 1 (only from 1890 -- earlier 1-0 was a real score) | 252 | one UPDATE |
| 8 | **Residuals**: games furthest from what the ratings predict | misnamed opponents, typos, swapped scores | `game_residuals.py` |
| 9 | **Gap audit**: team-seasons short of games, ranked | targets for filling | `missing_games_audit.py` |

## Per state: suggested order

1. **Name cleanup first** (it changes every later count): run the double-booked query and the alias
   finder restricted to the state's teams; merge pure aliases; split names that hold two schools by
   opponent city/county or by era (HS names are usually "Name (ST)", so same-named schools in other
   states are already apart -- the risk is same-name schools inside one state, renamed schools, and
   consolidations).
2. **Season/date checks** (#6) and **forfeits** (#7) for the state.
3. **Outside-source comparison** (#4/#5): pick the best per-state source (MaxPreps, state association
   archives, LoneStarFootball for TX, school sites, newspaper OCR) and compare by team + date (+/-2 days)
   regardless of opponent spelling; look for SWAPPED clusters by Source/BatchID.
4. **Duplicate copies** that survive: keep the dated/sourced row, move the other.
5. **Rerate**, then **residuals** for the state's games, then a **gap audit** for filling.

## What to adapt for HS_Scores

- Key: HS_Scores uses `ID` (uniqueidentifier) plus `BatchID`, not `Access_ID`; "source block" = BatchID or Source.
- Duplicates table and existing HS duplicate-removal scripts replace College_Scores_Duplicates.
- Team state comes from HS_Team_Names; the opponent-state splits become opponent-city/county splits
  inside a state.
- `fix_cross_name_dups.py` logic carries over directly (rules: BUSY -> STATE/region -> SOURCE -> REVIEW,
  plus a hand `prefer` file); only table/column names change.
- HS forfeit rule already exists (ScoresWinLoss: 1-0 / 2-0 after 1949 when Forfeit is NULL).

## Lessons that will repeat

- Some sources merge same-named teams (Winsipedia's "Bethel (TN)" page had all three Bethels); check
  that a team's opponents stay in one region.
- School/athletics sites can link one-off opponents to a single history page (Missouri S&T's
  "Christian Brothers" held 25 other teams) -- prefer season-by-season pages.
- Weekly loads re-create aliases unless their spellings are mapped (wolfe_name_map.csv in college).
- Fix names before scores: most "bad scores" in the residuals were really wrong opponents.
