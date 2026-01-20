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
        # Updated to use the recovered Keras 3 compatible model
        model_path = os.path.join(os.path.dirname(__file__), 'spiral_model.keras')
        if os.path.exists(model_path):
            # compile=False is safer for inference, especially with custom metrics/losses
            _model = load_model(model_path, compile=False)
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
        keras_preproc = importlib.import_module('tensorflow.keras.preprocessing')
        image = getattr(keras_preproc, 'image')
    except Exception:
        return "Preprocessing library not available"

    try:
        # Load and preprocess the image
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # Make prediction
        prediction = model.predict(img_array)

        # Interpret result
        if prediction[0][0] > 0.5:
            return "Parkinson Detected"
        else:
            return "Healthy Drawing"

    except Exception as e:
        return f"Error: {str(e)}"
