import os
import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Input, Flatten, Dense, Dropout
from tensorflow.keras.applications import VGG16

# Force UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
MODEL_PATH = os.path.join('detection_app', 'spiral_model.h5')
# Saving as legacy .h5 because .keras (zip) is causing corruption issues on this Windows env
SAVE_PATH = os.path.join('detection_app', 'spiral_model_recovered.h5')
INPUT_SHAPE = (224, 224, 3)

print("=== SPIRAL MODEL RECOVERY (Option B) ===")

def recover_model():
    if not os.path.exists(MODEL_PATH):
        print(f"FAILED: {MODEL_PATH} not found.")
        return

    print("[1] Building VGG16 Backbone (Functional API)...")
    # Base VGG16, frozen
    base_model = VGG16(weights='imagenet', include_top=False, input_shape=INPUT_SHAPE)
    base_model.trainable = False
    
    print("[2] Attaching Classifier Head...")
    # Functional API chaining
    x = base_model.output
    x = Flatten(name='flatten')(x)
    x = Dense(128, activation='relu', name='dense')(x)
    x = Dropout(0.5, name='dropout')(x)
    output = Dense(1, activation='sigmoid', name='dense_1')(x)

    model = Model(inputs=base_model.input, outputs=output)

    print("[3] Architecture Summary:")
    model.summary()

    print(f"\n[4] Loading weights from {MODEL_PATH}...")
    try:
        # Load weights: allow partial match
        model.load_weights(MODEL_PATH, by_name=True, skip_mismatch=True)
        print("[INFO] Weights loaded successfully (partial/full match).")
    except Exception as e:
        print(f"FAILED to load weights: {e}")
        return

    print("\n[5] Verifying with dummy inference...")
    try:
        dummy_input = np.zeros((1, 224, 224, 3))
        pred = model.predict(dummy_input)
        print(f"[INFO] Prediction successful: {pred}")
    except Exception as e:
        print(f"[ERROR] Inference failed: {e}")
        return

    print(f"\n[6] Saving to {SAVE_PATH}...")
    model.save(SAVE_PATH)
    print("[INFO] Model saved successfully!")

if __name__ == "__main__":
    recover_model()
