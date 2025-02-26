import pytesseract
import cv2
import os
import glob

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\demck\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Folder containing newspaper images
image_folder = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers"

# Get all image files
image_files = glob.glob(os.path.join(image_folder, "*.jpg"))

# Output text file for results
output_txt = os.path.join(image_folder, "ocr_results.txt")

# Open file to write results
with open(output_txt, "w", encoding="utf-8") as f:
    for image_path in image_files:
        print(f"Processing: {image_path}")

        # Read and preprocess image
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)  # Upscale
        image = cv2.GaussianBlur(image, (3,3), 0)  # Reduce noise
        image = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]  # Binarization

        # Perform OCR
        extracted_text = pytesseract.image_to_string(image, config="--psm 6")

        # Write results to file
        f.write(f"=== {os.path.basename(image_path)} ===\n")
        f.write(extracted_text + "\n\n")
        
        # Print sample output to console
        print(f"\nExtracted text from {os.path.basename(image_path)}:\n")
        print(extracted_text[:500])  # Print first 500 characters for preview

print(f"\nOCR results saved to: {output_txt}")
