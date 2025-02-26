import pandas as pd

# Define file paths
files = [
    "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores.csv",
    "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores_fixed.csv",
    "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores_for_bulk_insert.csv",
    "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores_for_bulk_insert_final.csv",
    "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores_for_bulk_insert_fixed.csv"
]

# Read and display the first few rows of each file
for file in files:
    try:
        df = pd.read_csv(file, header=None)
        print(f"\n🔍 File: {file}")
        print(df.head())  # Print first few rows
        print(f"Columns detected: {len(df.columns)}\n")
    except Exception as e:
        print(f"\n❌ Error reading {file}: {e}")
