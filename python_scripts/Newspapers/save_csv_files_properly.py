import pandas as pd

# ✅ Load CSV with explicit encoding & remove blank lines
csv_path = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged\cleaned_scores_for_bulk_insert_final.csv"
df = pd.read_csv(csv_path, header=None, encoding="utf-8", skip_blank_lines=True)

# ✅ Ensure exactly 17 columns
expected_columns = 17
if df.shape[1] != expected_columns:
    print(f"⚠️ Warning: CSV has {df.shape[1]} columns instead of {expected_columns}. Verify structure.")

# ✅ Save cleaned file
cleaned_csv_path = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged\cleaned_scores_fixed.csv"
df.to_csv(cleaned_csv_path, index=False, header=False, encoding="utf-8", lineterminator="\n")

print(f"✅ Cleaned CSV re-saved at: {cleaned_csv_path}")
