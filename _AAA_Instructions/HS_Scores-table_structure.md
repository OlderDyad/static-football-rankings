Here are all the tables and columns that have a direct relationship back to dbo.HS_Team_Names.ID (or Team_Name):

games: source_team_id, opponent_team_id

DataQualityNotes: TeamID

HS_Team_MaxPreps: Team_ID

HS_Team_Media: Team_ID

AlternateNames: Team_ID

HS_TeamSeason: TeamID (Appears twice with different constraint names, but same table/column)

HSTeamSeasons: TeamID

team_scraping_status: team_id

TeamConferenceMembership: Team_Name (References Team_Name, not ID)

HS_Scores Schema:
COLUMN_NAME	ORDINAL_POSITION	DATA_TYPE	IS_NULLABLE	CHARACTER_MAXIMUM_LENGTH	NUMERIC_PRECISION	NUMERIC_SCALE
Date	1	date	YES	NULL	NULL	NULL
Season	2	int	YES	NULL	10	0
Home	3	varchar	YES	111	NULL	NULL
Visitor	4	varchar	YES	111	NULL	NULL
Neutral	5	bit	YES	NULL	NULL	NULL
Location	6	varchar	YES	111	NULL	NULL
Location2	7	varchar	YES	255	NULL	NULL
Line	8	int	YES	NULL	10	0
Future_Game	9	bit	YES	NULL	NULL	NULL
Source	10	varchar	YES	255	NULL	NULL
Date_Added	11	datetime	YES	NULL	NULL	NULL
OT	12	int	YES	NULL	10	0
Forfeit	13	bit	YES	NULL	NULL	NULL
ID	14	uniqueidentifier	NO	NULL	NULL	NULL
Visitor_Score	15	int	YES	NULL	10	0
Home_Score	16	int	YES	NULL	10	0
Margin	17	int	YES	NULL	10	0
BatchID	18	int	YES	NULL	10	0
Access_ID	19	varchar	YES	255	NULL	NULL