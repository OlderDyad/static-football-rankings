import cv2
import numpy as np
from PIL import Image

def preprocess_image(input_path, output_path):
    # Load the image
    img = cv2.imread(input_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to get black text on white background
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # Reduce noise
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    
    # Improve contrast
    alpha = 1.5  # Contrast control
    beta = 10    # Brightness control
    enhanced = cv2.convertScaleAbs(denoised, alpha=alpha, beta=beta)
    
    # Save the preprocessed image
    cv2.imwrite(output_path, enhanced)
    print(f"Preprocessed image saved to {output_path}")

# Example usage
preprocess_image("The_Post_Standard_2003_10_19_41.jpg", 
                 "The_Post_Standard_2003_10_19_41_preprocessed.jpg")