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
        # base_dir should be project root (parkinson_detection_system_final)
        # file is in detection_app/api/services/prediction_service.py
        # 1. services
        # 2. api
        # 3. detection_app
        # 4. root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # FIX: Use new model rf_model_parkinson.pkl (in root)
        rf_path = os.path.join(base_dir, 'rf_model_parkinson.pkl')
        # Scaler is skipped as per manual fix
        
        if not os.path.exists(rf_path):
             return "Voice model missing"

        # Load from file if not loaded (or rely on cached loads)
        model = joblib.load(rf_path)
        # scaler = joblib.load(scaler_path) # REMOVED

        features = extract_features(audio_path)
        # Scaler skipped, reshape for single sample
        features_reshape = features.reshape(1, -1)
        
        prediction = model.predict(features_reshape)[0]

        return "Parkinson's Detected" if prediction == 1 else "Healthy Voice"
    except Exception as e:
        print(f"Voice prediction error: {e}")
        return f"Error in voice analysis: {e}"

def predict_brain_wrapper(image_path):
    # Reimplementing logic from brain_upload_view
    try:
        # Lazy import of heavy libs
        from tensorflow.keras.models import load_model
        from tensorflow.keras.preprocessing.image import load_img, img_to_array
        
        # base_dir should be project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # FIX: Use brain_model_recovered.h5
        model_path = os.path.join(base_dir, 'detection_app', 'models', 'brain_model_recovered.h5')
        
        if not os.path.exists(model_path):
            return "Model not found"
            
        brain_model = load_model(model_path, compile=False)
        
        img = load_img(image_path, target_size=(224, 224))
        img_array = img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        prediction = brain_model.predict(img_array, verbose=0)[0][0]
        return "Parkinson Detected" if prediction > 0.5 else "Normal"
        
    except Exception as e:
        print(f"Brain prediction error: {e}")
        return f"Error in brain analysis: {e}"

def is_valid_mri_wrapper(image_path):
    try:
        from detection_app.mri_validator import is_valid_mri
        return is_valid_mri(image_path)
    except ImportError:
        return False
    except Exception:
        return False

def calculate_risk_score(user):
    from detection_app.models import AssessmentResult, SpiralAssessmentResult, SpeechAssessmentResult, BrainScanResult

    # Normalization Logic
    # 1. Quiz (0-100)
    quiz_score = 0
    quiz_count = 0
    latest_quiz = AssessmentResult.objects.filter(user=user).order_by('-created_at').last() # Default ordering is correct, but let's be safe with .last() or order_by desc .first()
    # Actually models have ordering = ['created_at'], so .last() gives the most recent.
    # To be explicit: order_by('-created_at').first()
    latest_quiz = AssessmentResult.objects.filter(user=user).order_by('-created_at').first()
    
    if latest_quiz:
        quiz_count = 1
        stage_str = latest_quiz.predicted_stage.lower()
        if "no" in stage_str or "normal" in stage_str or "healthy" in stage_str:
            quiz_score = 0
        elif "stage 1" in stage_str:
            quiz_score = 20
        elif "stage 2" in stage_str:
            quiz_score = 40
        elif "stage 3" in stage_str:
            quiz_score = 60
        elif "stage 4" in stage_str:
            quiz_score = 80
        elif "stage 5" in stage_str:
            quiz_score = 100
        # If unknown string, defaults to 0 (conservative)
    
    # 2. Spiral (0 or 100)
    spiral_score = 0
    spiral_count = 0
    latest_spiral = SpiralAssessmentResult.objects.filter(user=user).order_by('-created_at').first()
    if latest_spiral:
        spiral_count = 1
        if "parkinson" in latest_spiral.result.lower():
            spiral_score = 100
        # else 0

    # 3. Voice (0 or 100)
    voice_score = 0
    voice_count = 0
    latest_voice = SpeechAssessmentResult.objects.filter(user=user).order_by('-created_at').first()
    if latest_voice:
        voice_count = 1
        if "parkinson" in latest_voice.result.lower():
            voice_score = 100
        # else 0
            
    # 4. Brain (0 or 100)
    brain_score = 0
    brain_count = 0
    latest_brain = BrainScanResult.objects.filter(user=user).order_by('-created_at').first()
    if latest_brain:
        brain_count = 1
        if "parkinson" in latest_brain.result.lower():
            brain_score = 100
        # else 0

    total_components = quiz_count + spiral_count + voice_count + brain_count
    
    if total_components == 0:
        return {
            "risk_percentage": 0,
            "message": "No assessments found.",
            "components": {}
        }
        
    avg_score = (quiz_score + spiral_score + voice_score + brain_score) / total_components
    
    return {
        "risk_percentage": round(avg_score, 2),
        "message": "Risk score based on latest assessments.",
        "components": {
            "quiz": {"score": quiz_score, "available": bool(quiz_count)},
            "spiral": {"score": spiral_score, "available": bool(spiral_count)},
            "voice": {"score": voice_score, "available": bool(voice_count)},
            "brain": {"score": brain_score, "available": bool(brain_count)}
        }
    }
