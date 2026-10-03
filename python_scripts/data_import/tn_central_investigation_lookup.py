import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

# The 35 confirmed "Central ambiguity" rows from the generalized check, with their
# verdict and (for relabel candidates) the correct target team name.
rows = [
    # (ScoresID, Date, Season, Verdict, CorrectCentralTarget)
    ('15C3E2D1-05AC-46DC-9956-D03D01A27677', '1926-09-24', 1926, 'RELABEL', 'Chattanooga Central (TN)'),
    ('25E5DB64-E28F-4B80-8F94-8B43F29FB97B', '1926-09-24', 1926, 'RELABEL', 'Nashville Central (TN)'),
    ('C17182B5-D020-4EC6-8D13-D5488A476F25', '1942-09-04', 1942, 'RELABEL', 'Nashville Central (TN)'),
    ('A32974B1-ACA6-4BBC-A274-0A239245F264', '1943-10-09', 1943, 'RELABEL', 'Nashville Central (TN)'),
    ('DBC1E9C2-BFA2-45F3-80E8-CF7ABFFAA302', '1943-10-16', 1943, 'RELABEL', 'Columbia Central (TN)'),
    ('D1D5A00E-8427-4E62-A81B-02E5F836F025', '1943-10-16', 1943, 'RELABEL', 'Nashville Central (TN)'),
    ('58CB1E80-3BED-4A2B-854E-ACC6003CCA12', '1946-10-05', 1946, 'RELABEL', 'Nashville Central (TN)'),
    ('71FA54F6-1AAE-4669-8533-351A16B51EB5', '1946-10-19', 1946, 'RELABEL', 'Memphis Central (TN)'),
    ('7EE1E2A8-4E71-4CFE-8411-8131458AEFC1', '1947-09-05', 1947, 'RELABEL', 'Chattanooga Central (TN)'),
    ('4061AE54-B808-401F-B69E-100CC4CC9FC1', '1947-10-18', 1947, 'RELABEL', 'Memphis Central (TN)'),
    ('B6086D81-0742-4EE8-9CF9-DD3FC8594277', '1947-11-08', 1947, 'RELABEL', 'Nashville Central (TN)'),
    ('56EC225E-0DD0-4449-9EC3-B1AF3B7B55A9', '1952-11-01', 1952, 'RELABEL', 'Nashville Central (TN)'),
    ('D835B993-F379-4802-B439-63D2A7794E26', '1953-10-17', 1953, 'RELABEL', 'Nashville Central (TN)'),
    ('481FD531-7FC6-4160-A3C1-A397CAEF7A9A', '1956-11-03', 1956, 'RELABEL', 'Nashville Central (TN)'),
    ('94157176-2D9A-420E-82AF-16687D14FAB7', '1958-11-08', 1958, 'RELABEL', 'Nashville Central (TN)'),
    ('9292126B-52B0-4C10-A15D-79D77B4B2DA8', '1959-10-17', 1959, 'RELABEL', 'Nashville Central (TN)'),
    ('81A5C7C3-FF23-4D72-9803-B8A06E3D0999', '1964-10-24', 1964, 'RELABEL', 'Memphis Central (TN)'),
    ('1B753448-28E4-41E1-842A-27A058C63071', '1964-11-07', 1964, 'RELABEL', 'Memphis Central (TN)'),
    ('0E635739-A858-43B2-AB1B-FBDB30BEE62A', '1987-11-13', 1987, 'RELABEL', 'Kingsport Central (TN)'),
    ('C0131EEC-DD81-404E-B6D1-3C4A96B6F4FE', '2003-09-26', 2003, 'RELABEL', 'Murfreesboro Central (TN)'),
    ('6F14BF94-4EEF-4DEB-88C2-AB963FD71FAC', '2003-10-31', 2003, 'RELABEL', 'Chattanooga Central (TN)'),

    ('26023000-BBF8-47EC-94E1-00192EFC6662', '1949-10-08', 1949, 'DUPLICATE', 'Nashville Central (TN)'),
    ('E79633EC-6AF6-4377-AE93-B578EAFF3DA6', '1951-11-10', 1951, 'DUPLICATE', 'Nashville Central (TN)'),
    ('D16A0459-703B-40F8-AB02-AC30C2E6563D', '1953-09-12', 1953, 'DUPLICATE', 'Nashville Central (TN)'),
    ('CA10A238-D63D-4454-A970-80E8A8BA14BB', '1954-10-16', 1954, 'DUPLICATE', 'Nashville Central (TN)'),
    ('C9535E49-17CD-4299-B8AD-5860BB1F5777', '1955-09-10', 1955, 'DUPLICATE', 'Nashville Central (TN)'),
    ('931859C7-F7B4-40AB-867F-804F6CF0CA2C', '1960-10-08', 1960, 'DUPLICATE', 'Nashville Central (TN)'),
    ('12135BB4-1F49-4DC6-AE88-41AAC8CAA855', '1960-10-29', 1960, 'DUPLICATE', 'Nashville Central (TN)'),
    ('4BF36E33-15B6-41F8-A29C-E86EECC1335D', '1961-10-07', 1961, 'DUPLICATE', 'Nashville Central (TN)'),
    ('93AB2ADB-F1A1-42C0-8656-0D22EC45CCFB', '1961-10-14', 1961, 'DUPLICATE', 'Nashville Central (TN)'),
    ('37277373-85D7-4C01-B546-F8669D5A289E', '1962-09-15', 1962, 'DUPLICATE', 'Nashville Central (TN)'),
    ('0B78C09D-6B50-4E1A-8416-863071F7A2A4', '1962-09-22', 1962, 'DUPLICATE', 'Nashville Central (TN)'),
    ('6F10EB34-EAFC-43F8-930C-B72978E771AC', '1963-10-12', 1963, 'DUPLICATE', 'Nashville Central (TN)'),
    ('1D73CCF3-E72D-4BDA-A679-9ACBB7399483', '1969-10-03', 1969, 'DUPLICATE', 'Nashville Central (TN)'),
    ('0FEED2A0-B4B9-4A27-9CCA-4612C124ECA9', '1970-09-04', 1970, 'DUPLICATE', 'Nashville Central (TN)'),
]

print('=== Step 1: For DUPLICATE candidates, confirm the pre-existing game vs the correct Central is on the SAME DATE ===')
print('    (if the dates differ, this may be a legitimate second meeting, not a duplicate -- flagged for manual review)')
print()
for scores_id, date, season, verdict, target in rows:
    if verdict != 'DUPLICATE':
        continue
    cur.execute("SELECT Home, Visitor FROM HS_Scores WHERE ID = ?", scores_id)
    row = cur.fetchone()
    if not row:
        print(f'  [{scores_id}] {date} -- ROW NOT FOUND (may have been edited/removed already)')
        continue
    opponent = row.Visitor if row.Home == 'Knoxville Central (TN)' else row.Home
    cur.execute("""
        SELECT Date, Home, Visitor, Home_Score, Visitor_Score, Source
        FROM HS_Scores
        WHERE Season = ?
          AND ((Home = ? AND Visitor = ?) OR (Home = ? AND Visitor = ?))
    """, season, opponent, target, target, opponent)
    matches = cur.fetchall()
    same_date_matches = [m for m in matches if str(m.Date) == date]
    if same_date_matches:
        m = same_date_matches[0]
        print(f'  [{scores_id}] {date} vs {opponent} -- SAME-DATE match confirmed: {m.Home} {m.Home_Score}-{m.Visitor_Score} {m.Visitor} [{m.Source}]  ==> safe to DELETE')
    else:
        print(f'  [{scores_id}] {date} vs {opponent} -- NO same-date match (existing game(s) vs {target} this season on different date(s): {[str(m.Date) for m in matches]})  ==> NEEDS MANUAL REVIEW, do not blindly delete')

print()
print('=== Step 2: Look up matching HS_Mapping_Investigations rows for these 35 ScoresIDs ===')
print('    (first, discover the actual column names on this table)')
cur.execute("""
    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'HS_Mapping_Investigations'
    ORDER BY ORDINAL_POSITION
""")
cols = [r.COLUMN_NAME for r in cur.fetchall()]
print(f'  Columns: {cols}')
print()

# Try the most likely candidate columns for a scores-row linkage.
link_cols = [c for c in cols if 'Scores' in c or 'ID' in c and c != 'InvestigationID' and c != 'ID']
print(f'  Candidate link columns to try: {link_cols}')
print()

for scores_id, date, season, verdict, target in rows:
    found_any = False
    for col in link_cols:
        try:
            cur.execute(f"SELECT * FROM HS_Mapping_Investigations WHERE {col} = ?", scores_id)
            matches = cur.fetchall()
            if matches:
                found_any = True
                for m in matches:
                    print(f'  [{scores_id}] {date} ({verdict}) -- matched via {col}: {list(zip([d[0] for d in cur.description], m))}')
        except Exception:
            continue
    if not found_any:
        print(f'  [{scores_id}] {date} ({verdict}) -- NO investigation row found via any candidate link column')
