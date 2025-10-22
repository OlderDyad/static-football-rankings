import pandas as pd

# Load the CSV file
csv_path = "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged/cleaned_scores_for_bulk_insert_fixed.csv"
df = pd.read_csv(csv_path, header=None)

# Print first 5 rows and columns
print("🔍 First few rows of CSV:")
print(df.head())

# Print number of columns detected
print(f"🛠 Detected Columns: {df.shape[1]}")
