#!/usr/bin/env python3
"""
edmond_oca_jv_apply.py

Applies the Edmond Oklahoma Christian Academy (OK) varsity/JV split.

Background: Edmond OCA's HS_Scores rows for 2003-2022 run at roughly 2x a
plausible varsity-only season length every year. Cross-checking each
season's DB rows against Edmond OCA's REAL varsity schedule (scraped
directly from MaxPreps -- 18 of the 20 seasons have a live schedule page;
2003 and 2022 return 404 and are excluded here entirely, left untouched)
confirms: every row that doesn't match the real varsity schedule by
(date, our_score, their_score) is a real game, just played at a
JV/sub-varsity level, imported under the same standardized name as
varsity. 221 rows across 2004-2021 fall into this category.

This script does NOT do any web scraping (the scraping was done directly
against MaxPreps and the results are baked into FLAGGED_ROWS below, since
requests from this network get blocked by MaxPreps' bot protection with
an HTTP 406). It only needs your normal DB connection.

Each row is renamed ID-scoped (never a blanket rename by team name) from
"Edmond Oklahoma Christian Academy (OK)" to
"Edmond Oklahoma Christian Academy JV (OK)" on whichever field (Home or
Visitor) currently holds the varsity name, with a full audit trail
logged to HS_Scores_Change_Log (Script='edmond_oca_jv_apply.py').

Usage:
  python edmond_oca_jv_apply.py                # dry run (default) -- prints what WOULD change
  python edmond_oca_jv_apply.py --apply         # actually applies the 221 renames
"""

import argparse
import logging

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

TEAM_NAME = "Edmond Oklahoma Christian Academy (OK)"
JV_NAME = "Edmond Oklahoma Christian Academy JV (OK)"

# (ScoresID, field-to-change, Date, Season) -- 221 rows, confirmed NOT on
# Edmond OCA's real varsity schedule for that season via MaxPreps cross-check.
FLAGGED_ROWS = [
    ('CE68CB78-8DD1-4F72-8CA4-61EF5CA3B9B4', 'Home', '2004-09-03', 2004),
    ('EA81FD6E-AD5B-4581-88D1-40EA504A4BE3', 'Home', '2004-09-10', 2004),
    ('448CA456-AD4C-482B-A929-53C95C8FB01E', 'Home', '2004-09-17', 2004),
    ('64DF0D44-C24D-4CA4-9146-FAA9B11C0826', 'Home', '2004-09-24', 2004),
    ('61A45870-39D7-4FED-9A4D-515AE58E0DB2', 'Visitor', '2004-10-01', 2004),
    ('1CE5F0DF-B0A2-4D79-8BBC-B244B02BA7B8', 'Home', '2004-10-08', 2004),
    ('37553E90-8C53-4109-9343-F589D4E9651D', 'Visitor', '2004-10-15', 2004),
    ('D4C8EFA8-5EDC-40A8-8A39-2837C8F0372F', 'Visitor', '2004-10-21', 2004),
    ('A7EDD4BE-BFD0-4D00-9FEE-6DAD59A1F8CC', 'Home', '2004-10-29', 2004),
    ('D9D70EAE-33DF-4765-9192-B8D054FF3A93', 'Home', '2004-11-05', 2004),
    ('9DA9E17C-8A9A-47D1-8742-86BEED494185', 'Visitor', '2005-09-02', 2005),
    ('217C8843-A9E6-4B8A-80B8-3B2F250D43A6', 'Visitor', '2005-09-09', 2005),
    ('1CBC9D90-51B5-4C8E-8E12-A19D50D87091', 'Home', '2005-09-16', 2005),
    ('2B061FC8-68C5-4FAD-84CE-5CEA25A19984', 'Home', '2005-09-23', 2005),
    ('41763795-A466-41F9-9132-C04BD33D3A23', 'Home', '2005-09-30', 2005),
    ('1D75EB17-5D8F-42AF-9AC9-067E800CD7CA', 'Visitor', '2005-10-07', 2005),
    ('CDA03CD3-972E-4F53-BC2F-0545BD45E0FD', 'Home', '2005-10-14', 2005),
    ('36A16E5D-D47F-40BC-A1A4-EC752C4B9292', 'Visitor', '2005-10-20', 2005),
    ('B4CF4CD1-A4CC-4DFE-B46E-99B37DEFF663', 'Home', '2005-10-28', 2005),
    ('3C8D18B0-A6C6-46D9-89B7-13B2C0AAAD88', 'Visitor', '2005-11-04', 2005),
    ('1BE18704-B31B-480E-B27A-19FAEAFEBDCB', 'Visitor', '2006-09-01', 2006),
    ('49DA049D-E6D3-4BFB-AF9F-78BC76AC1B0A', 'Home', '2006-09-08', 2006),
    ('97B0E0E5-D0C4-4C92-A2D5-400F97AB20F1', 'Home', '2006-09-15', 2006),
    ('34B7E3E2-0533-46E1-B94B-B7020CC3FAEA', 'Visitor', '2006-09-22', 2006),
    ('FEA1DEF6-B827-4FA2-8196-DF0D9B60DEF5', 'Home', '2006-09-29', 2006),
    ('B6ECE52D-1487-41F6-9FCC-D82F8810FD83', 'Visitor', '2006-10-06', 2006),
    ('9566EE9F-357B-49C6-A5BE-2159C9999217', 'Home', '2006-10-13', 2006),
    ('2BCC0639-EFFB-4980-8F8C-6A6D239DE5D2', 'Visitor', '2006-10-19', 2006),
    ('158FE06C-9F1F-44BE-982A-FE3214D628FD', 'Visitor', '2006-10-27', 2006),
    ('4A50BD03-7F62-4405-94A6-FD7934D16E45', 'Visitor', '2006-11-03', 2006),
    ('347FD265-5813-417F-88D1-8CB7CF6F4EB8', 'Home', '2006-11-10', 2006),
    ('CCD4F024-902B-4A9C-BE04-D25084C1F0DD', 'Visitor', '2007-08-31', 2007),
    ('A5F42B8E-D8A2-481F-8B03-AC7623D34D37', 'Visitor', '2007-09-07', 2007),
    ('27FC8326-6EB2-4A34-A4CD-8BF194EA7D0F', 'Visitor', '2007-09-14', 2007),
    ('0EF5258F-6413-4607-8CB0-5BF7DCE02F22', 'Home', '2007-09-21', 2007),
    ('1CB095E4-0CE3-4788-A004-04334DBE55E2', 'Visitor', '2007-09-28', 2007),
    ('FAAB0FA6-AF77-470D-850E-44D360327FDF', 'Home', '2007-10-05', 2007),
    ('337B8B34-5754-4A53-BC27-483A572EAF4D', 'Visitor', '2007-10-12', 2007),
    ('AC45FB2D-87FB-41FC-A0C9-4EF25BD77BA9', 'Home', '2007-10-19', 2007),
    ('2E2D2226-17C0-4857-A9C3-4F6106466435', 'Home', '2007-10-26', 2007),
    ('31C0DC31-3332-44FE-9C42-CAAB587846D9', 'Visitor', '2007-11-02', 2007),
    ('774458CD-DD45-4012-9630-2FEA4844A406', 'Visitor', '2007-11-09', 2007),
    ('DD77AD04-0465-458A-9DBE-D4FDEA954337', 'Visitor', '2008-09-05', 2008),
    ('2A1F3062-841E-4204-BD79-45FCBE3460F1', 'Visitor', '2008-09-12', 2008),
    ('8D515819-27E4-4000-A572-24272F85A646', 'Home', '2008-09-19', 2008),
    ('A1263600-C8E7-4809-B714-2197295EC4F7', 'Visitor', '2008-09-26', 2008),
    ('F5754C87-FEC0-4A02-B2BE-43B20CD999C6', 'Home', '2008-10-03', 2008),
    ('EDA17C45-EDAA-4BFF-B597-E316A7EE26B8', 'Home', '2008-10-10', 2008),
    ('4CF9A2EA-4FD7-4FB1-87CB-3B34E3A67CFC', 'Visitor', '2008-10-16', 2008),
    ('D9FCA5A4-2294-4A65-8101-F3A41C46231A', 'Home', '2008-10-24', 2008),
    ('ACDA99D8-B756-4D83-B46A-CAD08533F66D', 'Visitor', '2008-10-31', 2008),
    ('D8AA4AAF-FA8D-450F-9F7F-23742EE35208', 'Home', '2008-11-07', 2008),
    ('6745AAD8-903E-40DB-BCE7-3F55F550F8A4', 'Home', '2008-11-14', 2008),
    ('04A718BF-E26A-4EC5-9E27-DF87B28CD152', 'Visitor', '2008-11-21', 2008),
    ('C23A061E-42F4-4D19-8EDB-4979155E4AF7', 'Home', '2008-11-29', 2008),
    ('0B9A719E-B3EE-479D-A0C7-E734F57995E4', 'Home', '2009-09-04', 2009),
    ('97808164-217A-4D5E-87E1-51FCF8E367F0', 'Home', '2009-09-04', 2009),
    ('12AE5810-5BA9-4321-B944-1F6A0446F2D3', 'Home', '2009-09-11', 2009),
    ('42A1A12A-5CAA-4F3A-B7C2-2FFAC83F5978', 'Visitor', '2009-09-18', 2009),
    ('599869D6-BF92-4CF7-8106-E97203BD03C5', 'Home', '2009-09-25', 2009),
    ('F62F9AF6-7E88-4135-8BF0-D4B02F7BC24C', 'Visitor', '2009-10-02', 2009),
    ('63AC8CF2-68CB-48FC-B0BA-82F1167C99C8', 'Visitor', '2009-10-09', 2009),
    ('29691E06-F340-4DF0-8DE6-3B07BD7D17D8', 'Home', '2009-10-15', 2009),
    ('363034BD-88FA-466E-98EE-821CD6DA2CC1', 'Visitor', '2009-10-23', 2009),
    ('0C85824E-BC0A-44A8-BF76-C2C2BAD0D993', 'Home', '2009-10-30', 2009),
    ('C72F3839-57C2-4FC9-B7B3-F81C29E12905', 'Visitor', '2009-11-06', 2009),
    ('014B6BFC-5395-4ADA-A4F3-9ACE2424484E', 'Visitor', '2009-11-13', 2009),
    ('75FFC947-AF62-46F5-9E07-3C8269749AD7', 'Home', '2010-09-03', 2010),
    ('A5962D7B-6882-4AEB-99E3-72A0DF857AD5', 'Visitor', '2010-09-10', 2010),
    ('45A830D3-653F-457F-A5D2-C7ADAA84EFFC', 'Home', '2010-09-17', 2010),
    ('54A5BF4B-CE6E-4AD0-812D-B32AE8209DEB', 'Visitor', '2010-09-24', 2010),
    ('ABDB98B9-3F14-433A-B1F0-21A7D0F78234', 'Home', '2010-10-01', 2010),
    ('9E90A854-0057-47CB-97CE-62F1416DBC11', 'Visitor', '2010-10-08', 2010),
    ('6C4EBDC9-8463-4707-A356-33843D29C6B6', 'Home', '2010-10-15', 2010),
    ('73FCF480-1604-42B9-8D2D-70780B5F783C', 'Home', '2010-10-22', 2010),
    ('D22DD479-DF34-45B3-AC97-2633FE30EDB4', 'Home', '2010-10-29', 2010),
    ('C5C994F0-5583-43C8-B7A5-12583E340E82', 'Visitor', '2010-11-05', 2010),
    ('4EFEA57C-8AEA-4E87-BED5-18C52738F15C', 'Visitor', '2010-11-12', 2010),
    ('190AF553-D756-4EAA-85E3-3A9512FA6248', 'Visitor', '2011-09-02', 2011),
    ('D84B8D99-B89B-48DD-9286-95750A2F9B7C', 'Home', '2011-09-09', 2011),
    ('37E7DC5F-0FFF-4B5B-993D-22A0715FB037', 'Visitor', '2011-09-16', 2011),
    ('FC05F78A-5890-4057-BFBA-70CB692CAD86', 'Home', '2011-09-23', 2011),
    ('1DD23463-475C-4B77-8358-7E1CF3CC4984', 'Visitor', '2011-09-30', 2011),
    ('124577B2-4C51-4B29-9AC7-9E38DF94559F', 'Home', '2011-10-07', 2011),
    ('738A9D2E-A9EE-45F7-967D-9364F739A108', 'Home', '2011-10-14', 2011),
    ('525F7B49-3E48-44DE-BEB0-6633DEA27B81', 'Visitor', '2011-10-14', 2011),
    ('70F6B2A4-072E-497C-8316-B9B9548BD913', 'Visitor', '2011-10-21', 2011),
    ('E9959FF9-4C1B-4174-A64F-936F35A3583B', 'Visitor', '2011-10-28', 2011),
    ('EF9C011A-08E8-446E-B5BF-60FB14D0F609', 'Visitor', '2011-11-03', 2011),
    ('0A9F751F-615A-41B1-95AE-6CEF28DFD497', 'Home', '2011-11-04', 2011),
    ('CABB59D8-2344-4E26-B2B3-8BC89CA2BDB0', 'Visitor', '2011-11-11', 2011),
    ('8DF4D45F-0F49-4B45-9E2D-0E7DF9483CD0', 'Home', '2011-11-18', 2011),
    ('54E3055D-C31B-4F5D-AA64-A90B8BBDF38A', 'Visitor', '2012-08-31', 2012),
    ('BE49C34B-A99B-453A-B050-234107E6642C', 'Home', '2012-09-07', 2012),
    ('22228EDF-AA5B-45B4-A316-CA86F0BC291B', 'Home', '2012-09-14', 2012),
    ('4D600430-E541-4B30-BFA0-5BE01AACB43D', 'Visitor', '2012-09-21', 2012),
    ('FF8CEF4F-9D16-4CA0-ABFB-DB8E01121823', 'Home', '2012-09-28', 2012),
    ('FB43A0B1-732F-412B-9127-4582867A4133', 'Home', '2012-10-05', 2012),
    ('3B7361DD-B4EC-4BBA-B52F-C0DA25D67B63', 'Visitor', '2012-10-12', 2012),
    ('928AFD46-8964-4A35-9ACB-58FBC17DC5F4', 'Home', '2012-10-18', 2012),
    ('ECFE5430-20C4-4438-8643-15242E3C4FE8', 'Visitor', '2012-10-25', 2012),
    ('BA60976B-E971-423B-9F1F-D9E8583A96F9', 'Home', '2012-11-02', 2012),
    ('26C77C69-19A3-4C9B-9492-E2BCAC232EC8', 'Home', '2012-11-09', 2012),
    ('2D4DBEBC-B3C2-4CE4-AFC6-B47420D3EF05', 'Home', '2012-11-16', 2012),
    ('4061FF6D-B942-41F5-8D35-CD4066407D92', 'Home', '2012-11-23', 2012),
    ('975F83FF-059B-47DC-8FEC-C65E20A4442D', 'Home', '2012-11-30', 2012),
    ('3265CAE7-B9B6-45A3-A1D2-B4BCFBEE4252', 'Home', '2012-12-08', 2012),
    ('7DA3FC64-235D-4263-BCE4-B271E0D864AF', 'Home', '2013-09-06', 2013),
    ('8B11C635-8DE1-4164-B128-CF5C369B4C55', 'Visitor', '2013-09-13', 2013),
    ('2A53C45B-7795-4F02-B010-17FF928A5F61', 'Visitor', '2013-09-20', 2013),
    ('3F86DC71-BC2B-437A-B072-2AAE371A9515', 'Home', '2013-09-27', 2013),
    ('F9C158F4-DF9C-48CA-AAD4-9A55AA4F066A', 'Visitor', '2013-10-04', 2013),
    ('AE6DB74B-47AA-4B8C-987A-C1A910C0360A', 'Visitor', '2013-10-11', 2013),
    ('F30A0968-20E1-4CF1-8715-85103A140ACE', 'Home', '2013-10-17', 2013),
    ('A13A64FA-4409-40DC-BE4D-8277C1D9B4AD', 'Visitor', '2013-10-25', 2013),
    ('D48B01E3-18E5-45F7-B682-7E28D08D3D71', 'Home', '2013-11-01', 2013),
    ('010AC8EA-A14D-41B9-A208-3273F735DDE4', 'Visitor', '2013-11-08', 2013),
    ('261AEAF6-440C-4495-925A-D6DD5FA20E37', 'Visitor', '2013-11-15', 2013),
    ('44414303-42F4-45C6-9473-3144B712BFEA', 'Visitor', '2013-11-22', 2013),
    ('EB2F0EAE-5514-4892-923F-71761BADBC6C', 'Home', '2013-11-29', 2013),
    ('FE26E4D6-7D48-4493-AA8D-6D1F48E747A7', 'Visitor', '2014-09-05', 2014),
    ('7A9D18DB-66FE-4F86-9F8F-71AD7E04A3EB', 'Visitor', '2014-09-12', 2014),
    ('C89827FA-EC0E-4A32-AEA6-AB7B3553B24A', 'Home', '2014-09-19', 2014),
    ('04BED967-3230-4B7C-B3F9-17B5778B0E01', 'Visitor', '2014-09-26', 2014),
    ('2520A683-471A-42C6-8004-F73B15441B5D', 'Home', '2014-10-03', 2014),
    ('9CAFDF61-E82C-461E-A68E-6A0ABD124D85', 'Home', '2014-10-10', 2014),
    ('05F97228-FC49-4C45-A15E-5541BFADC18D', 'Home', '2014-10-16', 2014),
    ('77550184-8983-49E4-80D2-4C99115E6D3D', 'Visitor', '2014-10-24', 2014),
    ('C6F39156-EFE3-470C-BB32-4B4FE86F5E86', 'Home', '2014-10-31', 2014),
    ('448662EA-34FE-40AC-96A0-83F6BFAEC66A', 'Visitor', '2014-11-07', 2014),
    ('BEBA4128-5FB3-4884-865A-665995DA4163', 'Home', '2014-11-14', 2014),
    ('BB8B466C-8FEF-418E-B474-F4889953E04E', 'Home', '2014-11-21', 2014),
    ('2380760F-87B6-4286-A3B7-FD628FA401B2', 'Home', '2014-11-28', 2014),
    ('EF39F034-5E6C-4106-B139-7230E6DE844E', 'Visitor', '2014-12-05', 2014),
    ('E68BD196-F5D4-43FC-8AB3-A6D7B4407DFB', 'Home', '2015-09-04', 2015),
    ('1CB04B99-BA1C-4CF0-AC9B-C860F990FE17', 'Home', '2015-09-11', 2015),
    ('2DA85136-D345-45ED-AC56-295BB262CA50', 'Visitor', '2015-09-18', 2015),
    ('4F7ACB11-30BC-4693-8B98-001D30D9FEFB', 'Home', '2015-09-24', 2015),
    ('81892F98-FE95-45E3-B17D-054B5FBB744A', 'Visitor', '2015-10-09', 2015),
    ('D53531B9-5581-42AA-9EDE-28ADB29F1CD2', 'Visitor', '2015-10-09', 2015),
    ('D0516300-5E8F-4637-8E94-4DFD5F2D2E64', 'Visitor', '2015-10-15', 2015),
    ('876BE954-1344-4885-84DE-2FA4339823BB', 'Home', '2015-10-23', 2015),
    ('04800EEB-E85D-42AA-A963-CF17B31C6D05', 'Visitor', '2015-10-27', 2015),
    ('576243D5-1444-4424-B125-06F1A4DED25D', 'Home', '2015-10-27', 2015),
    ('FD411C54-EA8F-4FC1-92F4-173D0E979DE2', 'Visitor', '2015-10-29', 2015),
    ('0DDDDD1A-BDEA-483F-8707-CD761563D19F', 'Home', '2015-11-06', 2015),
    ('51DDD417-DDB5-410B-A530-2867F570F5A4', 'Visitor', '2015-11-13', 2015),
    ('D5705905-F0BF-47D9-8267-04EA65A5C83B', 'Home', '2016-08-26', 2016),
    ('BF82B0FF-EFEC-48FD-9448-DB5F8945B6D9', 'Visitor', '2016-09-09', 2016),
    ('D0DDA6E4-B8AF-42FF-BF3C-6A478F2168BC', 'Home', '2016-09-16', 2016),
    ('1FF04474-8540-4938-A743-944D48D2F81B', 'Visitor', '2016-09-22', 2016),
    ('894BF67D-FC44-4279-B4AF-E643A32D8FE3', 'Visitor', '2016-09-27', 2016),
    ('FD96ADF5-7FA4-428E-B0E4-B39ACB2823B3', 'Home', '2016-09-27', 2016),
    ('F8D3B795-697B-4715-A64D-0E47F85FAA38', 'Home', '2016-09-30', 2016),
    ('2CC39607-BEFF-4739-A27D-556C3BF7D7AC', 'Home', '2016-10-13', 2016),
    ('16B44C3A-EB88-4F44-9AB8-EECC902A953B', 'Visitor', '2016-10-20', 2016),
    ('4CAF3C5D-D86C-4806-BE77-5DBE53CD4D17', 'Home', '2016-10-28', 2016),
    ('909A8F01-92FC-4AE7-8DAF-F1DF2DB91BA7', 'Visitor', '2016-11-04', 2016),
    ('9B9DAC9B-DCA3-416A-95B9-C4507475583B', 'Visitor', '2016-11-11', 2016),
    ('484412D6-D108-4518-A10C-F6C408B7CEDB', 'Visitor', '2017-08-25', 2017),
    ('53750A43-993E-4D83-B091-FD6C268B10A5', 'Home', '2017-09-01', 2017),
    ('9156A56D-54C9-44F4-B4DC-5DAAC7D85B6F', 'Home', '2017-09-08', 2017),
    ('D3031755-38A1-4601-B16B-996591A47A0C', 'Visitor', '2017-09-15', 2017),
    ('06F0865A-D081-46B3-B7B3-0AE6ED920D76', 'Home', '2017-09-22', 2017),
    ('63134871-0A0D-433B-B52C-EE1FED098F96', 'Visitor', '2017-09-29', 2017),
    ('222FA740-D571-4820-A42F-4C942EA77C2D', 'Visitor', '2017-10-12', 2017),
    ('42EE5459-FA8A-42D5-8B4F-B477B0521CB1', 'Home', '2017-10-19', 2017),
    ('FDB0226A-4D33-4505-8CE1-5B4D65159498', 'Visitor', '2017-10-27', 2017),
    ('AA44A801-D02D-49B6-90DB-6B0118239393', 'Home', '2017-11-03', 2017),
    ('FFCBCE9E-EB3E-4863-8A1D-D92BBFF36DC6', 'Home', '2017-11-10', 2017),
    ('467F23F5-D4AE-49A5-B7F5-10414C9558C9', 'Home', '2017-11-17', 2017),
    ('A6A6EC92-C55C-4689-B13F-16B2A80DF33F', 'Visitor', '2017-11-24', 2017),
    ('1402CDD6-FEDF-4695-BF01-715EE954118A', 'Home', '2018-08-24', 2018),
    ('B0404A91-EB1B-4CB9-A7A2-4177143FFA14', 'Visitor', '2018-08-31', 2018),
    ('583FDB48-E962-4B32-B358-831C714E2140', 'Visitor', '2018-09-07', 2018),
    ('5595FD73-3701-4438-A33D-BC49742BD54A', 'Home', '2018-09-20', 2018),
    ('EE823DC5-ABC0-424D-8F3C-92B93FEA786C', 'Visitor', '2018-09-28', 2018),
    ('86252073-29FB-411F-BCA1-F93FE18688E4', 'Home', '2018-10-05', 2018),
    ('900A4F3A-5E7F-4E0B-BEAC-C1A20E781670', 'Visitor', '2018-10-11', 2018),
    ('03AB3AFF-00A5-4CC5-8588-E9299D9E6E1C', 'Home', '2018-10-18', 2018),
    ('C5ED3E14-1582-4F5E-A6B4-34EDC6B8120C', 'Visitor', '2018-10-26', 2018),
    ('F4E569A7-C738-4327-A25F-9BEEA8C093AC', 'Home', '2018-11-02', 2018),
    ('DDF5ED14-3D23-4331-BFCB-F8BE9C549AF8', 'Home', '2018-11-09', 2018),
    ('95C57E56-0997-4A3B-8F35-8ABEF2F7C367', 'Visitor', '2018-11-16', 2018),
    ('87D15064-3A6A-414D-AB6A-3D4C4949F9A7', 'Visitor', '2019-08-30', 2019),
    ('0F183484-7C72-4F05-8D6D-0F78BC88F4F9', 'Home', '2019-09-06', 2019),
    ('BC78B3B3-5C7E-4B29-A676-EF5AEE01FA95', 'Home', '2019-09-13', 2019),
    ('4153F384-C911-41FE-B197-D3495F477588', 'Visitor', '2019-09-27', 2019),
    ('BCCA8FF7-8C90-4F50-AA13-4FAEFC6DAA8B', 'Home', '2019-10-01', 2019),
    ('8CB7DEE4-EB64-4471-BE32-9CC79A11AA1A', 'Home', '2019-10-04', 2019),
    ('3FCC56E9-6003-440B-99D0-93C5EBE8CF73', 'Visitor', '2019-10-11', 2019),
    ('BE6C7230-9C58-4A8B-99AD-2C19F8F46BD1', 'Home', '2019-10-17', 2019),
    ('E8F612D1-DFF0-46D2-9F61-A708EDE608AF', 'Visitor', '2019-10-25', 2019),
    ('A71054E7-DD7C-4251-ACEF-27F4077F7858', 'Home', '2019-11-01', 2019),
    ('485A82C0-8605-40D6-BFA1-BE838446680C', 'Visitor', '2019-11-08', 2019),
    ('04D0E227-01B6-4370-8A6E-7E6058380EE9', 'Visitor', '2019-11-15', 2019),
    ('116EE986-A24C-4D79-B31B-8C4B99F68515', 'Home', '2020-08-28', 2020),
    ('6AB2B0B3-A0A5-413C-93D1-AEAAF0D7A2B5', 'Home', '2020-09-04', 2020),
    ('80389A88-9505-4B40-A75C-9FE8FB065D33', 'Visitor', '2020-09-25', 2020),
    ('46E2C108-2D43-4076-910B-564A88D94B2C', 'Home', '2020-10-02', 2020),
    ('8FA14EB0-05F7-4994-A41E-CC51642CA408', 'Home', '2020-10-09', 2020),
    ('B355AE13-04BF-4D1A-BDD3-8456B93ECCCF', 'Visitor', '2020-10-16', 2020),
    ('56EE1303-313D-412B-9362-E648E6414BA4', 'Visitor', '2020-10-23', 2020),
    ('FE2F295E-ECE5-4FDD-8998-CCF8E2E8CFF7', 'Home', '2020-10-30', 2020),
    ('B3625F95-6C01-4ABE-9482-48F5C2202007', 'Home', '2020-11-20', 2020),
    ('A23DA82A-BA03-4595-B32B-FF73EF9DBEF9', 'Home', '2020-11-27', 2020),
    ('C94D7A72-CD74-49C4-ADEF-CF1A9D3FA0EA', 'Visitor', '2020-12-04', 2020),
    ('8B68E31E-9259-452C-9AE9-9CB71A9B4D4B', 'Home', '2020-12-11', 2020),
    ('4A55176F-7F1F-4B28-AD94-4FA619CFABFD', 'Home', '2021-08-27', 2021),
    ('D59E2985-92DF-4FFF-9676-597788B73F42', 'Visitor', '2021-09-03', 2021),
    ('4B13ECD7-34A5-4636-805B-FAA817B3FDE6', 'Visitor', '2021-09-10', 2021),
    ('09EAE28B-3C9D-4080-AEAA-77CF03BC9406', 'Home', '2021-09-24', 2021),
    ('468349F8-991D-4FBE-B50C-0B377B50FFB3', 'Visitor', '2021-10-01', 2021),
    ('DA0FC468-5C23-46DD-8FD2-0709A0B6C00B', 'Visitor', '2021-10-08', 2021),
    ('89B13F0E-BA7E-4FB2-B807-C2B81123B8ED', 'Home', '2021-10-15', 2021),
    ('0353E200-63FF-432B-988D-1085AD06121C', 'Home', '2021-10-22', 2021),
    ('420A825D-2CA1-47EF-9A21-728F4E296ED2', 'Visitor', '2021-10-29', 2021),
    ('C580AFDC-D545-4A9C-BB16-94BE2AC45C78', 'Home', '2021-11-05', 2021),
    ('1EC01B45-372C-4580-8C04-45BE2FE6F68A', 'Home', '2021-11-12', 2021),
    ('212036B4-C28A-454D-B4D4-8EE7727EFD1E', 'Home', '2021-11-19', 2021),
    ('1A56ACEE-E2C0-4686-9FCD-779A1DCA9B06', 'Visitor', '2021-11-26', 2021),]


def apply_jv_rename(scores_id, field, reason, dry_run=True):
    with engine.begin() as conn:
        current = conn.execute(text(f"SELECT {field} AS val FROM HS_Scores WHERE ID = :id"),
                                {'id': scores_id}).fetchone()
        if current is None:
            logger.warning(f"No HS_Scores row found for ID {scores_id} -- skipped.")
            return 'missing'
        old_value = current.val

        if str(old_value) == JV_NAME:
            logger.info(f"{scores_id}: {field} already '{JV_NAME}' -- no change needed.")
            return 'already_jv'

        if old_value != TEAM_NAME:
            logger.warning(f"{scores_id}: {field} is '{old_value}', not '{TEAM_NAME}' as expected -- skipped (may have been touched by another fix already).")
            return 'unexpected'

        preview = f"{scores_id}: SET {field} = '{JV_NAME}' (was '{old_value}')"

        if dry_run:
            logger.info(f"[DRY RUN] {preview}")
            return 'would_apply'

        conn.execute(text("""
            INSERT INTO HS_Scores_Change_Log
                (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
            VALUES (:id, NULL, :field, :old, :new, :reason, :script)
        """), {'id': scores_id, 'field': field, 'old': str(old_value), 'new': JV_NAME,
               'reason': reason, 'script': 'edmond_oca_jv_apply.py'})

        conn.execute(text(f"UPDATE HS_Scores SET {field} = :new WHERE ID = :id"),
                     {'new': JV_NAME, 'id': scores_id})

    logger.info(preview + "  [logged to HS_Scores_Change_Log]")
    return 'applied'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help="Actually apply the renames (default is dry-run/review only)")
    args = parser.parse_args()

    counts = {}
    for scores_id, field, date_, season in FLAGGED_ROWS:
        reason = (f"Edmond OCA varsity/JV split: {date_} game (season {season}) not found on real "
                  f"MaxPreps varsity schedule for that season -- reclassified as JV/sub-varsity.")
        result = apply_jv_rename(scores_id, field, reason, dry_run=not args.apply)
        counts[result] = counts.get(result, 0) + 1

    print(f"\n=== {'APPLY' if args.apply else 'DRY RUN'} summary ===")
    print(f"Total rows: {len(FLAGGED_ROWS)}")
    for k, v in counts.items():
        print(f"  {k}: {v}")

    if not args.apply:
        print("\n(Dry run only -- no changes made. Re-run with --apply once you've reviewed this.)")


if __name__ == "__main__":
    main()