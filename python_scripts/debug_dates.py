import pandas as pd

try:
    df = pd.read_csv("bc_schedules.csv")
    print(f"Total rows in CSV: {len(df)}")
    
    # Print the first 5 dates exactly as Python sees them
    print("\n--- RAW DATES IN CSV ---")
    print(df['Date'].head(5))
    
    # Check specifically for the first one
    first_date = df['Date'].iloc[0]
    print(f"\nFirst Date String: '{first_date}'")
    
except Exception as e:
    print(f"Error: {e}")