WRONG=[('Chicago Parker','Paris'),('Avon','Aurora West'),('East St. Louis Lincoln','Lincoln'),('Carbondale University High','Tolono Unity'),('Chicago Washington','Washington'),
('Paris','Pana Coop'),('Aurora Waubonsie Valley','Fairview Valley'),('Decatur Eisenhower','Blue Island Eisenhower'),('Barry Western Community','Buda Western'),
('Newman','Sterling Newman Central Catholic'),('Chicago St. Joseph','Westchester St. Joseph'),('Niantic Sangamon Valley','London Mills Spoon River Valley'),('Monmouth','Alexis United'),
('Alton Marquette Catholic','Ottawa Marquette Academy'),('River Forest Trinity','Bloomington Trinity'),('Michigantown Clinton Central (IN)','Clinton (IN)'),
('Cleveland Midway (MO)','Saint Louis Cleveland (MO)'),('Mount Carmel','Chicago Mt. Carmel')]
ALIAS=[('Wheaton Warrenville','Wheaton Warrenville South'),('St. Jacob-Triad','Troy Triad')]
C='''Momence|Momence Coop;Forrest|Forrest-Strawn-Wing;Toulon|Toulon Stark County;Gilman|Gilman Iroquois;Manlius|Manlius Bureau Valley;Fairbury Prairie Central|Fairbury-Cropsey;
Tiskilwa|Tiskilwa Crossroads;Albion|Albion Edwards County;Minonk Fieldcrest|Minonk-Dana-Rutland;Flora Coop|Flora-North Clay;Bridgeport|Bridgeport Red Hill;Sparta|Sparta-Steeleville;
Wyoming Community|Wyoming Stark County;Saybrook|Saybrook-Arrowsmith;Mahomet|Mahomet-Seymour;Meredosia|Meredosia-Chambersburg;Kempton|Kempton-Cabery;White Hall|White Hall North Greene;
Petersburg|Petersburg PORTA;Albion Edwards County|Albion Edwards County-Grayville;Deer Creek|Deer Creek-Mackinaw;Farmer City Blue Ridge|Farmer City-Mansfield;Warrensburg|Warrensburg-Latham;
Biggsville|Biggsville Union;Mulkeytown Zeigler-Royalton|Zeigler-Royalton;DeLand|DeLand-Weldon;Sesser|Sesser-Valier;Abingdon|Abingdon-Avon;Cerro Gordo|Cerro Gordo-DeLand-Weldon-Bement;
Greenfield|Greenfield-Northwestern Coop;Hoopeston|Hoopeston-East Lynn;Villa Grove|Villa Grove-Heritage;Northwestern Coop|Sciota Northwestern;Arthur|Arthur Lovington Atwood Hammond;
Minonk-Dana|Minonk-Dana-Rutland;Gibson City|Gibson City-Melvin-Sibley;Bradley|Bradley-Bourbonnais Community;Jerseyville|Jerseyville Jersey;Lewistown|Lewistown Community;Joliet|Joliet Township;
Champaign|Champaign Central;Decatur|Decatur Stephen Decatur;Wheaton|Wheaton Central;Chicago Woodlawn|University of Chicago Charter;Olympia Fields Rich Central|Olympia Fields Rich Township;
Chicago International Charter-Longwood Academy|Chicago Longwood;Chicago Ellison|Chicago International Charter-Ellison;
Arlington Christian Liberty Academy-Christian Heritage Academy|Arlington Heights Christian Liberty Academy;Chillicothe Illinois Valley Central|Chillicothe Township;Farmington|Farmington East;
Northbrook Glenbrook North|Northfield Township Glenbrook;Frankfort Lincoln-Way|New Lenox Lincoln-Way Central;Franklin Park-Northlake Leyden|Northlake Leyden'''
COOP=[tuple(p.strip().split('|')) for p in C.replace('\n','').split(';')]
