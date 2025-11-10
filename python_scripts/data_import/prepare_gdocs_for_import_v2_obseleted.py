# prepare_gdocs_for_import.py (Corrected Version)

import os
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json # <--- CHANGED: Use the standard json library
import logging
from collections import defaultdict
import time
import shutil  # <--- ADD THIS LINE

from collections import defaultdict

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
    """Authenticates with Google and returns a service object for the Drive API."""
    creds = None
    token_path = 'token.json'
    # The INFO log message you saw about "file_cache" comes from this section. It is harmless and can be ignored.
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
    """Fetches all text from a Google Doc."""
    try:
        document = service.documents().get(documentId=doc_id).execute()
        content = document.get('body').get('content')
        text = ''
        if content: # Check if content is not None
            for value in content:
                if 'paragraph' in value:
                    elements = value.get('paragraph').get('elements')
                    for elem in elements:
                        text += elem.get('textRun', {}).get('content', '')
        return text
    except HttpError as err:
        logger.error(f"Could not fetch content for doc ID {doc_id}: {err}")
        return None

def ai_clean_and_format_text(raw_text, template_name='default'):
    """
    Uses the Gemini AI to clean the raw OCR text based on a selected template.
    """
    if not raw_text.strip():
        logger.warning("Skipping AI call for empty raw text.")
        return ""
        
    logger.info(f"Sending text to AI for cleaning using '{template_name}' template...")
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # This line uses the correct, current model name
        model = genai.GenerativeModel('gemini-1.5-flash-latest') 
    except Exception as e:
        logger.fatal(f"Failed to configure AI model. Check your API key. Error: {e}")
        return None

    # --- TEMPLATE SELECTION ---
    if template_name == 'boston_globe':
        # --- NEW, SPECIALIZED PROMPT FOR COMPLEX FORMATS ---
        prompt = f"""
        You are an expert sports data extraction assistant. Your task is to analyze raw OCR text from a newspaper that uses complex formats and extract only the final game scores.

        **Primary Goal: Extract ONLY the main summary score line.**

        **Parsing Rules for this Format:**

        1.  **Find the Main Score:** The primary score line might be separated by a comma (',') or a long series of dots ('.........'). Your first job is to identify this main line (e.g., 'Everett 49 .................. Revere 0').
        2.  **IGNORE Detailed Breakdowns:** Immediately following the main score line, there is often a detailed breakdown with individual stats, scoring plays, or quarter-by-quarter scores. **YOU MUST IGNORE THIS ENTIRE DETAILED SECTION.** Your only output should be the final score.
        3.  **Example:** If the input is 'Central Catholic 14, St. John's 6' followed by a box score showing individual touchdown runs, your one and only output for that game must be `Central Catholic 14, St. John's 6`.
        4.  **Handle 'Bar' Separators:** Treat a long series of dots ('....') or underscores ('____') as a simple comma separator.

        **Formatting Rules:**

        1.  Format each game score onto a new line in the format: `Team A Name ScoreA, Team B Name ScoreB`.
        2.  Ignore all headers ('DIVISION 1', 'NON-LEAGUE', etc.) and all text that is not a final score line.

        Here is the raw text:
        ---
        {raw_text}
        ---

        Cleaned Scores:
        """
    else: # 'default' template
        # --- THIS IS THE EXISTING, TRUSTED PROMPT ---
        prompt = f"""
# In the ai_clean_and_format_text() function of prepare_gdocs_for_import_v2.py
# ... inside the 'else: # default template' block
prompt = f"""
    You are a data processing robot. Your only job is to extract game scores from raw text.

    **Primary Directive:** Your highest priority is to correctly identify games that are split across two lines.
    -   **Rule 1:** If you see a line that ends with `TeamA ScoreA,` you MUST look at the very next line.
    -   **Rule 2:** The entire content of that next line IS the opponent's score. Treat it as a number and combine the two lines into a single output: `TeamA ScoreA, OpponentB ScoreB`. Do not change the number you see on the second line.

    **Secondary Directives:**
    - If a line contains a full game `TeamA ScoreA, TeamB ScoreB`, format it as-is.
    - If a line is garbled or unreadable, ignore it completely to prevent errors.
    - Ignore all headers and other non-score text.

    Here is the raw text:
    ---
    {raw_text}
    ---

    Cleaned Scores:
"""

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
        
        template_to_use = 'default'
        if 'boston_globe' in base_name.lower():
            template_to_use = 'boston_globe'
        
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
        
        # This function is missing from your provided script but should be there
        # pre_processed_text = pre_process_ocr_text(combined_text) 
        
        cleaned_data = ai_clean_and_format_text(combined_text, template_name=template_to_use)

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
                shutil.move(src, dest)
            logger.info(f"Moved {len(file_list)} processed .gdoc files to '{processed_gdocs_dir}'.")

        except Exception as e:
            logger.error(f"Failed to write output file or move source files for {base_name}. Error: {e}")

    logger.info("--- Automated Document Preprocessing Complete! ---")

if __name__ == "__main__":
    main()