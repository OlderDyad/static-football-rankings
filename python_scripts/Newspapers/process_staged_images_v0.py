import os
import pytesseract
from PIL import Image

# 📌 Set paths
STAGED_FOLDER = "H:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"

# Ensure Tesseract is installed (Update this path if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Get all images in the Staged folder
image_files = [f for f in os.listdir(STAGED_FOLDER) if f.endswith(('.jpg', '.png'))]

if not image_files:
    print("❌ No images found in 'Staged' folder. Exiting.")
    exit()

print(f"🔍 Found {len(image_files)} image(s) for OCR processing.")

for image_file in image_files:
    image_path = os.path.join(STAGED_FOLDER, image_file)
    
    print(f"📄 Processing: {image_file} ...")
    
    try:
        # Load image and perform OCR
        img = Image.open(image_path)
        extracted_text = pytesseract.image_to_string(img)

        # Save extracted text to a .txt file
        text_filename = os.path.splitext(image_file)[0] + ".txt"
        text_filepath = os.path.join(STAGED_FOLDER, text_filename)

        with open(text_filepath, "w", encoding="utf-8") as f:
            f.write(extracted_text)

        print(f"✅ OCR completed: {text_filename}")

    except Exception as e:
        print(f"❌ Error processing {image_file}: {e}")

print("🎉 All images processed successfully!")
