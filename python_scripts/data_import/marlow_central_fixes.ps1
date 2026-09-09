# Marlow Central (OK) three-way name-collision fix
# 37 rows reconciled via exact date/opponent/score match against real MaxPreps schedules
# for Sallisaw Central (OK) and Tulsa Central (OK) 2021 & 2022 seasons.
# Run with -DryRun switch first (add --dry-run to each line), then without.

# ===== 2021 season — Sallisaw Central (OK), 10 rows =====
python mapping_conflict_audit.py fix --id 503E82D9-B130-4259-A967-D4560995668C --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-09-02 vs Panama matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 4DB5912D-B862-4361-B919-0C0AB55E131F --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-09-10 vs Pocola matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id C36A413F-1C4C-44A1-A923-BC076313E975 --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-09-17 vs Heavener matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id A45CE765-B7E4-4E45-93E2-C36062716C41 --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-09-24 vs Colcord matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 089BB5AE-26A6-4922-944C-BD7A0483E9BA --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-01 vs Gore matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 55BAC1C2-CDEE-4D23-999F-FA750E3CDA4C --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-08 vs Warner matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 619CC0A3-8CD9-44F0-81A2-121D314CD8B1 --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-14 vs Canadian matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 904FAE11-F7BA-40A8-B1FF-A446631CD334 --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-22 vs Porter matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 4559C06D-D5ED-4AE9-96BA-C3FCCF0280CA --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-29 vs Talihina matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 5D91CD83-F673-47DA-9009-8AE77355164C --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2021-11-05 vs Hulbert matches Sallisaw Central actual schedule"

# ===== 2021 season — Tulsa Central (OK), 9 rows =====
python mapping_conflict_audit.py fix --id 586EDAA2-8480-4F71-8AA0-E8AEA944BB0E --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-08-27 vs Tulsa McLain matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id E4FB440A-9F37-4671-99E4-DD7F05095456 --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-09-03 vs Tulsa Memorial matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 4D8C81B5-0160-48AA-8665-6B2A4B1F04CD --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-09-17 vs Wewoka matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 382939B1-1864-49C3-8062-0C501A89B241 --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-09-24 vs Vinita matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 229998B4-0E95-4795-95C2-66A2B9ACC589 --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-08 vs Mannford matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id E5E0F30D-FEE4-4CC3-AFD2-27B72BC8AB80 --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-14 vs Claremore Verdigris matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id F86E51C6-D616-4C95-8879-0B780C89266D --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-22 vs Tulsa Berryhill matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id B57955FD-A575-41CF-A8F5-FAD6D0EEF18D --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-10-29 vs Inola matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 0794143A-258A-4B5B-8B94-E1872EE8010A --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2021-11-05 vs Jay matches Tulsa Central actual schedule"

# ===== 2022 season — Sallisaw Central (OK), 9 rows =====
python mapping_conflict_audit.py fix --id 68ACAB25-9CC5-4B4C-975B-71BDDA5050D7 --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-02 vs Heavener matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id E5B9D381-559C-45B4-AC86-DFA8D9F0984B --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-09 vs Warner matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 290B9E37-4A31-4CA1-A5C0-F5798DCB2E08 --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-15 vs Roland matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id F84124D3-2B0C-4321-8D98-780DCE788CFF --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-23 vs Haskell matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 17546911-E81E-4FC6-81F6-812FE73DA11B --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-30 vs Pocola matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 3AFC4E8F-E6A4-41C4-AE4E-5CDD98D7BFFA --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-10-07 vs Porter matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id E691E9E3-97DF-4900-A589-949AE3823CAC --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-10-13 vs Gore matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id 5C5B42BA-C4F4-4B64-A035-EF9D26B0DD85 --field Visitor --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-10-28 vs Panama matches Sallisaw Central actual schedule"
python mapping_conflict_audit.py fix --id C6C9E63E-27BF-4B0B-A68A-5FEBA9433DA5 --field Home    --value "Sallisaw Central (OK)" --reason "Marlow Central 3-way collision: 2022-11-03 vs Canadian matches Sallisaw Central actual schedule"

# ===== 2022 season — Tulsa Central (OK), 9 rows =====
python mapping_conflict_audit.py fix --id 05B0DBC6-92DB-48FD-B7EF-9807A6A090AD --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-08-26 vs Tulsa McLain matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 69C685D1-13EE-428C-AA42-108214ACC165 --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-02 vs Tulsa Memorial matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 71A0386C-A096-4D83-8247-EAF14FF54D45 --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-09 vs Okmulgee matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 5AC4CE49-3DE3-440F-A86B-22F1AD394446 --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-23 vs Claremore Verdigris matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 738E8886-2F1F-46E2-B260-4199290AEA02 --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-09-30 vs Tulsa Cascia Hall matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 8A6E4F9A-975B-4794-9C0A-308276E047E7 --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-10-07 vs Inola matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id D1B818F7-37D5-4909-81E0-D5C2B59EA3B5 --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-10-21 vs Dewey matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id FE1E0689-B5B6-4632-B86F-728BC4BD8861 --field Home    --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-10-28 vs Jay matches Tulsa Central actual schedule"
python mapping_conflict_audit.py fix --id 57269E01-6CBA-4D09-A2E1-0100C11A15BD --field Visitor --value "Tulsa Central (OK)" --reason "Marlow Central 3-way collision: 2022-11-03 vs Bristow matches Tulsa Central actual schedule"