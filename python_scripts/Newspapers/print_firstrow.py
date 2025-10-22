import pandas as pd

# Load the cleaned CSV
csv_path = "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores_for_bulk_insert_fixed.csv"
df = pd.read_csv(csv_path, header=None)

# Print first few rows
print("🔍 First few rows of CSV:")
print(df.head())
