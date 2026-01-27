"""
Quick test: Margin-only vs 3-component on holdout
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

# Column names
COLUMN_NAMES = [
    'Season', 'Date', 'Home', 'Visitor', 'Home_Score', 'Visitor_Score', 'Margin', 'Home_Won',
    'Home_Margin_Rating', 'Home_WinLoss_Rating', 'Home_Log_Rating', 'Home_Offense_Rating', 'Home_Defense_Rating',
    'Visitor_Margin_Rating', 'Visitor_WinLoss_Rating', 'Visitor_Log_Rating', 'Visitor_Offense_Rating', 'Visitor_Defense_Rating'
]

# Load data
print("Loading datasets...")
train = pd.read_csv(r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\train_games_1950_2015.csv", 
                    header=None, names=COLUMN_NAMES)
holdout = pd.read_csv(r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\holdout_games_2021_2024.csv", 
                      header=None, names=COLUMN_NAMES)

# Calculate differences
train['Margin_Diff'] = train['Home_Margin_Rating'] - train['Visitor_Margin_Rating']
holdout['Margin_Diff'] = holdout['Home_Margin_Rating'] - holdout['Visitor_Margin_Rating']

# Remove missing
train = train.dropna(subset=['Margin_Diff', 'Margin'])
holdout = holdout.dropna(subset=['Margin_Diff', 'Margin'])

# Train Margin-only model
print("\n" + "="*80)
print("MARGIN-ONLY MODEL")
print("="*80)
X_train = train[['Margin_Diff']].values
y_train = train['Margin'].values

model = LinearRegression(fit_intercept=True)
model.fit(X_train, y_train)

print(f"\nCoefficient: {model.coef_[0]:.6f}")
print(f"Intercept:   {model.intercept_:.6f}")

# Test on holdout
X_holdout = holdout[['Margin_Diff']].values
y_holdout = holdout['Margin'].values
y_pred = model.predict(X_holdout)

rmse = np.sqrt(mean_squared_error(y_holdout, y_pred))
r2 = r2_score(y_holdout, y_pred)
win_acc = np.sum((y_pred > 0) == (y_holdout > 0)) / len(y_holdout)

print("\nHOLDOUT PERFORMANCE (2021-2024):")
print(f"  RMSE:          {rmse:.2f} points")
print(f"  R²:            {r2:.4f}")
print(f"  Win Accuracy:  {win_acc:.1%}")

print("\n" + "="*80)
print("COMPARISON")
print("="*80)
print(f"Margin-Only:   RMSE = {rmse:.2f}")
print(f"3-Component:   RMSE = 13.21")
print(f"Difference:    {13.21 - rmse:+.2f} points")
print()

if rmse < 13.21:
    diff = 13.21 - rmse
    print(f"✓ MARGIN-ONLY IS BETTER by {diff:.2f} points!")
    print("  RECOMMENDATION: Use Margin-only formula")
    print(f"  Combined Rating = {model.coef_[0]:.6f} × Margin + {model.intercept_:.6f}")
else:
    diff = rmse - 13.21
    print(f"✗ 3-COMPONENT IS BETTER by {diff:.2f} points")
    print("  RECOMMENDATION: Use 3-component formula")
    print("  Combined Rating = 1.041×Margin - 1.470×WinLoss - 0.346×Log + 2.942")