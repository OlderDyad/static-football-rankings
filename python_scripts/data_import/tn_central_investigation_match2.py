import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

# The table has no direct ScoresID link -- it's keyed by AnchorTeam/Season/GhostTeamCandidate instead.
# Pull every registered investigation for Knoxville Central and print full detail so we can match
# by season + opponent name against our 35 confirmed rows.
cur.execute("""
    SELECT InvestigationID, AnchorTeam, State, Season, DateIdentified, Status, GhostTeamCandidate,
           ProbableCorrectOpponent, VerificationSource, Notes, MinDaysApart, ScoreMatchFlag,
           Priority, AnchorScoreOnlyMatch, ConflictType, ProposedCorrection
    FROM HS_Mapping_Investigations
    WHERE AnchorTeam = 'Knoxville Central (TN)' AND State = '(TN)'
    ORDER BY Season, InvestigationID
""")
rows = cur.fetchall()
cols = [d[0] for d in cur.description]
print(f'Found {len(rows)} registered investigations for Knoxville Central (TN):')
print()
for r in rows:
    d = dict(zip(cols, r))
    print(f"  InvestigationID={d['InvestigationID']}  Season={d['Season']}  Status={d['Status']}  ConflictType={d['ConflictType']}")
    print(f"    GhostTeamCandidate={d['GhostTeamCandidate']!r}  ProbableCorrectOpponent={d['ProbableCorrectOpponent']!r}")
    print(f"    DateIdentified={d['DateIdentified']}  MinDaysApart={d['MinDaysApart']}  ScoreMatchFlag={d['ScoreMatchFlag']}  Priority={d['Priority']}")
    print(f"    Notes={d['Notes']!r}")
    print(f"    ProposedCorrection={d['ProposedCorrection']!r}")
    print()
