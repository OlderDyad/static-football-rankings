# SOP: Suspicious Scores Review Workflow
*Last Updated: April 2026*

---

## Overview

OCR misreads from newspaper imports frequently produce impossible scores (e.g. 814, 614, 404).
These inflate the rating calculator catastrophically — a single bad score can push a team's
combined rating to 14,000+ when the all-time best is ~120. This workflow catches, quarantines,
and resolves them.

**Real-world score ceiling for reference:**
- All-time record: 256-0 (1927)
- Current filter threshold: any individual score > 100 from non-MaxPreps sources

---

## Files & Scripts

| File | Purpose |
|------|---------|
| `Suspicious_high_scores.sql` | Bulk moves flagged records from `HS_Scores` → `HS_Scores_Under_Review` |
| `Suspicious_high_scores_validated.sql` | Releases reviewed records back to `HS_Scores` (validated=1) or deletes (validated=0) |
| `review_suspicious_scores.py` | Interactive Python script to review 5 records at a time |

---

## Table: HS_Scores_Under_Review

Key columns beyond the standard `HS_Scores` columns:

| Column | Type | Meaning |
|--------|------|---------|
| `Date_Flagged` | DATETIME | When the record was moved out of HS_Scores |
| `Flag_Reason` | NVARCHAR | e.g. `Home_Score > 100` |
| `Corrected_Home_Score` | INT | Fill in if OCR misread; NULL = use original |
| `Corrected_Visitor_Score` | INT | Fill in if OCR misread; NULL = use original |
| `Review_Notes` | NVARCHAR | Free text for investigation notes |
| `Validated_Score` | BIT | **NULL** = pending, **1** = release back, **0** = delete |

---

## Workflow Steps

### Step 1 — After any newspaper import, move suspicious scores out of HS_Scores

Run **`Suspicious_high_scores.sql`**

This script:
- Finds all records where `Home_Score > 100 OR Visitor_Score > 100`
- Excludes MaxPreps sources (`Source NOT LIKE '%maxpreps%'`)
- Skips records already in `HS_Scores_Under_Review` (safe to re-run)
- Moves them to `HS_Scores_Under_Review` with a `Flag_Reason`
- Deletes them from `HS_Scores`

**⚠️ Always run this BEFORE restarting the rating calculator after an import.**

Verify it worked:
```sql
SELECT COUNT(*) FROM HS_Scores
WHERE (Home_Score > 100 OR Visitor_Score > 100)
AND Source NOT LIKE '%maxpreps%';
-- Should return 0
```

---

### Step 2 — Review records periodically using the Python script

```bash
# Activate venv first
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings
.\venv\Scripts\activate
python python_scripts\review_suspicious_scores.py
```

The script fetches 5 pending records at a time (oldest first) and presents options for each:

| Key | Action |
|-----|--------|
| Enter | Skip — leave as pending/under investigation |
| `1` | Mark as validated — will be released to HS_Scores on next run |
| `0` | Mark as bad — will be deleted on next run |
| `e` | Edit home/visitor scores, auto-calculates new margin, optionally add notes |
| `n` | Add investigation notes without changing validation state |
| `q` | Quit |

**Tips:**
- Use `e` to correct OCR misreads (e.g. 814 → 14, 404 → 40)
- Use Enter to skip records you need to research further
- You don't need to review all records before recalculating — just need them OUT of HS_Scores

---

### Step 3 — Release validated records back to HS_Scores

Run **`Suspicious_high_scores_validated.sql`**

This script:
- Re-inserts records where `Validated_Score = 1` back into `HS_Scores`
  - Uses `Corrected_Home_Score`/`Corrected_Visitor_Score` if provided, otherwise originals
  - Recalculates `Margin` correctly on insert
- Deletes records where `Validated_Score = 0` permanently
- Leaves `Validated_Score = NULL` (pending) records untouched

**Run this periodically** after review sessions — not required before every calc run.

---

## Checking What's Pending

```sql
-- How many still need review?
SELECT COUNT(*) FROM HS_Scores_Under_Review WHERE Validated_Score IS NULL;

-- See pending records
SELECT ID, Date, Season, Home, Visitor, Home_Score, Visitor_Score,
       Flag_Reason, Review_Notes
FROM HS_Scores_Under_Review
WHERE Validated_Score IS NULL
ORDER BY Date_Flagged;
```

---

## Important Warnings

- **Never run the importer and rating calculator simultaneously** — concurrent access causes
  page-level blocking and the importer will hang indefinitely on alias lookups.
- **Always COMMIT or ROLLBACK any open SSMS transactions before running the importer.**
  An uncommitted transaction on `HS_Scores` will cause the importer to hang on alias
  lookups with no obvious error message.
- **Always run Step 1 before restarting the rating calculator after any import.**
  Even one bad score (e.g. 814) will inflate an entire regional cluster of ratings.

---

## Future Expansion

The current filter catches individual scores > 100. Eventually expand to also flag:
- Total combined score > 150 (e.g. 90-80 = legitimate but suspicious)
- Margin > 150 from non-MaxPreps sources

When ready, update the WHERE clause in `Suspicious_high_scores.sql` and add new
`Flag_Reason` CASE values. The review table and Python script require no changes.