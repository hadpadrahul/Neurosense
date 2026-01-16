import os
import joblib
import numpy as np
from django.conf import settings
import importlib

# --- Pattern B: Copying Quiz Logic Verbatim ---

# Adjust paths to point to the parent detection_app directory
BASE_APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_APP_DIR, "parkinsons_stage_model.joblib")
ENCODER_PATH = os.path.join(BASE_APP_DIR, "label_encoder.joblib")

stage_model = None
label_encoder = None

try:
    stage_model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)
    # print("✅ Service: Quiz Prediction Models loaded successfully!")
except Exception as e:
    stage_model = None
    label_encoder = None
    print(f"⚠️ Service: Quiz Prediction Model or Encoder loading failed: {e}")

def predict_quiz(quiz_answers_dict):
    """
    Orchestrates the quiz prediction logic, copying the if/else messaging blocks
    verbatim from detection_app/views.py upload_assessment.
    
    Args:
        quiz_answers_dict (dict): Dictionary of q1...q20 keys with integer values (0-4).
    
    Returns:
        dict: Contains 'predicted_stage', 'main_message', 'stage_description', etc.
    """
    
    # Initialize core context variables with default values (copied from views.py)
    predicted_stage_text = "Not Assessed"
    main_result_message = "Assessment Incomplete"
    stage_description = "Please complete the assessment quiz for a preliminary indication."
    doctor_type = "Neurologist"
    next_steps_advice = [
        "Schedule an appointment with a neurologist for a professional evaluation.",
        "Prepare a detailed list of your symptoms and their onset for your doctor.",
        "Discuss any family history of neurological conditions.",
        "Do not self-diagnose or alter any medication based on this assessment."
    ]
    consolation_message = "Thank you for completing the assessment. Remember, early information is a step towards better health."

    # Extract user inputs in order q1...q20
    user_inputs = []
    question_keys = [f"q{i}" for i in range(1, 21)]
    
    for key in question_keys:
        val = quiz_answers_dict.get(key, 0)
        user_inputs.append(val)

    # Attempt to make a prediction if model is available
    if stage_model and label_encoder:
        try:
            prediction_array = np.array(user_inputs).reshape(1, -1)
            
            # Validation: Check feature count
            if hasattr(stage_model, 'n_features_in_') and len(user_inputs) == stage_model.n_features_in_:
                prediction = stage_model.predict(prediction_array)[0]
                predicted_stage_text = label_encoder.inverse_transform([prediction])[0]

                # --- START VERBATIM ORCHESTRATION COPY ---
                # Refine messages based on the predicted_stage_text for all 6 stages
                if "No Parkinson" in predicted_stage_text or "No PD" in predicted_stage_text or "Healthy" in predicted_stage_text:
                    main_result_message = "Fantastic News! Your assessment indicates a low likelihood of Parkinson's symptoms."
                    stage_description = "This is a great sign! Continue to prioritize your health and well-being. Remember, this assessment is preliminary; consult a doctor if any concerns arise."
                    doctor_type = "General Practitioner (for routine check-ups)"
                    next_steps_advice = [
                        "Maintain a healthy and active lifestyle with regular exercise and a balanced diet.",
                        "Stay vigilant for any new or unusual health changes and consult your doctor if they occur.",
                        "Consider regular wellness check-ups with your general practitioner for overall health maintenance."
                    ]
                    consolation_message = "Wonderful news! Your commitment to health is admirable. Keep shining brightly! Remember to enjoy life's simple pleasures and stay positive."
                elif "Stage 1" in predicted_stage_text:
                    main_result_message = "Preliminary Indication: Early Stage Symptoms for Parkinson's Detected."
                    stage_description = "Early detection is crucial. Consulting a neurologist promptly can help in confirming diagnosis and discussing early management strategies to maintain quality of life."
                    doctor_type = "Neurologist (Specialist)"
                    next_steps_advice = [
                        "Schedule an appointment with a neurologist as soon as possible for a definitive diagnosis.",
                        "Prepare a detailed list of your symptoms, their onset, and any family history for your doctor.",
                        "Discuss potential early interventions, lifestyle adjustments, and therapeutic options.",
                        "Do not self-diagnose or alter any medication based on this assessment."
                    ]
                    consolation_message = "Remember, you're not alone on this journey. Every step forward, no matter how small, is progress. Focus on self-care and lean on your support system. We're here to support you."
                elif "Stage 2" in predicted_stage_text:
                    main_result_message = "Preliminary Indication: Moderate Stage Symptoms for Parkinson's Detected."
                    stage_description = "It's important to consult a neurologist for a comprehensive evaluation. Effective treatments are available to manage symptoms and improve daily living."
                    doctor_type = "Neurologist (Specialist)"
                    next_steps_advice = [
                        "Seek consultation with a neurologist for a thorough diagnosis and treatment plan.",
                        "Discuss medication options and non-pharmacological therapies (e.g., physical therapy, occupational therapy).",
                        "Explore local support groups and educational resources for Parkinson's patients and caregivers.",
                        "Ensure regular follow-up appointments with your medical team to adjust treatment as needed."
                    ]
                    consolation_message = "Your strength is inspiring. Focus on self-care and lean on your support system. Brighter days are ahead, and every effort counts. Keep your spirits high!"
                elif "Stage 3" in predicted_stage_text:
                    main_result_message = "Preliminary Indication: Mid-to-Advanced Stage Symptoms for Parkinson's Detected."
                    stage_description = "Symptoms may be more noticeable at this stage. A neurologist can guide you on advanced management strategies and therapies to improve mobility and quality of life."
                    doctor_type = "Neurologist (Specialist)"
                    next_steps_advice = [
                        "Arrange an urgent consultation with a neurologist specializing in movement disorders.",
                        "Discuss advanced treatment options and multidisciplinary care approaches (e.g., speech therapy, dietetics).",
                        "Consider home modifications or assistive devices to enhance safety and independence.",
                        "Engage with support networks for emotional and practical guidance."
                    ]
                    consolation_message = "Take a deep breath. You possess incredible resilience. Focus on what brings you comfort and peace, and remember that support is always available."
                elif "Stage 4" in predicted_stage_text:
                    main_result_message = "Preliminary Indication: Advanced Stage Symptoms for Parkinson's Detected."
                    stage_description = "At this stage, symptoms are significant. Immediate consultation with a neurologist is vital to optimize treatment, manage complications, and ensure comprehensive support."
                    doctor_type = "Neurologist (Specialist)"
                    next_steps_advice = [
                        "Seek immediate medical attention from a neurologist for comprehensive care planning.",
                        "Discuss options for managing severe motor and non-motor symptoms.",
                        "Consider palliative care or hospice care options to enhance comfort and quality of life.",
                        "Ensure a strong support system is in place, including family, caregivers, and medical professionals."
                    ]
                    consolation_message = "Even in challenging times, remember your inner strength. Focus on moments of joy and connection, and know that you are surrounded by care."
                elif "Stage 5" in predicted_stage_text:
                    main_result_message = "Preliminary Indication: Very Advanced Stage Symptoms for Parkinson's Detected."
                    stage_description = "This indicates very advanced symptoms requiring intensive medical and supportive care. A neurologist can help in managing complex symptoms and ensuring comfort."
                    doctor_type = "Neurologist (Specialist) & Multidisciplinary Care Team"
                    next_steps_advice = [
                        "Urgent consultation with a neurologist and a multidisciplinary care team is essential.",
                        "Focus on comprehensive symptom management, comfort, and quality of life.",
                        "Discuss advanced care planning and support services for both the patient and caregivers.",
                        "Connect with specialized Parkinson's care centers for expert management."
                    ]
                    consolation_message = "Your journey is unique, and your courage shines brightly. Embrace moments of peace and know you are supported every step of the way."
                else: # Fallback for any unexpected stage outputs
                    main_result_message = "Assessment Complete. Further Evaluation Recommended."
                    stage_description = "The assessment provides a preliminary indication. For a definitive diagnosis and personalized advice, a professional medical consultation is essential."
                    doctor_type = "Neurologist"
                    consolation_message = "Thank you for completing the assessment. Remember, early information is a step towards better health."
                # --- END VERBATIM ORCHESTRATION COPY ---
            else:
                 # Feature mismatch fallback
                 expected = stage_model.n_features_in_ if hasattr(stage_model, 'n_features_in_') else "Unknown"
                 print(f"Error: Expected {expected} features, got {len(user_inputs)}")
                 main_result_message = "Processing Error"
                 predicted_stage_text = "Error"
                 stage_description = "There was an issue processing your quiz answers. Please try again or contact support."
                 consolation_message = "We encountered an issue. Please try again or reach out for support."

        except Exception as e:
            print(f"Prediction error: {e}")
            main_result_message = "Prediction Error"
            predicted_stage_text = "Error"
            stage_description = "An error occurred during prediction. Please try again or contact support."
            consolation_message = "An unexpected error occurred. Your well-being is important; please try again or contact support."
    else:
        # Model not loaded
        main_result_message = "Model Not Loaded"
        predicted_stage_text = "Not Available"
        stage_description = "The prediction model could not be loaded. Please contact the administrator."
        consolation_message = "Our system is experiencing technical difficulties. We apologize for the inconvenience."

    return {
        'predicted_stage': predicted_stage_text,
        'main_message': main_result_message,
        'stage_description': stage_description,
        'doctor_type': doctor_type,
        'next_steps_advice': next_steps_advice, # Returning list, serializer might need to json dumps this or FE handles it
        'consolation_message': consolation_message
    }


# --- Wrappers for other services ---

def predict_spiral_wrapper(image_path):
    try:
        from detection_app.spiral_predict import predict_spiral
        return predict_spiral(image_path)
    except ImportError:
        return "Spiral service not available"
    except Exception as e:
        return f"Error: {e}"

def is_valid_spiral_wrapper(image_path):
    try:
        from detection_app.spiral_validator import is_valid_spiral
        return is_valid_spiral(image_path)
    except ImportError:
        return False
    except Exception:
        return False

def predict_voice_wrapper(audio_path):
    # Reimplementing logic from voice_upload view as it's inline there
    try:
        from detection_app.feature_extraction import extract_features
        rf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'rf_model.pkl')
        scaler_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scaler.pkl')
        
        # Load from file if not loaded (or rely on cached loads)
        model = joblib.load(rf_path)
        scaler = joblib.load(scaler_path)

        features = extract_features(audio_path)
        scaled_features = scaler.transform([features])
        prediction = model.predict(scaled_features)[0]

        return "Parkinson's Detected" if prediction == 1 else "Healthy Voice"
    except Exception as e:
        print(f"Voice prediction error: {e}")
        return "Error in voice analysis"

def predict_brain_wrapper(image_path):
    # Reimplementing logic from brain_upload_view
    try:
        # Lazy import of heavy libs
        from tensorflow.keras.models import load_model
        from tensorflow.keras.preprocessing.image import load_img, img_to_array
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, 'detection_app', 'models', 'brain_model.h5')
        
        if not os.path.exists(model_path):
            return "Model not found"
            
        brain_model = load_model(model_path)
        
        img = load_img(image_path, target_size=(224, 224))
        img_array = img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        prediction = brain_model.predict(img_array)[0][0]
        return "Parkinson Detected" if prediction > 0.5 else "Normal"
        
    except Exception as e:
        print(f"Brain prediction error: {e}")
        return "Error in brain analysis"

def is_valid_mri_wrapper(image_path):
    try:
        from detection_app.mri_validator import is_valid_mri
        return is_valid_mri(image_path)
    except ImportError:
        return False
    except Exception:
        return False
