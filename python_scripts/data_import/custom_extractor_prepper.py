# custom_extractor_prepper.py (Final Interactive Version - Corrected)

import os
import sys
import logging
from google.cloud import documentai
import time
import csv
import shutil # <-- FIX #1: Added the shutil library

# === CONFIGURATION ===
# Define the configurations for each format
PROCESSOR_CONFIGS = {
    'b': {
        "description": "Bar-Separated Format",
        "raw_dir": r"J:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Next_Images_Bar_Format",
        "completed_dir": r"C:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Completed\Processed_IMAGES_Bar_Format",
        # --- FIX ---
        # PASTE YOUR "BAR" PROCESSOR'S FULL NAME HERE
        "processor_version_name": "projects/static-football-rankings/locations/us/processors/97f459082e74cedd/processorVersions/pretrained-foundation-model-v1.5-2025-05-05"
    },
    'c': {
        "description": "Comma-Separated Format",
        "raw_dir": r"J:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Next_Images_Comma_Format",
        "completed_dir": r"C:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Completed\Processed_IMAGES_Comma_Format",
        # --- FIX ---
        # This is the "comma" processor's name we found before
        "processor_version_name": "projects/static-football-rankings/locations/us/processors/4ee5cab6a5ec631e/processorVersions/f8f903268834a6d9"
    }
}


STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
PROJECT_ID = 'static-football-rankings'
LOCATION = 'us'

# === Boilerplate Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_custom_image(file_path, processor_id):
    """
    Sends an image to the processor and returns a list of lists, formatted
    with the correct quality_status and processing_notes columns.
    """
    logger.info(f"Processing '{os.path.basename(file_path)}' with processor ID: {processor_id}")
    try:
        opts = {"api_endpoint": f"{LOCATION}-documentai.googleapis.com"}
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        name = f"projects/static-football-rankings/locations/us/processors/4ee5cab6a5ec631e/processorVersions/f8f903268834a6d9"

        with open(file_path, "rb") as image:
            image_content = image.read()

        raw_document = documentai.RawDocument(content=image_content, mime_type="image/jpeg")
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = client.process_document(request=request)
        document = result.document

        output_rows = []
        for entity in document.entities:
            if entity.type_ == 'game':
                game_data = {
                    "team_one": "", "score_one": "", "team_two": "", "score_two": "",
                    "overtime": "", "forfeit": "", "tie": ""
                }
                for prop in entity.properties:
                    if prop.type_ in game_data:
                        game_data[prop.type_] = prop.mention_text.strip().replace('\n', ' ')

                # Logic to set the quality status and notes
                quality_status = 'good'
                notes = ''
                if game_data.get("forfeit"):
                    quality_status = 'needs_review'
                    notes = 'Forfeit game detected'
                else:
                    required_fields = ['team_one', 'score_one', 'team_two', 'score_two']
                    missing_fields = [field for field in required_fields if not game_data.get(field)]
                    if missing_fields:
                        quality_status = 'needs_review'
                        notes = f"Missing fields: {', '.join(missing_fields)}"

                # Assemble the row in the correct order for the importer
                row = [
                    game_data.get("team_one", ""),
                    game_data.get("score_one", ""),
                    game_data.get("team_two", ""),
                    game_data.get("score_two", ""),
                    game_data.get("overtime", ""),
                    quality_status,   # Column 6
                    notes             # Column 7
                ]
                output_rows.append(row)
        
        logger.info(f"Successfully processed {len(output_rows)} game lines from entities.")
        return output_rows

    except Exception as e:
        logger.error(f"Failed to process image with Custom Extractor: {e}")
        return None

def main():
    """Main execution function with interactive prompt and corrected CSV output."""
    while True:
        choice = input("Select raw data format - Comma (c) or Bar (b): ").lower()
        if choice in PROCESSOR_CONFIGS:
            config = PROCESSOR_CONFIGS[choice]
            break
        else:
            print("Invalid choice. Please enter 'c' or 'b'.")
    
    logger.info(f"--- Starting Custom Extractor for '{config['description']}' ---")
    
    RAW_IMAGE_DIR = config['raw_dir']
    PROCESSOR_ID = config['processor_id']
    processed_images_dir = config['completed_dir']
    
    if not os.path.exists(processed_images_dir):
        os.makedirs(processed_images_dir)

    image_files = [f for f in os.listdir(RAW_IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        logger.warning(f"No image files found in '{RAW_IMAGE_DIR}'. Exiting.")
        return
        
    logger.info(f"Found {len(image_files)} images to process.")

    for image_name in image_files:
        file_path = os.path.join(RAW_IMAGE_DIR, image_name)
        csv_rows = process_custom_image(file_path, PROCESSOR_ID)
        
        if not csv_rows:
            logger.error(f"Processing returned no data for '{image_name}'. No output file will be generated.")
            continue
            
        base_name, _ = os.path.splitext(image_name)
        output_filename = f"{base_name}.csv"
        output_filepath = os.path.join(STAGING_DIRECTORY, output_filename)
        
        try:
            with open(output_filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # This header now correctly matches the importer's expected columns
                writer.writerow(['home_team', 'home_score', 'visitor_team', 'visitor_score', 'overtime', 'quality_status', 'notes'])
                writer.writerows(csv_rows)

            logger.info(f"Successfully created prepped CSV file: '{output_filepath}'")
            
            dest = os.path.join(processed_images_dir, image_name)
            # <-- FIX #2: Replaced os.rename with shutil.move to handle cross-disk moves
            shutil.move(file_path, dest)
            logger.info(f"Moved processed image to '{processed_images_dir}'.")
        except Exception as e:
            logger.error(f"Failed to write output file or move source file for {image_name}. Error: {e}")

    logger.info("--- Custom Extractor Preprocessing Complete! ---")

if __name__ == "__main__":
    main()