import os
import logging
import numpy as np
from pathlib import Path
from django.conf import settings
from PIL import Image
import tensorflow as tf

logger = logging.getLogger(__name__)

# --- Ensure ALZ_MODEL is available (try import if not set earlier) ---
ALZ_MODEL = globals().get("ALZ_MODEL", None)
MODEL_PATH = globals().get("MODEL_PATH", None) or getattr(settings, "ALZ_MODEL_PATH", None)

def try_load_model_once():
    global ALZ_MODEL, MODEL_PATH
    if ALZ_MODEL is not None:
        return ALZ_MODEL
    # candidate fallback paths
    candidates = [
        MODEL_PATH,
        str(Path(settings.BASE_DIR) / "detection_app" / "models_files" / "alz_effnetb0_multiclass.h5"),
        str(Path(settings.BASE_DIR) / "detection_app" / "models_files" / "alz_mri_model.h5"),
    ]
    candidates = [c for c in candidates if c]
    for p in candidates:
        if os.path.exists(p):
            try:
                # import tensorflow as tf # Already imported at top
                ALZ_MODEL = tf.keras.models.load_model(p, compile=False)
                MODEL_PATH = p
                logger.info("Loaded ALZ model from: %s", p)
                break
            except Exception as e:
                logger.exception("Failed to load model at %s : %s", p, e)
    if ALZ_MODEL is None:
        logger.error("No ALZ model loaded. Tried: %s", candidates)
    return ALZ_MODEL

# Simple preprocessing; replace with your real preprocessing function
def preprocess_image_for_debug(image_path, target_size=(224,224)):
    img = Image.open(image_path).convert("RGB")
    img = img.resize(target_size)
    arr = np.asarray(img).astype("float32") / 255.0
    arr = np.expand_dims(arr, 0)  # batch
    return arr

# label mapping - adjust to your training labels and order
CLASS_LABELS = ["Normal", "VeryMildDemented", "MildDemented", "ModerateDemented"]
# if your model used different labels, change above accordingly.

def safe_predict_and_decode(image_abs_path):
    """
    Returns: dict with keys:
    - raw_output: np.array
    - probs: np.array (sums to 1 for multiclass, or two-way for binary)
    - predicted_label: str
    - confidence: float (0-1)
    - warnings: list[str]
    """
    model = try_load_model_once()
    info = {"raw_output": None, "probs": None, "predicted_label": None, "confidence": None, "warnings": []}
    if model is None:
        info["warnings"].append("Model not loaded on server.")
        return info

    try:
        x = preprocess_image_for_debug(image_abs_path)
    except Exception as e:
        info["warnings"].append(f"Preprocessing failed: {e}")
        logger.exception("Preprocessing failed")
        return info

    try:
        preds = model.predict(x)
    except Exception as e:
        info["warnings"].append(f"Model prediction failed: {e}")
        logger.exception("Model predict failed")
        return info

    preds = np.asarray(preds)
    info["raw_output"] = preds.tolist()  # JSON-serializable for template
    logger.info("Model raw output shape=%s values=%s", preds.shape, preds)

    # Try to interpret output
    # Cases:
    # 1) preds is (1, ) or (1,) -> single scalar (sigmoid)
    # 2) preds is (1, n_classes)
    # 3) preds is (n_classes,) after squeeze
    p = preds.squeeze()
    if p.ndim == 0:
        # binary scalar probability
        prob_pos = float(p)
        probs = np.array([1.0 - prob_pos, prob_pos])
        info["probs"] = probs.tolist()
        labels = ["NoAlzheimer", "Alzheimer"]
        idx = int(prob_pos >= 0.5)
        info["predicted_label"] = labels[idx]
        info["confidence"] = float(probs[idx])
    else:
        # multiclass: if values don't sum ~1, apply softmax
        s = float(np.sum(p))
        if not (0.99 <= s <= 1.01):
            # softmax
            exp = np.exp(p - np.max(p))
            probs_arr = exp / np.sum(exp)
            info["warnings"].append("Applied softmax to raw outputs (sum != 1).")
        else:
            probs_arr = p
        info["probs"] = probs_arr.tolist()
        # map to CLASS_LABELS if lengths match, otherwise use indices
        if len(probs_arr) == len(CLASS_LABELS):
            labels = CLASS_LABELS
        else:
            labels = [f"class_{i}" for i in range(len(probs_arr))]
            info["warnings"].append("CLASS_LABELS length mismatch; using numeric labels.")
        top = int(np.argmax(probs_arr))
        info["predicted_label"] = labels[top]
        info["confidence"] = float(probs_arr[top])

    # sanity checks
    if np.allclose(p, 0) or np.allclose(p, p[0]):
        info["warnings"].append("Model output looks constant/degenerate (all zeros or identical).")
    if np.any(np.isnan(p)):
        info["warnings"].append("Model output contains NaN.")

    logger.info("Decoded prediction: label=%s confidence=%s warnings=%s",
                info.get("predicted_label"), info.get("confidence"), info.get("warnings"))
    return info

def predict_alz_mri(image_path):
    """
    Main entry point for API to predict Alzheimer's MRI.
    Wraps the verbatim logic to provide a clean API response.
    """
    info = safe_predict_and_decode(image_path)
    
    # Build human-friendly prediction_pretty mapping (from view logic)
    pretty = "Unknown"
    lbl = (info.get("predicted_label") or "").lower()
    if "normal" in lbl or lbl in ["noalzheimer", "no_alzheimer", "no-alzheimer"]:
        pretty = "Normal Brain (No Dementia)"
    elif "alzheimer" in lbl or "demented" in lbl:
        pretty = "Alzheimer Likely"
    else:
        pretty = info.get("predicted_label") or "Unknown"

    # Prepare probabilities mapping (label->percent)
    # The view logic does this, so we should too for consistency
    probs_map = {}
    if info.get("probs"):
        probs = info["probs"]
        if len(probs) == len(CLASS_LABELS):
            for lab, pv in zip(CLASS_LABELS, probs):
                probs_map[lab] = float(pv) * 100.0
        else:
            for i, pv in enumerate(probs):
                probs_map[f"class_{i}"] = float(pv) * 100.0
                
    # Return structure matching the view's context context keys relevant for API
    return {
        "prediction_label": info.get("predicted_label"),
        "prediction_pretty": pretty,
        "confidence": info.get("confidence"), # 0-1
        "probabilities": probs_map, # 0-100 values
        "warnings": info.get("warnings")
    }
