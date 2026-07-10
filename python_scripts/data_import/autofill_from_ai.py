#!/usr/bin/env python3
"""
autofill_from_ai.py

Copies AI_Suggested_Name into Final_Proper_Name for every still-blank row at
or above a chosen confidence tier -- no API call, works entirely off the
AI_Suggested_Name / AI_Confidence columns gemini_alias_resolver.py already
wrote. Use this after eyeballing a handful of rows at a tier and deciding you
trust the whole tier, instead of manually copy-pasting each one.

Fits in the pipeline right after gemini_alias_resolver.py:

    python master_scores_importer.py
    python gemini_alias_resolver.py
    python autofill_from_ai.py --min-confidence Medium-Low   # <-- this
    python flag_unresolved_as_ignore.py
    python apply_corrections.py --final
    python master_scores_importer.py

Usage
-----
python autofill_from_ai.py                                  # default: Medium-Low and above
python autofill_from_ai.py --min-confidence High             # only High
python autofill_from_ai.py --dry-run                         # preview, write nothing
"""

import os
import argparse
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
SUGGESTION_CSV = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv')

CONFIDENCE_ORDER = {"Low": 0, "Medium-Low": 1, "Medium": 2, "Medium-High": 3, "High": 4}

# Defensive guard: AI_Suggested_Name sometimes contains a non-answer
# ("Unresolvable", "Unknown (SD)", blank) even at Low confidence -- never
# copy those into Final_Proper_Name even if a --min-confidence of Low is
# passed explicitly.
BAD_VALUES = {'', 'unresolvable', 'unresolved', 'unknown', 'n/a', 'none'}


def main():
    parser = argparse.ArgumentParser(description="Autofill Final_Proper_Name from AI_Suggested_Name at/above a confidence tier.")
    parser.add_argument('--input', default=SUGGESTION_CSV)
    parser.add_argument('--min-confidence', default='Medium-Low',
                         choices=['High', 'Medium-High', 'Medium', 'Medium-Low', 'Low'],
                         help="Autofill rows at or above this tier. Default: Medium-Low (i.e. everything but Low).")
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    logger.info(f"Reading {args.input}")
    df = pd.read_csv(args.input, encoding='utf-8-sig')

    for col in ['Final_Proper_Name', 'AI_Suggested_Name', 'AI_Confidence']:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].fillna('')

    threshold = CONFIDENCE_ORDER[args.min_confidence]
    tier_ok = df['AI_Confidence'].map(lambda c: CONFIDENCE_ORDER.get(str(c).strip(), -1) >= threshold)

    mask = (
        (df['Final_Proper_Name'].str.strip() == '')
        & tier_ok
        & (~df['AI_Suggested_Name'].str.strip().str.lower().isin(BAD_VALUES))
    )

    updated = df[mask][['Unrecognized_Alias', 'AI_Confidence', 'AI_Suggested_Name']]
    logger.info(f"{len(updated)} row(s) at/above '{args.min_confidence}' confidence to autofill.")
    for _, r in updated.iterrows():
        print(f"  [{r['AI_Confidence']:<12}] {r['Unrecognized_Alias']:<35} -> {r['AI_Suggested_Name']}")

    if not len(updated):
        logger.info("Nothing to do.")
        return

    if args.dry_run:
        logger.info("[DRY RUN] Nothing written.")
        return

    df.loc[mask, 'Final_Proper_Name'] = df.loc[mask, 'AI_Suggested_Name']

    tmp = args.input + '.tmp'
    df.to_csv(tmp, index=False, encoding='utf-8-sig')
    os.replace(tmp, args.input)
    logger.info(f"Done. {mask.sum()} row(s) autofilled.")


if __name__ == "__main__":
    main()
