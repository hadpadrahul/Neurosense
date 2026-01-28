import numpy as np
import os
import importlib


# Lazy model loader: don't import heavy ML libraries at module import time.
_model = None
_model_loaded = False


def _get_model():
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    try:
        keras = importlib.import_module('tensorflow.keras')
        load_model = getattr(keras.models, 'load_model')
        
        # Load the recovered Keras 3 compatible model
        model_path = os.path.join(os.path.dirname(__file__), 'spiral_model_recovered.h5')
        if os.path.exists(model_path):
            # No custom objects needed anymore!
            _model = load_model(model_path, compile=False)
            print(f"[INFO] Spiral Model loaded successfully from {model_path}")
        else:
            print(f"[ERROR] Spiral model file not found at {model_path}")
            _model = None
    except Exception as e:
        print(f"[ERROR] Failed to load spiral_model.keras: {e}")
        # import traceback
        # traceback.print_exc()
        _model = None
    return _model


def predict_spiral(img_path):
    """
    Predicts whether the given spiral drawing indicates Parkinson's Disease or not.

    Args:
        img_path (str): Path to the image to predict.

    Returns:
        str: Prediction result – "Parkinson Detected" or "Healthy Drawing"
    """
    model = _get_model()
    if model is None:
        return "Model Not Loaded"

    try:
        import cv2
        from tensorflow.keras.applications.vgg16 import preprocess_input

        # 1. Read image
        img = cv2.imread(img_path)
        if img is None:
            return f"Error: Could not read image at {img_path}"

        # 2. Resize to (224, 224) - Corrected input shape
        img = cv2.resize(img, (224, 224))

        # 3. Convert BGR (OpenCV default) to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 4. Cast to float32
        img = img.astype('float32')

        # 5. Preprocess (VGG16 specific: Subtracts mean RGB, does NOT divide by 255)
        img = preprocess_input(img)

        # 6. Expand dims to (1, 128, 128, 3)
        img_array = np.expand_dims(img, axis=0)

        # Make prediction
        prediction = model.predict(img_array)

        # Interpret result
        if prediction[0][0] > 0.5:
            return "Parkinson Detected"
        else:
            return "Healthy Drawing"

    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        return f"Error: {str(e)}"
