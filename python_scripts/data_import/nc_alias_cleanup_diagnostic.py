"""
READ-ONLY diagnostic for three cleanup items found during the 1920s-1959 NC/SC newspaper batch.
Nothing is written to the database.

  python nc_alias_cleanup_diagnostic.py > nc_alias_cleanup_diagnostic.txt

  Part 1 - which alias rules send NC town names to the wrong state (by newspaper region)
  Part 2 - how many games ALREADY in HS_Scores are filed under the wrong-state school
  Part 3 - every spelling of Lees-McRae
  Part 4 - Weaverville-Barnardsville (VA)
"""
import pyodbc
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()
NC_PAPERS = ['The Charlotte News', 'The Charlotte Observer', 'The Greensboro Record']

def hdr(t): print('\n' + '=' * 100 + '\n' + t + '\n' + '=' * 100)

# ---------------------------------------------------------------------------------------------
hdr('PART 1. Alias rules for the problem names (ALL regions, so we see whether other papers share the problem)')
ALIASES = ['Lexington', 'Andrews', 'Farmville', 'Liberty', 'LaGrange', 'La Grange', 'Columbia', 'Bath', 'Cleveland',
           'Bennett', 'Lexington Dunbar', 'Dunbar', 'Nathanael Greene', 'Nathanael Green', 'Nathaniel Greene', 'Nat. Greene',
           'Hartsville', 'Cameron', 'Boiling Springs', 'Central', 'Hemp', 'Robbins']
for a in ALIASES:
    cur.execute("""SELECT Newspaper_Region, Standardized_Name FROM HS_Team_Name_Alias
                   WHERE Alias_Name = ? ORDER BY Newspaper_Region""", a)
    rows = cur.fetchall()
    nc = [r for r in rows if r.Newspaper_Region in NC_PAPERS or r.Newspaper_Region == '*Global*']
    other = len(rows) - len(nc)
    print(f'\n  {a!r}:  {len(rows)} rule(s) total, {other} in non-NC papers (not listed)')
    for r in nc:
        print(f'      [{r.Newspaper_Region}] -> {r.Standardized_Name}')

# ---------------------------------------------------------------------------------------------
hdr('PART 2. Games already in HS_Scores filed under a wrong-state school (opponent is an NC team)')
TARGETS = [  # (wrong team as stored, probable correct NC team)
    ('Farmville (VA)', 'Farmville (NC)'), ('LaGrange (GA)', 'LaGrange North Lenoir (NC)'),
    ('Hot Springs Bath County (VA)', 'Bath (NC)'), ('Cleveland (TN)', 'Cleveland (NC)'),
    ('Kingsport Dobyns-Bennett (TN)', 'Bennett (NC)'), ('Lexington Paul Laurence Dunbar (KY)', 'Lexington Dunbar (NC)'),
    ('Siloam Nathanael Greene Academy (GA)', 'Nathanael Greene (NC)'),
    ('Lexington (SC)', 'Lexington (NC)'), ('Liberty (SC)', 'Liberty (NC)'), ('Andrews (SC)', 'Andrews (NC)'),
    ('Columbia (SC)', 'Columbia (NC)'), ('Cameron (SC)', 'Cameron (NC)'), ('Hartsville (SC)', 'Concord Hartsell (NC)'),
]
print('  "NC-paper" = Source is a Charlotte News / Charlotte Observer / Greensboro Record clipping.')
print('  A game vs an NC opponent is only a CANDIDATE: SC and VA schools did play NC teams. Review the lists.\n')
summary = []
for wrong, right in TARGETS:
    cur.execute("""
        SELECT Season, Date, Home, Home_Score, Visitor, Visitor_Score, Source, ID
        FROM HS_Scores
        WHERE (Home = ? AND Visitor LIKE '%(NC)') OR (Visitor = ? AND Home LIKE '%(NC)')
        ORDER BY Date""", wrong, wrong)
    rows = cur.fetchall()
    papers = [r for r in rows if r.Source and any(r.Source.startswith(p.replace(' ', '_')) for p in NC_PAPERS)]
    paper_ids = {str(r.ID) for r in papers}
    cur.execute("SELECT COUNT(*), MIN(Season), MAX(Season) FROM HS_Scores WHERE Home = ? OR Visitor = ?", wrong, wrong)
    tot = cur.fetchone()
    summary.append((wrong, right, tot[0], len(rows), len(papers)))
    print(f'-- {wrong}  (all games {tot[0]}, {tot[1]}-{tot[2]})  vs NC opponent: {len(rows)}   ...of those from NC papers: {len(papers)}   -> probably {right}')
    for r in rows[:40]:
        flag = 'NCpaper' if str(r.ID) in paper_ids else '       '
        print(f'     {flag} {r.Date} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}  [{r.Source}]')
    if len(rows) > 40: print(f'     ... {len(rows) - 40} more')
print('\n  SUMMARY  wrong team | probable NC team | all games | vs NC opp | from NC papers')
for s in summary: print(f'  {s[0]:40s} {s[1]:30s} {s[2]:6} {s[3]:6} {s[4]:6}')

# does the NC target name exist yet?
print('\n  Does each probable NC name already exist?')
for _, right in TARGETS:
    cur.execute("SELECT COUNT(*) FROM HS_Team_Names WHERE Team_Name = ?", right); t = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM HS_Scores WHERE Home = ? OR Visitor = ?", right, right); g = cur.fetchone()[0]
    print(f'    {right:35s} HS_Team_Names={t}  games={g}')

# ---------------------------------------------------------------------------------------------
def name_report(pattern_list, label):
    hdr(label)
    names = set()
    for pat in pattern_list:
        cur.execute("SELECT DISTINCT Home FROM HS_Scores WHERE Home LIKE ? UNION SELECT DISTINCT Visitor FROM HS_Scores WHERE Visitor LIKE ?", pat, pat)
        names |= {r[0] for r in cur.fetchall()}
        cur.execute("SELECT Team_Name FROM HS_Team_Names WHERE Team_Name LIKE ?", pat); names |= {r[0] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT Standardized_Name FROM HS_Team_Name_Alias WHERE Standardized_Name LIKE ?", pat); names |= {r[0] for r in cur.fetchall()}
    for n in sorted(names):
        cur.execute("SELECT COUNT(*), MIN(Season), MAX(Season) FROM HS_Scores WHERE Home = ? OR Visitor = ?", n, n); g = cur.fetchone()
        cur.execute("SELECT ID FROM HS_Team_Names WHERE Team_Name = ?", n); ids = [str(r[0]) for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM HS_Team_Name_Alias WHERE Standardized_Name = ?", n); a = cur.fetchone()[0]
        print(f'  {n:45s} games={g[0]:<5} seasons={g[1]}-{g[2]}  HS_Team_Names ID={",".join(ids) or "-"}  alias rules pointing here={a}')
        cur.execute("SELECT TOP 6 Season, Home, Home_Score, Visitor, Visitor_Score FROM HS_Scores WHERE Home = ? OR Visitor = ? ORDER BY Season", n, n)
        for r in cur.fetchall(): print(f'        e.g. {r.Season} {r.Home} {r.Home_Score}-{r.Visitor_Score} {r.Visitor}')
    cur.execute("SELECT Alias_Name, Standardized_Name, Newspaper_Region FROM HS_Team_Name_Alias WHERE " +
                " OR ".join(["Alias_Name LIKE ?"] * len(pattern_list)), *pattern_list)
    print('  Alias rows whose Alias_Name matches:')
    for r in cur.fetchall(): print(f'      {r.Alias_Name!r} -> {r.Standardized_Name}  [{r.Newspaper_Region}]')

name_report(['%Lees%McRae%', '%Lees-McRae%', '%Lees McRae%', '%Lees-Mc Rae%'], 'PART 3. Every spelling of Lees-McRae')
name_report(['%Weaverville%', '%Barnardsville%'], 'PART 4. Weaverville / Barnardsville names')
