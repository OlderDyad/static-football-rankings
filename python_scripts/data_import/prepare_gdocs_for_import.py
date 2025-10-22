# prepare_gdocs_for_import.py (Corrected Version 6 - Final)

import os
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import logging
from collections import defaultdict
import time
import re

# === CONFIGURATION ===
# --- Paths ---
RAW_DOCS_DIR = "J:\\Users\\demck\\Google Drive\\Documents\\Football\\HSF\\Newspapers\\Next"
COMPLETED_DIR = "J:\\Users\\demck\\Google Drive\\Documents\\Football\\HSF\\Newspapers\\Completed"
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"

# --- Google API ---
SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]
CLIENT_SECRET_FILE = 'credentials.json'

# --- AI Model ---
GEMINI_API_KEY = 'AIzaSyC4BGBE9eJIcN0nMaeYfpqQmrGSZfU00z4' # <--- Make sure your key is pasted here

# =================================================

# === Boilerplate Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# ========================

def get_gdrive_service():
    creds = None
    token_path = 'token.json'
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build('docs', 'v1', credentials=creds)

def get_doc_content(service, doc_id):
    try:
        document = service.documents().get(documentId=doc_id).execute()
        content = document.get('body').get('content')
        text = ''
        if content:
            for value in content:
                if 'paragraph' in value:
                    elements = value.get('paragraph').get('elements')
                    for elem in elements:
                        text += elem.get('textRun', {}).get('content', '')
        return text
    except HttpError as err:
        logger.error(f"Could not fetch content for doc ID {doc_id}: {err}")
        return None

# --- NEW FUNCTION: PYTHON PRE-PROCESSOR ---
def pre_process_ocr_text(text):
    """
    Performs simple, high-confidence text replacements to fix common OCR errors
    before sending the text to the AI.
    """
    logger.info("Performing initial OCR cleanup...")
    # Fix a score of 8 or 6 being read as '&'. We replace ' & ' with ' 8 ' 
    # as 8 is a more common final digit in scores than 6.
    text = text.replace(" & ", " 8 ")
    
    # Fix a comma being read as a period between a score and the next team.
    # e.g., "TeamA 21. TeamB 7" becomes "TeamA 21, TeamB 7"
    text = re.sub(r'(\d+)\.\s+([A-Za-z])', r'\1, \2', text)
    
    return text
# --- END OF NEW FUNCTION ---

def ai_clean_and_format_text(raw_text):
    """Uses the Gemini AI to clean the raw OCR text."""
    if not raw_text.strip():
        logger.warning("Skipping AI call for empty raw text.")
        return ""
        
    logger.info("Sending text to AI for cleaning and formatting...")
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except Exception as e:
        logger.fatal(f"Failed to configure AI model. Check your API key. Error: {e}")
        return None

    # --- NEW, UPGRADED AI PROMPT ---
    prompt = f"""
    You are an expert sports data extraction assistant.
    Your task is to analyze the raw OCR text from a newspaper's sports section below and extract only the high school football game scores.

    The raw text may contain content from multiple files or newspaper columns, which are separated by markers like '--- START OF TEXT FROM FILE: ... ---'.
    Treat all the text between these markers as a single, continuous document. Your job is to find and extract ALL valid game scores from the entire combined text.

    **Error Correction and Parsing Rules:**

    1.  **Handle Corrupted Lines:** Some lines may contain OCR errors (e.g., 'TeamA 42, TeamB &'). If a line is corrupted, do not merge it with the next line. Attempt to fix it using the rules below. If it cannot be fixed, discard the single corrupted line and continue processing the next line.
    2.  **Aggressively Split Lines:** If a single line of text appears to contain more than one game (e.g., 'TeamA 21, TeamB 7 TeamC 14, TeamD 0'), you MUST split this into multiple, separate output lines.
    3.  **Fix Common OCR Errors:** The letter 'O' in a score should always be the number '0'. A period '.' separating a score from a team name should be a comma ','.
    4.  **The Winner-First Rule:** This is a critical rule. In 99.9% of cases, the winning team is listed first. If your initial parsing of a line results in a losing team being listed first, it's highly likely your parsing is wrong. Re-evaluate the text to find the correct team boundaries.

    **Formatting Rules:**

    1.  Format each game score onto a new line in the format: `Team A Name ScoreA, Team B Name ScoreB`.
    2.  Ignore all other text, including headers, section titles, reporter names, commentary, player stats, advertisements, and the file separator markers themselves.

    Here is the raw text:
    ---
    {raw_text}
    ---

    Cleaned Scores:
    """
    # --- END OF NEW PROMPT ---

    # Add retry logic for quota errors
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            cleaned_text = response.text
            logger.info("Successfully received cleaned data from AI.")
            return cleaned_text.strip()
        except Exception as e:
            if "429" in str(e):
                logger.warning(f"Quota limit hit. Waiting 60 seconds to retry... (Attempt {attempt + 1}/3)")
                time.sleep(60)
                continue
            else:
                logger.error(f"An error occurred during the AI cleaning process: {e}")
                return None
    
    logger.error("Failed to get response from AI after multiple retries due to quota limits.")
    return None


def main():
    """Main execution function to process documents."""
    logger.info("--- Starting Automated Document Preprocessing ---")
    
    processed_gdocs_dir = os.path.join(COMPLETED_DIR, "Processed_GDOCS")
    if not os.path.exists(processed_gdocs_dir):
        os.makedirs(processed_gdocs_dir)

    try:
        service = get_gdrive_service()
    except Exception as e:
        logger.fatal(f"Failed to authenticate with Google. Please check your 'credentials.json' file. Error: {e}")
        return

    gdoc_files = [f for f in os.listdir(RAW_DOCS_DIR) if f.lower().endswith('.gdoc')]
    if not gdoc_files:
        logger.warning(f"No .gdoc files found in the '{RAW_DOCS_DIR}' directory.")
        return

    grouped_files = defaultdict(list)
    for gdoc in gdoc_files:
        base_name = gdoc.replace('.gdoc', '').split(' (')[0]
        grouped_files[base_name].append(gdoc)
    
    logger.info("--- File Grouping Analysis ---")
    if not grouped_files:
        logger.info("No groups to process.")
    else:
        for base_name, file_list in grouped_files.items():
            logger.info(f"Group '{base_name}' contains {len(file_list)} file(s):")
            for f_name in sorted(file_list):
                logger.info(f"  - {f_name}")
    logger.info("--- End of Grouping Analysis ---")

    for base_name, file_list in grouped_files.items():
        logger.info(f"Processing group: {base_name}")
        logger.info(f"Combining text from {len(file_list)} file(s) for this group.")

        combined_text = ""
        for file_name in sorted(file_list):
            file_path = os.path.join(RAW_DOCS_DIR, file_name)
            
            try:
                with open(file_path, 'r') as f:
                    gdoc_data = json.load(f)
                    doc_id = gdoc_data['doc_id']
                
                logger.info(f"  Extracting text from '{file_name}' (Doc ID: {doc_id})...")
                content = get_doc_content(service, doc_id)

                if content:
                    combined_text += f"\n--- START OF TEXT FROM FILE: {file_name} ---\n"
                    combined_text += content
                    combined_text += f"\n--- END OF TEXT FROM FILE: {file_name} ---\n\n"
                    
            except Exception as e:
                logger.error(f"Could not process file {file_name}. Error: {e}")
                continue

        if not combined_text.strip():
            logger.warning(f"No content extracted for group {base_name}. Skipping.")
            continue
        
        # --- CALL THE NEW PRE-PROCESSOR ---
        pre_processed_text = pre_process_ocr_text(combined_text)
        # --- END OF CALL ---
        
        cleaned_data = ai_clean_and_format_text(pre_processed_text)

        if cleaned_data is None:
            logger.error(f"AI processing failed for group {base_name}. No output file will be generated.")
            continue
            
        output_filename = f"{base_name}.txt"
        output_filepath = os.path.join(STAGING_DIRECTORY, output_filename)
        
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned_data)
            logger.info(f"Successfully created prepped file: '{output_filepath}'")
            
            for file_name in file_list:
                src = os.path.join(RAW_DOCS_DIR, file_name)
                dest = os.path.join(processed_gdocs_dir, file_name)
                os.rename(src, dest)
            logger.info(f"Moved {len(file_list)} processed .gdoc files to '{processed_gdocs_dir}'.")

        except Exception as e:
            logger.error(f"Failed to write output file or move source files for {base_name}. Error: {e}")

    logger.info("--- Automated Document Preprocessing Complete! ---")

if __name__ == "__main__":
    main()