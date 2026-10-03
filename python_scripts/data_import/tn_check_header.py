import csv, os

repo_root = os.path.join('..', '..')
alias_path = os.path.join(repo_root, 'excel_files', 'State_Aliases_ProperNames', 'TN_Alias_Rules_ACTIVE.csv')

with open(alias_path, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    print('Columns:', header)
    print()
    print('First 3 data rows:')
    for i, row in enumerate(reader):
        print(row)
        if i >= 2:
            break
