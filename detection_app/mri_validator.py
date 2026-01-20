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
        # Relaxed: Allow aspect ratio between 0.75 and 1.33 (e.g., 3:4 to 4:3)
        aspect_ratio = width / height
        if aspect_ratio < 0.75 or aspect_ratio > 1.33:
            return False

        # Check if image has enough contrast (Relaxed)
        contrast = img.std()
        if contrast < 5:  # Lowered from 15
            return False

        # Check if image isn't pure black or white (Relaxed)
        if img.max() < 20 or img.min() > 235: # Widened range
            return False

        return True
    except Exception as e:
        print("Validation error:", e)
        return False
