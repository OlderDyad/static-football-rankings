import os

STAGED_FOLDER = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged"

try:
    all_files = os.listdir(STAGED_FOLDER)
    print("📂 Files in Staged folder:", all_files)
    
    # Find OCR text files
    ocr_files = [f for f in all_files if f.endswith(".txt")]

    if not ocr_files:
        print("❌ No OCR result files found in Staged folder.")
    else:
        print(f"✅ Found OCR files: {ocr_files}")

except FileNotFoundError:
    print(f"❌ The folder '{STAGED_FOLDER}' was not found. Check if the path is correct.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
