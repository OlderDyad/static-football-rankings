# doc_ai_prepper.py (Version 2.1) 
# GEMINI_API_KEY = 'AIzaSyC4BGBE9eJIcN0nMaeYfpqQmrGSZfU00z4' # Paste your Gemini API key here
# PROCESSOR_ID = 'f3ec126fc70e6592' 

# doc_ai_prepper.py (Version 3.0 - Final Architecture)

import os
import google.generativeai as genai
from google.cloud import documentai
import logging
import time
import re

# === CONFIGURATION (ensure this is correct) ===
RAW_IMAGE_DIR = "J:\\Users\\demck\\Google Drive\\Documents\\Football\\HSF\\Newspapers\\Next_Images"
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
COMPLETED_DIR = "J:\\Users\\demck\\Google Drive\\Documents\\Football\\HSF\\Newspapers\\Completed"
GEMINI_API_KEY = 'AIzaSyC4BGBE9eJIcN0nMaeYfpqQmrGSZfU00z4' # Paste your Gemini API key here
PROJECT_ID = 'static-football-rankings'
LOCATION = 'us'
PROCESSOR_ID = 'f3ec126fc70e6592'

# === Boilerplate Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- NEW PYTHON FUNCTION TO FIX THE LAYOUT ---
def reassemble_boston_globe_text(text):
    """
    Takes the jumbled text from Document AI for 'bar' style formats and
    programmatically reassembles the game pairings.
    """
    logger.info("Re-assembling Boston Globe format...")
    lines = text.strip().split('\n')
    
    # Filter out headers and blank lines
    game_lines = []
    headers = ['GREATER BOSTON', 'OLD COLONY', 'NONLEAGUE', 'DIVISION', 'BAY STATE', 'CAPE ANN', 'SOUTH COAST']
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Check if the line contains any header keyword or is all caps with no digits
        if any(header in line for header in headers) or (line.isupper() and not any(char.isdigit() for char in line)):
            logger.info(f"  Discarding header: '{line}'")
            continue
        game_lines.append(line)
        
    # The list should now be perfectly even. Split it in half.
    if len(game_lines) % 2 != 0:
        logger.error(f"Filtered list has an odd number of lines ({len(game_lines)}), pairing will be incorrect.")
        return "" # Return empty string on failure

    split_point = len(game_lines) // 2
    left_column = game_lines[:split_point]
    right_column = game_lines[split_point:]
    
    reassembled_lines = []
    for i in range(split_point):
        # Combine the corresponding lines from each column
        left_team_score = left_column[i].replace('.', '').strip()
        right_team_score = right_column[i].replace('.', '').strip()
        new_line = f"{left_team_score}, {right_team_score}"
        reassembled_lines.append(new_line)
        
    logger.info(f"Successfully re-assembled {len(reassembled_lines)} game lines.")
    return "\n".join(reassembled_lines)


def process_image_with_doc_ai(file_path):
    """Sends a raw image file to Document AI to perform layout-aware OCR."""
    logger.info(f"Processing '{os.path.basename(file_path)}' with Document AI...")
    try:
        opts = {"api_endpoint": f"{LOCATION}-documentai.googleapis.com"}
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        name = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{PROCESSOR_ID}"
        with open(file_path, "rb") as image:
            image_content = image.read()
        _, file_extension = os.path.splitext(file_path)
        mime_type = "image/jpeg" if file_extension.lower() in [".jpg", ".jpeg"] else "image/png"
        raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = client.process_document(request=request)
        logger.info("Successfully extracted text layout with Document AI.")
        return result.document.text
    except Exception as e:
        logger.error(f"Failed to process image with Document AI: {e}")
        return None

def ai_final_cleanup(raw_text):
    """Uses Gemini AI for a final, simple cleanup pass."""
    if not raw_text.strip():
        return ""
    logger.info("Sending re-assembled text to Gemini for final cleanup...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
        You are a data cleanup robot. The text below has already been processed and assembled.
        Your only job is to perform final minor corrections.

        1.  Ensure each line is in the format `TeamA ScoreA, TeamB ScoreB`.
        2.  Correct obvious OCR errors, like the letter 'O' in a score should be '0'.
        3.  Remove any stray characters or artifacts.
        4.  Do not change the team pairings or scores.

        Here is the text:
        ---
        {raw_text}
        ---

        Cleaned Scores:
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"An error occurred during the Gemini AI cleanup: {e}")
        return None

def main():
    """Main execution function for the Document AI workflow."""
    logger.info("--- Starting Document AI Preprocessing (V3.0 Architecture) ---")
    processed_images_dir = os.path.join(COMPLETED_DIR, "Processed_IMAGES")
    if not os.path.exists(processed_images_dir):
        os.makedirs(processed_images_dir)
    image_files = [f for f in os.listdir(RAW_IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        logger.warning(f"No image files found in '{RAW_IMAGE_DIR}'.")
        return
    logger.info(f"Found {len(image_files)} images to process.")
    for image_name in image_files:
        file_path = os.path.join(RAW_IMAGE_DIR, image_name)
        
        # Step 1: Use Document AI to get structured (but still jumbled) text
        ordered_text = process_image_with_doc_ai(file_path)
        if not ordered_text:
            logger.error(f"Skipping '{image_name}' due to Document AI failure.")
            continue
            
        # Step 2: Use our custom Python function to fix the layout and re-assemble games
        reassembled_text = reassemble_boston_globe_text(ordered_text)
        if not reassembled_text:
            logger.error(f"Skipping '{image_name}' due to re-assembly failure.")
            continue
            
        # Step 3: Use Gemini for a simple, final cleanup pass
        final_data = ai_final_cleanup(reassembled_text)
        if final_data is None:
            logger.error(f"Gemini AI cleanup failed for '{image_name}'. No output file will be generated.")
            continue
            
        # Step 4: Save the final .txt file
        base_name, _ = os.path.splitext(image_name)
        output_filename = f"{base_name}.txt"
        output_filepath = os.path.join(STAGING_DIRECTORY, output_filename)
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(final_data)
            logger.info(f"Successfully created prepped file: '{output_filepath}'")
            dest = os.path.join(processed_images_dir, image_name)
            os.rename(file_path, dest)
            logger.info(f"Moved processed image to '{processed_images_dir}'.")
        except Exception as e:
            logger.error(f"Failed to write output file or move source file for {image_name}. Error: {e}")

    logger.info("--- Document AI Preprocessing Complete! ---")

if __name__ == "__main__":
    main()