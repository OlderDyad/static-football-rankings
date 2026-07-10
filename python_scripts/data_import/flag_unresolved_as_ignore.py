#!/usr/bin/env python3
"""
flag_unresolved_as_ignore.py

For whatever's left unresolved after autofill_from_ai.py (usually the
Low-confidence rows Gemini couldn't guess), sets Rule_Type=Ignore for the
ones that are genuine one-offs (Is_One_Off=Yes) -- so a handful of
un-resolvable clippings never block the whole batch from importing. Rows
that recur across multiple clippings are left alone and printed as a
warning, since those need a real name, not an Ignore.

This only edits the CSV -- it does NOT touch the database. The Ignore rows
stay inert until you run apply_corrections.py --final.

Fits in the pipeline right after autofill_from_ai.py:

    python master_scores_importer.py
    python gemini_alias_resolver.py
    python autofill_from_ai.py --min-confidence Medium-Low
    python flag_unresolved_as_ignore.py                      # <-- this
    python apply_corrections.py --dry-run --final             # sanity check
    python apply_corrections.py --final
    python master_scores_importer.py

Usage
-----
python flag_unresolved_as_ignore.py                # flag every remaining one-off, any confidence
python flag_unresolved_as_ignore.py --max-confidence Low   # only flag if AI confidence <= Low
python flag_unresolved_as_ignore.py --dry-run
"""

import os
import argparse
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
SUGGESTION_CSV = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv')

CONFIDENCE_ORDER = {"Low": 0, "Medium-Low": 1, "Medium": 2, "Medium-High": 3, "High": 4, "": -1}


def main():
    parser = argparse.ArgumentParser(description="Flag leftover one-off unresolved rows as Rule_Type=Ignore.")
    parser.add_argument('--input', default=SUGGESTION_CSV)
    parser.add_argument('--max-confidence', default=None,
                         choices=['High', 'Medium-High', 'Medium', 'Medium-Low', 'Low'],
                         help="Only flag rows whose AI_Confidence is at/below this tier. "
                              "Default: no confidence filter, just Final_Proper_Name blank + one-off.")
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    logger.info(f"Reading {args.input}")
    df = pd.read_csv(args.input, encoding='utf-8-sig')

    for col in ['Final_Proper_Name', 'Rule_Type', 'AI_Confidence', 'Is_One_Off']:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].fillna('')

    unresolved = (df['Final_Proper_Name'].str.strip() == '') & (df['Rule_Type'].str.strip().str.lower() != 'ignore')

    if args.max_confidence:
        ceiling = CONFIDENCE_ORDER[args.max_confidence]
        unresolved &= df['AI_Confidence'].map(lambda c: CONFIDENCE_ORDER.get(str(c).strip(), -1) <= ceiling)

    one_off_mask = unresolved & (df['Is_One_Off'].str.strip() == 'Yes')
    recurring_mask = unresolved & (df['Is_One_Off'].str.strip() != 'Yes')

    logger.info(f"{one_off_mask.sum()} row(s) will be flagged Rule_Type=Ignore (confirmed one-off).")
    for _, r in df[one_off_mask].iterrows():
        print(f"  {r['Unrecognized_Alias']}  (AI_Confidence: {r['AI_Confidence'] or 'n/a'})")

    if recurring_mask.sum():
        logger.warning(f"{recurring_mask.sum()} row(s) are still unresolved AND recur across multiple "
                        f"clippings/opponents -- NOT flagged. These need a real Final_Proper_Name, "
                        f"or a manual image check, not an Ignore:")
        for _, r in df[recurring_mask].iterrows():
            print(f"  {r['Unrecognized_Alias']}  (Source_Files: {r['Source_Files']})")

    if not one_off_mask.sum():
        logger.info("Nothing to flag.")
        return

    if args.dry_run:
        logger.info("[DRY RUN] Nothing written.")
        return

    df.loc[one_off_mask, 'Rule_Type'] = 'Ignore'

    tmp = args.input + '.tmp'
    df.to_csv(tmp, index=False, encoding='utf-8-sig')
    os.replace(tmp, args.input)
    logger.info(f"Done. {one_off_mask.sum()} row(s) set to Rule_Type=Ignore.")


if __name__ == "__main__":
    main()
