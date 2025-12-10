import pandas as pd
import sys
from collections import Counter

def analyze_scorestream_data(csv_file):
    """
    Analyze scraped ScoreStream data and generate reports
    """
    print(f"📊 Analyzing: {csv_file}")
    print("="*60)
    
    df = pd.read_csv(csv_file)
    
    print(f"\n📈 BASIC STATS")
    print(f"   Total games: {len(df)}")
    print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")
    
    # Level breakdown
    print(f"\n🎯 GAMES BY LEVEL")
    level_counts = df['Level'].value_counts()
    for level, count in level_counts.items():
        pct = count / len(df) * 100
        print(f"   {level}: {count} ({pct:.1f}%)")
    
    # Teams involved
    all_teams = list(df['Host'].unique()) + list(df['Opponent'].unique())
    unique_teams = set(all_teams)
    print(f"\n🏫 TEAMS")
    print(f"   Unique teams: {len(unique_teams)}")
    
    # Most common teams
    team_counts = Counter(all_teams)
    print(f"\n   Top 10 Most Common Teams:")
    for team, count in team_counts.most_common(10):
        print(f"      {team}: {count} games")
    
    # JV teams
    jv_teams = [t for t in unique_teams if 'JV' in t or 'Jv' in t]
    if jv_teams:
        print(f"\n🔰 JV TEAMS ({len(jv_teams)} found)")
        for team in sorted(jv_teams)[:20]:
            print(f"      {team}")
    
    # Check for duplicate games
    print(f"\n🔍 DATA QUALITY")
    
    # Games with missing scores
    missing_scores = df[(df['Score1'] == '') | (df['Score2'] == '')]
    if len(missing_scores) > 0:
        print(f"   ⚠️ Games with missing scores: {len(missing_scores)}")
    
    # Games with 0-0 scores (might be upcoming/unplayed)
    zero_scores = df[(df['Score1'] == '0') & (df['Score2'] == '0')]
    if len(zero_scores) > 0:
        print(f"   ⚠️ Games with 0-0 score: {len(zero_scores)} (may be unplayed)")
    
    # Potential duplicates (same teams, same date)
    df_check = df.copy()
    df_check['team_pair'] = df_check.apply(
        lambda x: tuple(sorted([x['Host'], x['Opponent']])), axis=1
    )
    duplicates = df_check[df_check.duplicated(['team_pair', 'Date'], keep=False)]
    if len(duplicates) > 0:
        print(f"   ⚠️ Potential duplicate games: {len(duplicates)}")
        print(f"      (Same teams playing on same date)")
    
    # State/Province distribution (if location in name)
    states = []
    for team in unique_teams:
        if '(' in team:
            state = team.split('(')[-1].replace(')', '').strip()
            states.append(state)
    
    if states:
        print(f"\n🗺️  GEOGRAPHIC DISTRIBUTION")
        state_counts = Counter(states)
        for state, count in state_counts.most_common(10):
            print(f"   {state}: {count} teams")
    
    print("\n" + "="*60)
    return df

def create_varsity_jv_splits(df, output_prefix="cleaned"):
    """
    Create separate files for varsity and JV games
    """
    varsity_df = df[df['Level'] == 'Varsity'].copy()
    jv_df = df[df['Level'] == 'JV'].copy()
    
    if len(varsity_df) > 0:
        varsity_file = f"{output_prefix}_varsity.csv"
        varsity_df.to_csv(varsity_file, index=False)
        print(f"✅ Varsity games saved: {varsity_file} ({len(varsity_df)} games)")
    
    if len(jv_df) > 0:
        jv_file = f"{output_prefix}_jv.csv"
        jv_df.to_csv(jv_file, index=False)
        print(f"✅ JV games saved: {jv_file} ({len(jv_df)} games)")
    
    return varsity_df, jv_df

def remove_duplicates(df):
    """
    Remove duplicate games (same teams, same date, but keep better scored entries)
    """
    print("\n🧹 CLEANING DUPLICATES")
    original_count = len(df)
    
    # Create team pair identifier
    df['team_pair'] = df.apply(
        lambda x: tuple(sorted([x['Host'], x['Opponent']])), axis=1
    )
    
    # Sort by: date, team_pair, then prioritize rows WITH scores
    df['has_score'] = df.apply(
        lambda x: 1 if (x['Score1'] != '' and x['Score2'] != '') else 0, axis=1
    )
    
    df_sorted = df.sort_values(['Date', 'team_pair', 'has_score'], ascending=[True, True, False])
    
    # Keep first occurrence (which will have score if one exists)
    df_clean = df_sorted.drop_duplicates(['team_pair', 'Date'], keep='first')
    
    # Remove helper columns
    df_clean = df_clean.drop(['team_pair', 'has_score'], axis=1)
    
    removed = original_count - len(df_clean)
    print(f"   Removed {removed} duplicate games")
    print(f"   Remaining: {len(df_clean)} games")
    
    return df_clean

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_scorestream_data.py <csv_file>")
        print("\nExample: python analyze_scorestream_data.py scorestream_games_20241208_143022.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    # Analyze
    df = analyze_scorestream_data(csv_file)
    
    # Clean
    df_clean = remove_duplicates(df)
    
    # Split by level
    print("\n📂 CREATING SPLIT FILES")
    varsity_df, jv_df = create_varsity_jv_splits(df_clean, "cleaned")
    
    # Save cleaned full file
    clean_file = "cleaned_all_levels.csv"
    df_clean.to_csv(clean_file, index=False)
    print(f"✅ All cleaned games: {clean_file}")
    
    print("\n✨ Analysis complete!")

if __name__ == "__main__":
    main()
