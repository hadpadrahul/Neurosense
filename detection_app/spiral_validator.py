import cv2
import numpy as np

def is_valid_spiral(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False

    # Resize (standardization)
    img = cv2.resize(img, (224, 224))

    # Blur to reduce noise
    blurred = cv2.GaussianBlur(img, (5, 5), 0)

    # Threshold (inverse so dark spiral on light bg becomes white on black)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return False

    # Get the largest contour (assumed to be the spiral)
    largest = max(contours, key=cv2.contourArea)

    area = cv2.contourArea(largest)
    perimeter = cv2.arcLength(largest, True)

    if perimeter == 0:
        return False

    circularity = (4 * np.pi * area) / (perimeter ** 2)
    
    # Reject retina-like patterns based on color/texture
    if np.mean(img) > 200:  # Too bright
         return False
    if np.std(img) < 10:    # Very low variance (no edges or structure)
         return False


    # Debug print:
    print(f"[DEBUG] Spiral validation: Area={area}, Perimeter={perimeter}, Circularity={circularity:.2f}")

    # Relaxed ranges to allow imperfect spirals (drawn by hand)
    return area > 1000 and circularity > 0.05
