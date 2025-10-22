import os

# Check what's in the report file
report_file = "Alias_Match_Report.txt"

print("=== CHECKING ALIAS MATCH REPORT ===")
print(f"Report file: {report_file}")
print(f"File exists: {os.path.exists(report_file)}")

if os.path.exists(report_file):
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    print("\n=== REPORT CONTENTS ===")
    print(content)
else:
    print("Report file not found!")