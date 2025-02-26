import pytesseract
import cv2
from PIL import Image
import os

# Set the Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\demck\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Load an image
image_path = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\The_Buffalo_News_1989_09_10_57.jpg"

# Check if file exists
if not os.path.exists(image_path):
    print(f"Error: File not found at {image_path}")
else:
    # Read the image
    image = cv2.imread(image_path)

    # Check if the image loaded correctly
    if image is None:
        print(f"Error: Could not open {image_path}. Check file format and path.")
    else:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Perform OCR
        text = pytesseract.image_to_string(gray, config="--psm 6")

        # Print extracted text
        print("Extracted Text:\n", text)
