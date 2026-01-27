"""
Coefficient Optimization for McKnight's American Football Rankings
Finds optimal weights for Margin, WinLoss, and LogScore ratings
Works with headerless CSV files exported from SQL Server
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from datetime import datetime

# Define column names based on SQL query output order
COLUMN_NAMES = [
    'Season',
    'Date',
    'Home',
    'Visitor',
    'Home_Score',
    'Visitor_Score',
    'Margin',
    'Home_Won',
    'Home_Margin_Rating',
    'Home_WinLoss_Rating',
    'Home_Log_Rating',
    'Home_Offense_Rating',
    'Home_Defense_Rating',
    'Visitor_Margin_Rating',
    'Visitor_WinLoss_Rating',
    'Visitor_Log_Rating',
    'Visitor_Offense_Rating',
    'Visitor_Defense_Rating'
]

class CoefficientOptimizer:
    """Optimizes coefficients for predicting game margins"""
    
    def __init__(self, train_path, validation_path, holdout_path):
        """Load all datasets"""
        print("="*80)
        print("COEFFICIENT OPTIMIZATION - McKnight's American Football Rankings")
        print("="*80)
        print()
        
        print("Loading datasets (headerless CSV files from SQL Server)...")
        
        # Load without headers, assign column names
        self.train = pd.read_csv(train_path, header=None, names=COLUMN_NAMES)
        self.validation = pd.read_csv(validation_path, header=None, names=COLUMN_NAMES)
        self.holdout = pd.read_csv(holdout_path, header=None, names=COLUMN_NAMES)
        
        print(f"  Training:   {len(self.train):,} games (1950-2015)")
        print(f"  Validation: {len(self.validation):,} games (2016-2020)")
        print(f"  Holdout:    {len(self.holdout):,} games (2021-2024)")
        print()
        
        # Show sample of data to verify it loaded correctly
        print("Sample of training data (first 3 rows):")
        print(self.train[['Season', 'Home', 'Visitor', 'Margin', 'Home_Margin_Rating']].head(3))
        print()
        
        # Calculate rating differences (home - visitor)
        print("Calculating rating differences...")
        for df in [self.train, self.validation, self.holdout]:
            df['Margin_Diff'] = df['Home_Margin_Rating'] - df['Visitor_Margin_Rating']
            df['WinLoss_Diff'] = df['Home_WinLoss_Rating'] - df['Visitor_WinLoss_Rating']
            df['Log_Diff'] = df['Home_Log_Rating'] - df['Visitor_Log_Rating']
        
        # Remove any rows with missing values
        print("Removing rows with missing values...")
        train_before = len(self.train)
        val_before = len(self.validation)
        holdout_before = len(self.holdout)
        
        self.train = self.train.dropna(subset=['Margin_Diff', 'WinLoss_Diff', 'Log_Diff', 'Margin'])
        self.validation = self.validation.dropna(subset=['Margin_Diff', 'WinLoss_Diff', 'Log_Diff', 'Margin'])
        self.holdout = self.holdout.dropna(subset=['Margin_Diff', 'WinLoss_Diff', 'Log_Diff', 'Margin'])
        
        print(f"  Training:   Removed {train_before - len(self.train):,} rows ({len(self.train):,} remaining)")
        print(f"  Validation: Removed {val_before - len(self.validation):,} rows ({len(self.validation):,} remaining)")
        print(f"  Holdout:    Removed {holdout_before - len(self.holdout):,} rows ({len(self.holdout):,} remaining)")
        print()
        
        self.best_model = None
        self.best_coefficients = None
        self.holdout_tested = False
    
    def optimize_three_component(self):
        """Optimize using Margin, WinLoss, and Log ratings"""
        print("="*80)
        print("OPTIMIZATION: Margin + WinLoss + Log")
        print("="*80)
        print()
        
        # Prepare training data
        X_train = self.train[['Margin_Diff', 'WinLoss_Diff', 'Log_Diff']].values
        y_train = self.train['Margin'].values
        
        # Fit model
        print("Training linear regression model on 1950-2015 data...")
        model = LinearRegression(fit_intercept=True)
        model.fit(X_train, y_train)
        
        # Extract coefficients
        coef_margin = model.coef_[0]
        coef_winloss = model.coef_[1]
        coef_log = model.coef_[2]
        intercept = model.intercept_
        
        print("\n" + "="*80)
        print("OPTIMAL COEFFICIENTS (from training data)")
        print("="*80)
        print(f"  Margin Rating:    {coef_margin:10.6f}")
        print(f"  WinLoss Rating:   {coef_winloss:10.6f}")
        print(f"  LogScore Rating:  {coef_log:10.6f}")
        print(f"  Intercept:        {intercept:10.6f}")
        print()
        
        # Evaluate on training set
        y_pred_train = model.predict(X_train)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        train_mae = mean_absolute_error(y_train, y_pred_train)
        train_r2 = r2_score(y_train, y_pred_train)
        
        # Win prediction accuracy
        train_correct = np.sum((y_pred_train > 0) == (y_train > 0))
        train_win_acc = train_correct / len(y_train)
        
        print("TRAINING SET PERFORMANCE (1950-2015):")
        print(f"  RMSE:          {train_rmse:.2f} points")
        print(f"  MAE:           {train_mae:.2f} points")
        print(f"  R²:            {train_r2:.4f}")
        print(f"  Win Accuracy:  {train_win_acc:.1%}")
        print()
        
        # Evaluate on validation set
        X_val = self.validation[['Margin_Diff', 'WinLoss_Diff', 'Log_Diff']].values
        y_val = self.validation['Margin'].values
        y_pred_val = model.predict(X_val)
        
        val_rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
        val_mae = mean_absolute_error(y_val, y_pred_val)
        val_r2 = r2_score(y_val, y_pred_val)
        
        val_correct = np.sum((y_pred_val > 0) == (y_val > 0))
        val_win_acc = val_correct / len(y_val)
        
        print("VALIDATION SET PERFORMANCE (2016-2020):")
        print(f"  RMSE:          {val_rmse:.2f} points")
        print(f"  MAE:           {val_mae:.2f} points")
        print(f"  R²:            {val_r2:.4f}")
        print(f"  Win Accuracy:  {val_win_acc:.1%}")
        print()
        
        # Store best model
        self.best_model = model
        self.best_coefficients = {
            'margin': coef_margin,
            'winloss': coef_winloss,
            'log': coef_log,
            'intercept': intercept
        }
        
        return {
            'model': model,
            'train_rmse': train_rmse,
            'val_rmse': val_rmse,
            'coefficients': self.best_coefficients
        }
    
    def optimize_margin_only(self):
        """Test if Margin alone is sufficient"""
        print("="*80)
        print("COMPARISON: Margin Only (no WinLoss or Log)")
        print("="*80)
        print()
        
        # Prepare training data
        X_train = self.train[['Margin_Diff']].values
        y_train = self.train['Margin'].values
        
        # Fit model
        print("Training model with Margin only...")
        model = LinearRegression(fit_intercept=True)
        model.fit(X_train, y_train)
        
        coef_margin = model.coef_[0]
        intercept = model.intercept_
        
        print(f"\nCoefficient: {coef_margin:.6f}")
        print(f"Intercept:   {intercept:.6f}")
        print()
        
        # Evaluate on validation set
        X_val = self.validation[['Margin_Diff']].values
        y_val = self.validation['Margin'].values
        y_pred_val = model.predict(X_val)
        
        val_rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
        val_r2 = r2_score(y_val, y_pred_val)
        
        val_correct = np.sum((y_pred_val > 0) == (y_val > 0))
        val_win_acc = val_correct / len(y_val)
        
        print("VALIDATION SET PERFORMANCE:")
        print(f"  RMSE:          {val_rmse:.2f} points")
        print(f"  R²:            {val_r2:.4f}")
        print(f"  Win Accuracy:  {val_win_acc:.1%}")
        print()
        
        return {'val_rmse': val_rmse, 'val_r2': val_r2}
    
    def test_on_holdout(self):
        """
        Test on holdout set - ONLY RUN ONCE!
        This is THE LOCKBOX
        """
        if self.holdout_tested:
            print("ERROR: Holdout set already tested! Cannot test multiple times.")
            return None
        
        if self.best_model is None:
            print("ERROR: Must run optimization first!")
            return None
        
        print("="*80)
        print("!!! THE LOCKBOX - HOLDOUT SET TEST (2021-2024) !!!")
        print("="*80)
        print()
        print("WARNING: This is the final test. Results cannot be used to tune further.")
        print()
        
        # Prepare holdout data
        X_holdout = self.holdout[['Margin_Diff', 'WinLoss_Diff', 'Log_Diff']].values
        y_holdout = self.holdout['Margin'].values
        
        # Predict
        y_pred_holdout = self.best_model.predict(X_holdout)
        
        # Evaluate
        holdout_rmse = np.sqrt(mean_squared_error(y_holdout, y_pred_holdout))
        holdout_mae = mean_absolute_error(y_holdout, y_pred_holdout)
        holdout_r2 = r2_score(y_holdout, y_pred_holdout)
        
        holdout_correct = np.sum((y_pred_holdout > 0) == (y_holdout > 0))
        holdout_win_acc = holdout_correct / len(y_holdout)
        
        print("HOLDOUT SET PERFORMANCE:")
        print(f"  RMSE:          {holdout_rmse:.2f} points")
        print(f"  MAE:           {holdout_mae:.2f} points")
        print(f"  R²:            {holdout_r2:.4f}")
        print(f"  Win Accuracy:  {holdout_win_acc:.1%}")
        print()
        
        self.holdout_tested = True
        
        return {
            'rmse': holdout_rmse,
            'mae': holdout_mae,
            'r2': holdout_r2,
            'win_accuracy': holdout_win_acc
        }
    
    def compare_to_current(self, current_margin, current_winloss, current_log):
        """Compare optimized coefficients to current system"""
        print("="*80)
        print("COMPARISON: New vs Current Coefficients")
        print("="*80)
        print()
        
        # Prepare validation data
        X_val = self.validation[['Margin_Diff', 'WinLoss_Diff', 'Log_Diff']].values
        y_val = self.validation['Margin'].values
        
        # Current system predictions
        y_pred_current = (current_margin * X_val[:, 0] + 
                         current_winloss * X_val[:, 1] + 
                         current_log * X_val[:, 2])
        
        current_rmse = np.sqrt(mean_squared_error(y_val, y_pred_current))
        current_correct = np.sum((y_pred_current > 0) == (y_val > 0))
        current_win_acc = current_correct / len(y_val)
        
        # New system predictions
        y_pred_new = self.best_model.predict(X_val)
        new_rmse = np.sqrt(mean_squared_error(y_val, y_pred_new))
        new_correct = np.sum((y_pred_new > 0) == (y_val > 0))
        new_win_acc = new_correct / len(y_val)
        
        # Comparison
        print(f"{'Metric':<20} {'Current':<15} {'New':<15} {'Change':<15}")
        print("-" * 65)
        print(f"{'Margin Coef':<20} {current_margin:<15.6f} {self.best_coefficients['margin']:<15.6f} {self.best_coefficients['margin']-current_margin:+.6f}")
        print(f"{'WinLoss Coef':<20} {current_winloss:<15.6f} {self.best_coefficients['winloss']:<15.6f} {self.best_coefficients['winloss']-current_winloss:+.6f}")
        print(f"{'Log Coef':<20} {current_log:<15.6f} {self.best_coefficients['log']:<15.6f} {self.best_coefficients['log']-current_log:+.6f}")
        print()
        print(f"{'RMSE (points)':<20} {current_rmse:<15.2f} {new_rmse:<15.2f} {new_rmse-current_rmse:+.2f}")
        print(f"{'Win Accuracy':<20} {current_win_acc:<15.1%} {new_win_acc:<15.1%} {new_win_acc-current_win_acc:+.1%}")
        print()
        
        improvement = current_rmse - new_rmse
        if improvement > 0.5:
            print(f"✓ NEW COEFFICIENTS ARE BETTER by {improvement:.2f} points RMSE")
            print("  RECOMMENDATION: IMPLEMENT NEW COEFFICIENTS")
        elif improvement > 0:
            print(f"≈ NEW COEFFICIENTS ARE SLIGHTLY BETTER by {improvement:.2f} points RMSE")
            print("  RECOMMENDATION: Optional implementation (small improvement)")
        else:
            print(f"✗ CURRENT COEFFICIENTS ARE BETTER by {-improvement:.2f} points RMSE")
            print("  RECOMMENDATION: KEEP CURRENT COEFFICIENTS")
        print()
    
    def generate_sql_update(self):
        """Generate SQL INSERT statement for new coefficients"""
        if self.best_coefficients is None:
            print("ERROR: Must run optimization first!")
            return
        
        print("="*80)
        print("SQL UPDATE STATEMENT")
        print("="*80)
        print()
        print("Copy and paste this into SQL Server to save new coefficients:")
        print()
        print("INSERT INTO Coefficients (")
        print("    Avg_Adjusted_Margin_Coef,")
        print("    Power_Ranking_Coef_Win_Loss,")
        print("    Power_Ranking_Coef,")
        print("    Date_Calculated,")
        print("    Method_Used,")
        print("    Notes")
        print(") VALUES (")
        print(f"    {self.best_coefficients['margin']:.6f},  -- Margin")
        print(f"    {self.best_coefficients['winloss']:.6f},  -- WinLoss")
        print(f"    {self.best_coefficients['log']:.6f},  -- LogScore")
        print(f"    '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}',")
        print("    'Linear Regression on 1950-2015 training data',")
        print(f"    'Optimized {datetime.now().strftime('%Y-%m-%d')} using train/val/holdout methodology'")
        print(");")
        print()


def main():
    """Main execution"""
    
    # File paths (relative to python_scripts directory)
    base_path = r"C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files"
    train_path = f"{base_path}\\train_games_1950_2015.csv"
    validation_path = f"{base_path}\\validation_games_2016_2020.csv"
    holdout_path = f"{base_path}\\holdout_games_2021_2024.csv"
    
    # Initialize optimizer
    optimizer = CoefficientOptimizer(train_path, validation_path, holdout_path)
    
    # Run optimization
    result = optimizer.optimize_three_component()
    
    # Compare to margin-only
    print()
    optimizer.optimize_margin_only()
    
    # Compare to current coefficients if known
    print()
    print("="*80)
    print("OPTIONAL: Compare to Current Coefficients")
    print("="*80)
    print()
    print("If you know your current coefficients, enter them below.")
    print("Otherwise, press Enter to skip.")
    print()
    
    try:
        current_margin = input("Current Margin coefficient (or press Enter to skip): ").strip()
        if current_margin:
            current_margin = float(current_margin)
            current_winloss = float(input("Current WinLoss coefficient: ").strip())
            current_log = float(input("Current Log coefficient: ").strip())
            optimizer.compare_to_current(current_margin, current_winloss, current_log)
    except (ValueError, KeyboardInterrupt):
        print("\nSkipping current coefficient comparison.")
    
    # Generate SQL update
    print()
    optimizer.generate_sql_update()
    
    # Ask about holdout test
    print()
    print("="*80)
    print("HOLDOUT TEST DECISION")
    print("="*80)
    print()
    print("The holdout set (2021-2024) is THE LOCKBOX.")
    print("You should only test on it ONCE to get final performance estimate.")
    print()
    response = input("Test on holdout now? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        optimizer.test_on_holdout()
    else:
        print("\nSkipping holdout test. Run script again when ready for final evaluation.")
    
    print()
    print("="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()