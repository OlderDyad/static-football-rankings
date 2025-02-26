import pandas as pd

# Load the cleaned CSV
csv_path = "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores_for_bulk_insert_fixed.csv"
df = pd.read_csv(csv_path, header=None)

# Print all unique values in the Future_Game column (index 8, zero-based)
print("🔍 Unique values in 'Future_Game' column:", df.iloc[:, 8].unique())
