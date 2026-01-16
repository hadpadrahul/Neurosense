# detection_app/mri_validator.py
import cv2
import numpy as np

def is_valid_mri(image_path):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False

        height, width = img.shape
        # MRI axial scans are generally square or slightly rectangular
        if height < 200 or width < 200 or abs(height - width) > 100:
            return False

        # Check if image has enough contrast
        contrast = img.std()
        if contrast < 15:  # Threshold tuned to allow real grayscale MRIs
            return False

        # Check if image isn't pure black or white
        if img.max() < 50 or img.min() > 200:
            return False

        return True
    except Exception as e:
        print("Validation error:", e)
        return False
