"""
ks_8man_classifier.py
Identifies KS 8-man programs using network analysis from a known anchor team.
Strategy: 
  1. Start with confirmed 8-man anchor (Stockton)
  2. Find all opponents across all seasons
  3. For each opponent, calculate what % of THEIR games are against 
     known 8-man teams
  4. Flag teams above threshold as likely 8-man
  5. Iterate to expand the network
"""
import pyodbc
import pandas as pd
from collections import defaultdict

# --- CONFIGURATION ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
STATE = "KS"
ANCHOR_TEAMS = [
    # Division I (previously confirmed)
    'Stockton (KS)',
    'Dighton (KS)',
    'Meade (KS)',
    'Ness City (KS)',
    'WaKeeney Trego (KS)',
    'Rock Hills (KS)',
    'Macksville (KS)',
    'Shawnee Maranatha Christian Academy (KS)',
    'Rosalia Flinthills (KS)',
    'Solomon (KS)',
    'Cedar Vale-Dexter (KS)',
    'Spearville (KS)',
    'Montezuma South Gray (KS)',
    'Pretty Prairie (KS)',
    'Greensburg Kiowa County (KS)',
    'Goessel (KS)',
    'Udall (KS)',
    'Leoti Wichita County (KS)',
    'Moundridge (KS)',
    'Brookville Ell-Saline (KS)',
    'Hoxie (KS)',
    'Howard West Elk (KS)',
    'Hill City (KS)',
    'Topeka Cair Paravel (KS)',
    'Clyde Clifton-Clyde (KS)',
    'Little River (KS)',
    'Cottonwood Falls Chase County (KS)',
    'Madison-Hamilton (KS)',
    'Attica-Argonia (KS)',
    'Lincoln (KS)',
    'Burlingame (KS)',
    'Sublette (KS)',
    'Oxford (KS)',
    'Herington (KS)',
    'Ransom Western Plains (KS)',
    'Osborne (KS)',
    'Tribune Greeley County (KS)',
    # Division II additions
    'Axtell (KS)',
    'Frankfort (KS)',
    'Southern Cloud co-op [Miltonvale-Glasco] (KS)',  # South Central
    'Victoria (KS)',
    'Bel Aire Sunrise Christian Academy (KS)',
    'Kiowa South Barber (KS)',
    'Minneola (KS)',
    'Kinsley (KS)',
    'Hanover (KS)',
    'Canton-Galva (KS)',
    'Sylvan Grove Sylvan-Lucas (KS)',
    'Claflin Central Plains (KS)',
    'Sharon Springs Wallace County (KS)',
    'Lebo (KS)',
    'Hutchinson Central Christian (KS)',
    'Jetmore Hodgeman County (KS)',
    'Bucklin (KS)',
    'Moran Marmaton Valley (KS)',
    'Randolph Blue Valley (KS)',
    'Kensington Thunder Ridge (KS)',
    'Rural Vista [Hope-White City] (KS)',
    'Wichita HomeSchool (KS)',
    'Downs Lakeside (KS)',
    'Saint Paul (KS)',
    'Colony Crest (KS)',
    'Linn (KS)',
    'Saint John (KS)',
    'Norwich (KS)',
    'Saint Francis (KS)',
    'Beloit St. John\'s-Tipton Catholic (KS)',
    'Topeka Cair Paravel (KS)',  # Life Prep equivalent
    'Stafford (KS)',
    'Logan-Palco (KS)',
    'Otis-Bison (KS)',
    'Wakefield (KS)',
    'Langdon Fairfield (KS)',
    'Satanta (KS)',
    'Highland Doniphan West (KS)',
    'Hartford (KS)',
    'Scandia Pike Valley (KS)',
    'Topeka Cornerstone Family (KS)',
    'Melvern Marais Des Cygne Valley (KS)',
    'Grainfield Wheatland-Grinnell (KS)',
]
THRESHOLD = 0.55
MIN_GAMES = 5
SEASON_START = 1990
SEASON_END = 2024

conn_str = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
)

def get_all_ks_games():
    """Pull all KS games in the analysis window."""
    query = f"""
        SELECT Season, Home, Visitor
        FROM dbo.HS_Scores
        WHERE (Home LIKE '%(KS)' OR Visitor LIKE '%(KS)')
          AND Season BETWEEN {SEASON_START} AND {SEASON_END}
    """
    with pyodbc.connect(conn_str) as conn:
        return pd.read_sql(query, conn)

def get_opponents(team, games_df):
    """Get all opponents for a team."""
    home_games = games_df[games_df['Home'] == team]['Visitor']
    away_games = games_df[games_df['Visitor'] == team]['Home']
    return pd.concat([home_games, away_games])

def classify_network(games_df, anchor_teams, threshold, min_games, iterations=3):
    """
    Iteratively expand the 8-man network from anchor teams.
    Returns dict of {team: confidence_score}
    """
    # Start with anchors as confirmed 8-man
    confirmed_8man = set(anchor_teams)
    all_ks_teams = set(
        games_df[games_df['Home'].str.endswith('(KS)')]['Home'].tolist() +
        games_df[games_df['Visitor'].str.endswith('(KS)')]['Visitor'].tolist()
    )
    
    results = {}
    
    for iteration in range(iterations):
        print(f"\n--- Iteration {iteration + 1} ---")
        print(f"Known 8-man teams: {len(confirmed_8man)}")
        newly_confirmed = set()
        
        for team in all_ks_teams:
            if team in confirmed_8man:
                continue
                
            opponents = get_opponents(team, games_df)
            total_games = len(opponents)
            
            if total_games < min_games:
                continue
            
            # Count games against known 8-man teams
            games_vs_8man = opponents.isin(confirmed_8man).sum()
            score = games_vs_8man / total_games
            
            results[team] = {
                'score': round(score, 3),
                'games_vs_8man': int(games_vs_8man),
                'total_games': int(total_games),
                'flagged': score >= threshold
            }
            
            if score >= threshold:
                newly_confirmed.add(team)
        
        if not newly_confirmed:
            print("Network stable - no new teams found.")
            break
            
        confirmed_8man.update(newly_confirmed)
        print(f"Newly flagged this iteration: {len(newly_confirmed)}")
        for t in sorted(newly_confirmed):
            print(f"  {t}: {results[t]['score']:.0%} of games vs 8-man")
    
    return confirmed_8man, results

def main():
    print("Loading KS games...")
    games_df = get_all_ks_games()
    print(f"Loaded {len(games_df):,} games")
    
    confirmed_8man, results = classify_network(
        games_df, ANCHOR_TEAMS, THRESHOLD, MIN_GAMES
    )
    
    # Build output dataframe
    rows = []
    for team, data in sorted(results.items(), key=lambda x: -x[1]['score']):
        rows.append({
            'TeamName': team,
            'Pct_vs_8man': f"{data['score']:.0%}",
            'Games_vs_8man': data['games_vs_8man'],
            'Total_Games': data['total_games'],
            'Likely_8man': 'YES' if data['flagged'] else 'no',
            'In_Confirmed_Set': 'YES' if team in confirmed_8man else 'no'
        })
    
    df_out = pd.DataFrame(rows)
    
    # Save results
    output_path = (
        "C:/Users/demck/OneDrive/Football_2024/"
        "static-football-rankings/excel_files/"
        "State_Aliases_ProperNames/KS_8man_candidates.csv"
    )
    df_out.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")
    
    # Print summary
    likely_8man = df_out[df_out['Likely_8man'] == 'YES']
    print(f"\n{'='*50}")
    print(f"SUMMARY: {len(confirmed_8man)} total 8-man programs identified")
    print(f"  - {len(ANCHOR_TEAMS)} anchor teams")
    print(f"  - {len(confirmed_8man) - len(ANCHOR_TEAMS)} network-identified")
    print(f"\nTop candidates by % games vs 8-man:")
    print(df_out.head(30).to_string(index=False))
    
    # Also flag Hill City transition separately
    print(f"\n--- Hill City transition check ---")
    hc_games = games_df[
        (games_df['Home'] == 'Hill City (KS)') | 
        (games_df['Visitor'] == 'Hill City (KS)')
    ]
    print(f"Hill City games by season:")
    for season in sorted(hc_games['Season'].unique()):
        season_games = hc_games[hc_games['Season'] == season]
        opps = pd.concat([
            season_games[season_games['Home'] == 'Hill City (KS)']['Visitor'],
            season_games[season_games['Visitor'] == 'Hill City (KS)']['Home']
        ])
        pct_8man = opps.isin(confirmed_8man).mean()
        print(f"  {season}: {len(opps)} games, {pct_8man:.0%} vs 8-man opponents")

if __name__ == "__main__":
    main()