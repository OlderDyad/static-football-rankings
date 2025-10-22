import os
from pathlib import Path

# --- Configuration ---
# IMPORTANT: Make sure this path is correct for your system
completed_directory = r'J:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Completed'

# Teams to search for (using partial names is fine)
target_teams = ['Forestville', 'Franklinville', 'Cattaraugus', 'Little Valley']

# Newspaper and YEAR filter
newspaper_filter = 'The_Buffalo_News'
years_to_process = ['2002']

# --- Script ---
print(f"Searching for mentions of teams in '{newspaper_filter}' files from year {year_filter}...")
print("-" * 40)

found_count = 0
directory_path = Path(completed_directory)

if not directory_path.is_dir():
    print(f"Error: Directory not found at '{completed_directory}'")
else:
    # Use rglob to search recursively through all subdirectories
    for file_path in directory_path.rglob(f'*{newspaper_filter}*{year_filter}*.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                relevant_lines = []
                for line in f:
                    # Check if any of the target team names are in the line
                    if any(team.lower() in line.lower() for team in target_teams):
                        relevant_lines.append(line.strip())

                if relevant_lines:
                    print(f"\n--- Found in File: {file_path.name} ---")
                    for line in relevant_lines:
                        print(line)
                    found_count += len(relevant_lines)
        except Exception as e:
            print(f"Could not read file {file_path.name}: {e}")

print("-" * 40)
print(f"Search complete. Found {found_count} relevant lines.")