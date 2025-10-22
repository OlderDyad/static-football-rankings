# find_long_notes.py (Corrected)
import os
import csv
import logging

# --- CONFIGURATION ---
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
MAX_NOTE_LENGTH = 255

# --- SCRIPT SETUP ---
# **FIX**: Moved logging config to the top so the logger is defined globally
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- SCRIPT ---
def find_long_notes():
    """
    Scans CSV files in the staging directory to find rows where the 'notes'
    column exceeds a specified character length.
    """
    logger.info(f"Scanning for long notes in directory: {STAGING_DIRECTORY}")
    found_issues = False

    staged_files = [
        f for f in os.listdir(STAGING_DIRECTORY)
        if f.lower().endswith('.csv') and 'new_alias_suggestions' not in f.lower()
    ]

    if not staged_files:
        logger.warning("No CSV files found to scan.")
        return

    for filename in staged_files:
        filepath = os.path.join(STAGING_DIRECTORY, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for i, row in enumerate(reader, 2):  # Start line count from 2
                    # Ensure row has enough columns to check for notes
                    if len(row) >= 7:
                        notes = row[6]
                        if len(notes) > MAX_NOTE_LENGTH:
                            found_issues = True
                            logger.error(f"!!! Found oversized note in file: {filename}")
                            logger.error(f"    Line Number: {i}")
                            logger.error(f"    Length: {len(notes)} (Max is {MAX_NOTE_LENGTH})")
                            logger.error(f"    Content: {notes[:200]}...")  # Print first 200 chars
        except Exception as e:
            logger.error(f"Could not process file {filename}. Error: {e}")

    if not found_issues:
        logger.info("Scan complete. No notes exceeded the max length.")

if __name__ == "__main__":
    find_long_notes()