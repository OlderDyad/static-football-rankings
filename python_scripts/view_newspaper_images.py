import cv2
import os
import glob

# Folder containing newspaper images
image_folder = r"H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers"

# Get all image files
image_files = glob.glob(os.path.join(image_folder, "*.jpg"))  # Adjust if PNG or other formats

# Display each image one by one
for image_path in image_files:
    print(f"Displaying: {image_path}")
    image = cv2.imread(image_path)

    if image is None:
        print(f"Error: Unable to open {image_path}")
        continue

    # Show image
    cv2.imshow("Newspaper Clipping", image)

    # Wait for key press (press any key to go to the next image, or ESC to exit)
    key = cv2.waitKey(0)
    if key == 27:  # Press ESC to exit early
        break

# Close all OpenCV windows
cv2.destroyAllWindows()
