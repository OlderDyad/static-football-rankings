#!/usr/bin/env python3
"""
gemini_alias_resolver.py

Slots into the pipeline BEFORE apply_corrections.py:

    python master_scores_importer.py      # regenerates New_Alias_Suggestions.csv
    python gemini_alias_resolver.py       # <-- NEW: batches unresolved rows through
                                           #     Gemini, writes suggestions back in
    # ...you review AI_Suggested_Name / AI_Confidence / AI_Reasoning, copy the ones
    # you trust into Final_Proper_Name (or use --autofill-min-confidence to do that
    # automatically for rows at/above a confidence level)...
    python apply_corrections.py [--final]
    python master_scores_importer.py

What it does
------------
Reads New_Alias_Suggestions.csv, batches every row that still needs a decision
(Final_Proper_Name blank AND Rule_Type != Ignore) into groups of --batch-size,
and sends each batch to the Gemini API with a structured-output schema so the
response parses directly into AI_Suggested_Name / AI_Confidence / AI_Reasoning
columns -- it does NOT touch Final_Proper_Name unless you pass
--autofill-min-confidence, matching the human-in-the-loop review step you
already do today (this just automates the "ask Gemini" part of it).

Requires
--------
pip install google-genai pydantic pandas --break-system-packages
Set your key as an environment variable (never pass it on the command line
or paste it into a script):
    setx GEMINI_API_KEY "your-key-here"      (Windows, new shells)
    $env:GEMINI_API_KEY = "your-key-here"     (current PowerShell session)

Usage
-----
python gemini_alias_resolver.py                              # process everything unresolved
python gemini_alias_resolver.py --limit 20                   # test on a small batch first
python gemini_alias_resolver.py --dry-run                    # print prompts, make zero API calls
python gemini_alias_resolver.py --autofill-min-confidence High   # also fill Final_Proper_Name for High-confidence rows
"""

import os
import sys
import time
import argparse
import logging
from typing import List, Literal, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === CONFIGURATION (matches apply_corrections.py / master_scores_importer.py) ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
SUGGESTION_CSV = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv')
DEFAULT_MODEL = "gemini-2.5-flash"  # verify this is still current against ai.google.dev before relying on it long-term
CONFIDENCE_ORDER = {"Low": 0, "Medium-Low": 1, "Medium": 2, "Medium-High": 3, "High": 4}

SYSTEM_INSTRUCTIONS = """You are a sports archivist resolving high school football team names from vintage
Midwest/upper-Midwest newspaper scoreboard clippings (Minnesota, North Dakota, South Dakota, Iowa,
Wisconsin, Montana, Illinois, Indiana, roughly 1900-1970) to their correct standalone historic institution.

Apply "Rule B - Keep Distinct": treat historic standalone town schools, independent academies, athletic
clubs, and county agricultural schools as their own distinct entities. Do NOT collapse them into a
modern post-1970 consolidated district name unless the clipping's era is actually after that
consolidation happened.

Match the exact naming convention already used in this database -- these are real, already-confirmed
examples from this same project, follow this style closely:
  "Mandan (ND)"
  "St. Peter (MN)"
  "Forman Sargent Central (ND)"
  "North Branch (MN)"
  "Bismarck St. Mary's Central (ND)"
  "Superior State Teachers College (WI)"

Use the Opponents_Played column as your strongest geographic signal -- teams almost always played
regional rivals, so county/region adjacency to the known opponent(s) is powerful evidence. Also
consider whether the alias text shows signs of OCR/typesetting corruption (broken words across line
wraps, stray single-letter fragments, embedded state abbreviations) versus being an independent
club/academy/school that just isn't in the database yet.

If you are not reasonably confident, say so honestly with Low confidence and a short, best-guess
reasoning rather than fabricating a specific town you are not sure about.
"""

try:
    from google import genai
    from google.genai import types
    from pydantic import BaseModel
except ImportError:
    genai = None
    types = None
    BaseModel = object


if BaseModel is not object:
    class AliasSuggestion(BaseModel):
        unrecognized_alias: str
        suggested_name: str  # empty string if no reasonable guess
        confidence: Literal["High", "Medium-High", "Medium", "Medium-Low", "Low"]
        reasoning: str

    class AliasBatchResponse(BaseModel):
        suggestions: List[AliasSuggestion]


def build_batch_prompt(rows: List[dict]) -> str:
    lines = ["Resolve each of these unrecognized team names. One suggestion object per row, "
             "in the same order given:\n"]
    for i, row in enumerate(rows, 1):
        # Drop NaN/blank fuzzy-match candidates instead of rendering literal "nan"
        # into the prompt.
        candidates = ", ".join(
            str(c) for c in (row.get('Suggested_Proper_Name_1'),
                              row.get('Suggested_Proper_Name_2'),
                              row.get('Suggested_Proper_Name_3'))
            if pd.notna(c) and str(c).strip() != ''
        )
        lines.append(
            f"{i}. Unrecognized_Alias: \"{row.get('Unrecognized_Alias', '')}\"\n"
            f"   Newspaper_Region: {row.get('Newspaper_Region', 'Unknown')}\n"
            f"   Opponents_Played: {row.get('Opponents_Played', 'Unknown')}\n"
            f"   Source_Files: {row.get('Source_Files', 'Unknown')}\n"
            f"   Existing fuzzy-match candidates (may or may not be correct): "
            f"{candidates if candidates else 'None'}\n"
        )
    return "\n".join(lines)


def call_gemini_batch(client, model, rows: List[dict], retries=3) -> List["AliasSuggestion"]:
    prompt = build_batch_prompt(rows)
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTIONS,
                    response_mime_type="application/json",
                    response_schema=AliasBatchResponse,
                    temperature=0.1,
                ),
            )
            parsed: AliasBatchResponse = response.parsed
            if parsed is None:
                raise ValueError("Model response did not parse against the expected schema.")
            return parsed.suggestions
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"Batch call failed (attempt {attempt}/{retries}): {e}. Retrying in {wait}s...")
            time.sleep(wait)
    logger.error(f"Batch of {len(rows)} row(s) starting with '{rows[0]['Unrecognized_Alias']}' failed after {retries} attempts -- skipped.")
    return []


def main():
    parser = argparse.ArgumentParser(description="Batch-resolve unrecognized team names via the Gemini API.")
    parser.add_argument('--input', default=SUGGESTION_CSV, help="Path to New_Alias_Suggestions.csv")
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--batch-size', type=int, default=20)
    parser.add_argument('--limit', type=int, default=None, help="Only process the first N unresolved rows (testing)")
    parser.add_argument('--dry-run', action='store_true', help="Build and print prompts, make ZERO API calls, write nothing.")
    parser.add_argument('--autofill-min-confidence', default=None,
                         choices=['High', 'Medium-High', 'Medium', 'Medium-Low', 'Low'],
                         help="Also copy the suggestion into Final_Proper_Name for rows at/above this "
                              "confidence level. Without this flag, only the AI_Suggested_Name/AI_Confidence/"
                              "AI_Reasoning columns are filled -- you still review before running apply_corrections.py.")
    parser.add_argument('--sleep-between-batches', type=float, default=1.0)
    args = parser.parse_args()

    if not args.dry_run and genai is None:
        logger.error("google-genai / pydantic not installed. Run: pip install google-genai pydantic")
        return

    api_key = os.environ.get('GEMINI_API_KEY')
    if not args.dry_run and not api_key:
        logger.error("GEMINI_API_KEY environment variable not set. Set it and re-run "
                      "(never pass an API key as a command-line argument or hardcode it in this file).")
        return

    logger.info(f"Reading {args.input}")
    df = pd.read_csv(args.input, encoding='utf-8-sig')

    for col in ['Final_Proper_Name', 'Rule_Type', 'AI_Suggested_Name', 'AI_Confidence', 'AI_Reasoning']:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].fillna('')

    # Exclude master_scores_importer.py's internal placeholders (e.g.
    # "[EMPTY/NULL HOME TEAM]") -- these mean the scan/OCR captured no team
    # name at all, there's nothing for the model to guess at, and sending
    # them just wastes a call and clutters the review.
    is_placeholder = df['Unrecognized_Alias'].astype(str).str.strip().str.startswith('[')

    unresolved_mask = ((df['Final_Proper_Name'].str.strip() == '')
                        & (df['Rule_Type'].str.strip().str.lower() != 'ignore')
                        & (~is_placeholder))
    unresolved_idx = df[unresolved_mask].index.tolist()

    skipped_placeholders = int((is_placeholder & (df['Final_Proper_Name'].str.strip() == '')).sum())
    if skipped_placeholders:
        logger.info(f"Skipping {skipped_placeholders} internal placeholder row(s) (e.g. [EMPTY/NULL...]) -- "
                     f"those need the source image checked, not an AI guess.")

    if args.limit:
        unresolved_idx = unresolved_idx[:args.limit]

    if not unresolved_idx:
        logger.warning("Nothing unresolved to send to Gemini. Nothing to do.")
        return

    logger.info(f"{len(unresolved_idx)} row(s) to resolve, in batches of {args.batch_size}.")

    client = None
    if not args.dry_run:
        client = genai.Client(api_key=api_key)

    resolved_count = 0
    autofilled_count = 0

    for batch_start in range(0, len(unresolved_idx), args.batch_size):
        batch_idx = unresolved_idx[batch_start: batch_start + args.batch_size]
        batch_rows = [df.loc[i].to_dict() for i in batch_idx]

        if args.dry_run:
            print("=" * 80)
            print(f"[DRY RUN] Batch {batch_start // args.batch_size + 1}: {len(batch_rows)} row(s), zero API calls made")
            print("=" * 80)
            print(build_batch_prompt(batch_rows))
            continue

        logger.info(f"Sending batch {batch_start // args.batch_size + 1} "
                    f"({len(batch_rows)} rows, starting with '{batch_rows[0]['Unrecognized_Alias']}')...")
        suggestions = call_gemini_batch(client, args.model, batch_rows)

        # Match suggestions back to rows by position (same order as sent) -- fall back to
        # alias-text matching if the model reordered anything.
        by_alias = {s.unrecognized_alias.strip().lower(): s for s in suggestions}
        for pos, row_idx in enumerate(batch_idx):
            alias = str(df.loc[row_idx, 'Unrecognized_Alias']).strip()
            s = suggestions[pos] if pos < len(suggestions) else by_alias.get(alias.lower())
            if s is None:
                continue
            df.loc[row_idx, 'AI_Suggested_Name'] = s.suggested_name
            df.loc[row_idx, 'AI_Confidence'] = s.confidence
            df.loc[row_idx, 'AI_Reasoning'] = s.reasoning
            resolved_count += 1

            if (args.autofill_min_confidence and s.suggested_name
                    and CONFIDENCE_ORDER.get(s.confidence, -1) >= CONFIDENCE_ORDER.get(args.autofill_min_confidence, 99)):
                df.loc[row_idx, 'Final_Proper_Name'] = s.suggested_name
                autofilled_count += 1

        time.sleep(args.sleep_between_batches)

    if args.dry_run:
        logger.info("[DRY RUN] Complete. No API calls made, no file written.")
        return

    # Atomic write: write to a temp file, then replace -- avoids corrupting the live
    # working file if the process is interrupted mid-write.
    tmp_path = args.input + '.tmp'
    df.to_csv(tmp_path, index=False, encoding='utf-8-sig')
    os.replace(tmp_path, args.input)

    logger.info(f"Done. {resolved_count} row(s) got an AI suggestion written to AI_Suggested_Name/AI_Confidence/AI_Reasoning.")
    if args.autofill_min_confidence:
        logger.info(f"{autofilled_count} row(s) at/above '{args.autofill_min_confidence}' confidence also had "
                    f"Final_Proper_Name auto-filled -- review before running apply_corrections.py.")
    else:
        logger.info("Final_Proper_Name was NOT touched. Review AI_Suggested_Name and copy in the ones you trust, "
                     "or re-run with --autofill-min-confidence to do that automatically.")


if __name__ == "__main__":
    main()
