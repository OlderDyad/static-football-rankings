# Newspaper Import Pipeline — Quick Guide

Copy-paste workflow for processing a batch of scanned newspaper clippings
from raw images through to imported games in `HS_Scores`.

## 0. One-time setup (every new terminal session)

```powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
C:\Users\demck\OneDrive\Football_2024\static-football-rankings\.venv\Scripts\Activate.ps1
```

If you'll be running the AI resolver this session, also set your key (get a
fresh one from aistudio.google.com/apikey if needed — never reuse a key
that's touched a chat window or a public repo):

```powershell
$env:GEMINI_API_KEY = "your-key-here"
```

---

## 1. OCR extraction (raw images -> staged CSVs)

Drop new scans into `Next_Images_Comma_Format` or `Next_Images_Bar_Format`
first, then:

```powershell
python custom_extractor_prepper.py
```

Prompts for `c` (comma-separated scores) or `b` (bar-separated). Moves
processed images to `Completed\Processed_IMAGES_...` and writes one CSV per
image into the `Staged` folder.

## 2. First import attempt

```powershell
python master_scores_importer.py
```

If everything resolves, it imports straight through. If not, it regenerates
`New_Alias_Suggestions.csv` with every unrecognized team name and stops —
continue below.

## 3. AI-assisted name resolution

```powershell
python gemini_alias_resolver.py --dry-run          # preview prompts, zero API calls
python gemini_alias_resolver.py                    # real run, writes AI_Suggested_Name/AI_Confidence/AI_Reasoning
```

Optional: skip straight to autofilling anything Gemini was fully confident
about (this re-calls the API, only High-confidence rows get written to
`Final_Proper_Name`):

```powershell
python gemini_alias_resolver.py --autofill-min-confidence High
```

## 4. Locally autofill the remaining confidence tiers

No API call — just copies `AI_Suggested_Name` into `Final_Proper_Name` for
rows already scored by step 3. Skim a few rows in the CSV first to make sure
a tier looks trustworthy, then:

```powershell
python autofill_from_ai.py --min-confidence Medium-Low
```

## 5. Flag the leftover one-offs as Ignore

Whatever's still blank after step 4 (usually Low-confidence, un-guessable
names) gets checked against the one-off rule (no comma in `Source_Files` or
`Opponents_Played`) and flagged `Rule_Type=Ignore` if it qualifies. Anything
that recurs across multiple clippings is left alone and printed as a
warning — those need a real name or an image check, not an Ignore.

```powershell
python flag_unresolved_as_ignore.py
```

## 6. Commit corrections to the database

```powershell
python apply_corrections.py --dry-run --final      # preview every SQL statement, zero DB writes
python apply_corrections.py --final                # commit aliases + Ignore rows for real
```

Leave off `--final` on any run where you're not ready to permanently
exclude the Ignore rows yet — they'll just stay pending for next time.

## 7. Re-run the importer to complete the batch

```powershell
python master_scores_importer.py
```

Should import clean now that every name is either aliased or flagged
Ignore. If it still balks, it means step 6 didn't cover everything — check
`New_Alias_Suggestions.csv` for remaining blanks.

## 8. Push the staged batch into HS_Scores

```powershell
python batch_queue_manager.py
```

Choose option `2` (Import all staged batches to HS_Scores).

---

## Adding a new state (North Dakota next, then Wisconsin, Illinois, Indiana)

The good news: nothing in this pipeline is hardcoded to Minnesota. Confirmed
while building this workflow:

- `custom_extractor_prepper.py` just OCRs whatever image is in the raw
  folder — no state awareness at all.
- `get_newspaper_region()` in `master_scores_importer.py` derives the
  region purely from the filename (everything before the first 4-digit
  year, e.g. `Bismarck_Tribune_1931...` → `"Bismarck Tribune"`). A new
  newspaper name just becomes a new region automatically.
- The alias/abbreviation tables and the fuzzy matcher are already global —
  the dry-run output you saw earlier included candidate matches from MS,
  TX, VA, etc., so it's already searching the whole database, not a
  Minnesota subset.
- `sanitize_raw_team_name()` / the homoglyph fix are generic OCR cleanup,
  no geography involved.

So starting North Dakota, Wisconsin, Illinois, or Indiana is mechanically
identical to what you just did for Minnesota — same 8 steps above. Two
things worth expecting/doing differently:

1. **Expect a much higher percentage of unrecognized names on the first few
   batches of each new state**, same as this Minnesota batch's earlier
   runs — the alias table hasn't been built up for that state yet. It'll
   drop off fast as `HS_Team_Name_Alias` fills in.
2. **Gemini's region list was out of date for IL/IN** — it already listed
   MN, ND, SD, IA, WI, MT, but not Illinois or Indiana. Updated
   `SYSTEM_INSTRUCTIONS` in `gemini_alias_resolver.py` to include both, so
   confidence/reasoning quality should be the same for those states as it
   is here. Worth revisiting that prompt again once you've got a batch of
   confirmed IL/IN names in the database, the same way the MN/ND/WI
   examples currently baked into it were pulled from real confirmed rows —
   a couple of real IL/IN examples will sharpen its sense of your naming
   convention for those states specifically.

No code changes needed to start ND — just point `Next_Images_Comma_Format` /
`Next_Images_Bar_Format` at North Dakota scans and run step 1.
