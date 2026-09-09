# Edmond OCA 2022 "season" duplicate-import cleanup
# 11 rows in Season=2022 are exact date(month/day)+score duplicates of real
# 2021 games -- the real game already exists correctly under Season=2021,
# these are spurious re-imports mislabeled a year off. Confirmed by
# comparing all 23 "2022" rows against all 24 "2021" rows for Edmond OCA:
# 11 match exactly, 12 are genuinely distinct games (left untouched).
# Run --dry-run first, then for real.

python mapping_conflict_audit.py delete --id ADF406E6-91F4-42A2-BD4E-8BA24C88A3AE --reason "Duplicate import: 2022-09-03 vs Sayre 62-13 exactly matches real 2021-09-03 game (ID 466689FE-5414-475E-999E-A7090E5EF969), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id FECB591B-D24C-4FFE-8E1B-9C993BF875E1 --reason "Duplicate import: 2022-09-11 vs Elk City Merritt 34-0 exactly matches real 2021-09-11 game (ID F6EC2814-8762-46B8-A490-B78F3D566202), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id EC038C02-83A5-4E53-9E79-928454A90C91 --reason "Duplicate import: 2022-09-17 vs Stratford 33-14 exactly matches real 2021-09-17 game (ID 232925DC-1883-4C81-AE3C-AFE729E149FD), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id E5230B97-EBEE-4381-975C-384E3414EC97 --reason "Duplicate import: 2022-09-24 vs Hinton 18-16 exactly matches real 2021-09-24 game (ID 980DB754-4BC4-4C0F-BE14-AAE0B866DD9B), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id 2C54CCAC-D130-451C-9A74-B3181DF3D7DA --reason "Duplicate import: 2022-10-01 vs Cashion 28-39 exactly matches real 2021-10-01 game (ID E98CC556-F0B4-4B6A-8A52-D78AEF54DA8F), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id CE394B14-BE74-4A1F-9FD0-636ACACC8D73 --reason "Duplicate import: 2022-10-08 vs Shawnee North Rock Creek 42-0 exactly matches real 2021-10-08 game (ID 819356EB-FB64-4B5C-8935-801706626D7A), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id 58A27893-4E8A-4269-A019-BA2C3037F9FE --reason "Duplicate import: 2022-10-14 vs Tonkawa 12-47 exactly matches real 2021-10-14 game (ID F496BCD9-E9F2-4319-9D3B-C0312DE4F88E), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id 3EAA9493-EF48-4E3B-B8F8-EDDCAF2030A2 --reason "Duplicate import: 2022-10-22 vs Crescent 34-28 exactly matches real 2021-10-22 game (ID BBE3B91A-F1B2-464F-848A-B04A31AABC64), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id AE966670-2F6B-46C7-893F-0FFDB81AB3E9 --reason "Duplicate import: 2022-10-28 vs Watonga 23-22 exactly matches real 2021-10-28 game (ID 1BAB20E7-A03F-4D9D-AB5F-820011691FF4), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id B9D6A5F7-13D6-429C-BC64-6DC1728146E8 --reason "Duplicate import: 2022-11-04 vs Fairfax Woodland 13-44 exactly matches real 2021-11-04 game (ID AC9EC686-618F-4339-A502-EB4871E21A09), mislabeled Season=2022"
python mapping_conflict_audit.py delete --id 45AEE2C5-357F-4853-96A9-C51F789579AA --reason "Duplicate import: 2022-11-12 vs Elmore City-Pernell 20-42 exactly matches real 2021-11-12 game (ID 82D79B1F-2EB1-4F04-931F-1A641D8A3C9B), mislabeled Season=2022"