import re

raw_text = """Record: 2-8-0   Head Coach: Curtis Smith
WK Team SC Team SC
1  3Hedleyv 52 LFort Elliottv 34
2  LNorthsidev 46 LFort Elliotty 0
9/19  *Silvertonv 68 LFort Elliottv 37
4  LMiami) 64 LFort Elliottv 19
5  LFort Elliottv 67 #Higginsv 24
6  7McLeanv 42 LFort Elliottv 27
7  nLefors) 64 LFort Elliottv 53
8  *Groomv 36 LFort Elliottv 34
10/31  LFort Elliottv 39 PSamnorwoodv 26 D
10  PFollettv 57 LFort Elliottp 8"""

games = []
lines = raw_text.split('\n')

print(f"Processing {len(lines)} lines:")
print()

for line_num, line in enumerate(lines, 1):
    line = line.strip()
    
    print(f"Line {line_num}: '{line}'")
    
    if not line or 'Record:' in line or 'WK' in line or 'Team SC' in line:
        print("  → SKIP (header/empty)")
        continue
    
    if not any(char.isdigit() for char in line):
        print("  → SKIP (no digits)")
        continue
    
    try:
        # Extract week
        week_match = re.match(r'^(\d+/?[\d]*)\s+', line)
        if week_match:
            week = week_match.group(1)
            line_after_week = line[len(week_match.group(0)):].strip()
            print(f"  Week: '{week}'")
            print(f"  After removing week: '{line_after_week}'")
        else:
            week = ''
            line_after_week = line
            print(f"  No week found")
            print(f"  Line to parse: '{line_after_week}'")
        
        # Split by scores (space before number, space after optional)
        parts = re.split(r'\s+(\d+)(?:\s+|$)', line_after_week)
        print(f"  Split parts: {parts}")
        
        if len(parts) < 4:
            print("  → SKIP (not enough parts)")
            continue
        
        team1_raw = parts[0].strip()
        score1 = int(parts[1])
        team2_raw = parts[2].strip()
        score2 = int(parts[3])
        
        print(f"  ✓ PARSED: Week={week}, Team1={team1_raw}, Score1={score1}, Team2={team2_raw}, Score2={score2}")
        games.append((week, team1_raw, score1, team2_raw, score2))
        
    except Exception as e:
        print(f"  → ERROR: {e}")
    
    print()

print("="*80)
print(f"Total games parsed: {len(games)}")
print()
for i, game in enumerate(games, 1):
    print(f"Game {i}: {game}")