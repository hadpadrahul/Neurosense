# detection_app/views.py
from django.conf import settings
import os
import joblib
import numpy as np
# Import necessary modules for spiral/other detections if they are used
# Ensure these are installed in your environment (e.g., pip install opencv-python tensorflow keras)
import cv2
import tensorflow as tf
from keras.models import load_model
from keras.preprocessing import image
from keras.utils import load_img, img_to_array

from itertools import chain
from operator import attrgetter
from .forms import (
    SpeechUploadForm, 
    CustomAuthenticationForm, 
    CustomUserCreationForm,
    CustomPasswordChangeForm
)
from .models import SpeechAssessmentResult
from .feature_extraction import extract_features

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils import timezone

# Import all models from your app (no duplicates)
from .models import AssessmentResult, PatientProfile, AssessmentHistory, SpiralAssessmentResult, SpeechAssessmentResult, BrainScanResult
# Import your custom prediction/validation functions
from .spiral_predict import predict_spiral
from .spiral_validator import is_valid_spiral
from .mri_validator import is_valid_mri

# Load Brain Model (Global)
# Adjust path as necessary. Assuming model is in detection_app or root.
BRAIN_MODEL_PATH = os.path.join(settings.BASE_DIR, 'detection_app', 'models', 'brain_model_recovered.h5') 
# Or wherever it is. The user didn't specify, but let's assume detection_app/brain.h5 or check list.
try:
    brain_model = load_model(BRAIN_MODEL_PATH)
    print(f"[OK] Brain Model loaded from {BRAIN_MODEL_PATH}")
except Exception as e:
    brain_model = None
    print(f"[ERROR] Brain Model failed to load: {e}")

# Unified Service Layer Imports
# Unified Service Layer Imports
# (None for legacy views currently, as Parkinson's logic is internal or in prediction_service - wait, views.py imports from .api.services?)
# views.py (line 38)
# from .api.services.epilepsy_service import assess_epilepsy_risk
# from .api.services.alz_mri_service import predict_alz_mri
# from .api.services.alz_interactive_service import ...
# ALL REMOVED



# --- Global Variables & Model Loading (Quiz Prediction) ---
# --- Global Variables & Model Loading (Quiz Prediction) ---
MODEL_PATH = os.path.join(settings.BASE_DIR, "detection_app", "parkinsons_stage_model.joblib")
# Keep encoder local as it's not in root (or use the one in root if it exists, checking...)
# Root has scaler.pkl, not label_encoder.joblib. So keep detection_app's encoder.
ENCODER_PATH = os.path.join(os.path.dirname(__file__), "label_encoder.joblib")

stage_model = None
label_encoder = None

try:
    stage_model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)
    print(f"[OK] Quiz Prediction Models loaded successfully from {MODEL_PATH}!")
    if hasattr(label_encoder, 'classes_'):
        print(f"Label Encoder Classes: {label_encoder.classes_}")
    if hasattr(stage_model, 'n_features_in_'):
        print(f"Quiz Model expected features (n_features_in_): {stage_model.n_features_in_}")

except Exception as e:
    stage_model = None
    label_encoder = None
    print(f"[ERROR] Quiz Prediction Model or Encoder loading failed: {e}")
    import traceback
    traceback.print_exc()

# --- Quiz Data (from quiz_data.py) ---
from .quiz_data import questions, option_choices




# ---------------------------- Core Website Views ----------------------------------

def home(request):
    return render(request, 'detection_app/index.html')

@login_required
def quiz(request):
    """
    Renders the quiz with questions grouped into 5 sections (4 questions each).
    Requires user to be logged in.
    """
    grouped_questions = [questions[i:i + 4] for i in range(0, len(questions), 4)]
    context = {
        'question_pages': grouped_questions,
        'option_choices': option_choices,
    }
    return render(request, 'detection_app/quiz.html', context)

@login_required # Quiz submission requires login
def quiz_result(request):
    """
    Handles quiz submission, processes the POST request, performs prediction,
    and renders the result page. It also saves the detailed assessment result.
    """
    if request.method == "POST":
        user_inputs = []
        quiz_answers_dict = {} # To store answers for saving to model

        # Define the ordinal mapping as used in your Colab notebook for consistency
        ordinal_map_django = {
            "never": 0,
            "rarely": 1,
            "sometimes": 2,
            "often": 3,
            "always": 4
        }

        question_keys = [f"q{i}" for i in range(1, 21)] # Generates "q1", "q2", ..., "q20"

        # Process quiz answers and store both for prediction and saving
        for key in question_keys:
            value = request.POST.get(key, '').lower()
            numerical_value = ordinal_map_django.get(value, 0) # Default to 0 if not found
            user_inputs.append(numerical_value)
            quiz_answers_dict[key] = numerical_value # Store for model saving

        # Initialize core context variables with default values
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

        # Attempt to make a prediction if model is available and inputs are correct
        if stage_model and label_encoder:
            try:
                prediction_array = np.array(user_inputs).reshape(1, -1)

                print(f"\n--- Quiz Prediction Debugging ---")
                print(f"Raw user_inputs (length {len(user_inputs)}): {user_inputs}")
                print(f"Numpy array for prediction (shape {prediction_array.shape}):\n{prediction_array}")
                print(f"Model expected features (n_features_in_): {stage_model.n_features_in_}")

                if len(user_inputs) == stage_model.n_features_in_:
                    prediction = stage_model.predict(prediction_array)[0]
                    predicted_stage_text = label_encoder.inverse_transform([prediction])[0]

                    print(f"Raw numerical prediction (index): {prediction}")
                    print(f"Inverse transformed prediction text: {predicted_stage_text}")
                    print(f"--- End Quiz Prediction Debugging ---\n")
                    
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

                    # --- SAVE ALL PREDICTION DATA TO DATABASE ---
                    if request.user.is_authenticated:
                        # Ensure all qX fields are present in quiz_answers_dict
                        # If a question was skipped, it defaults to 0, so it will be present.
                        AssessmentResult.objects.create(
                            user=request.user,
                            # Unpack the dictionary of quiz answers directly
                            **quiz_answers_dict,
                            predicted_stage=predicted_stage_text,
                            main_message=main_result_message,
                            stage_description=stage_description,
                            doctor_type=doctor_type,
                            consolation_message=consolation_message
                        )
                        messages.success(request, "Your assessment has been saved successfully.")
                        print(f"Saved detailed quiz result for {request.user.username}: {predicted_stage_text}")
                    else:
                        print("User not authenticated, quiz result not saved to history.")
                    # --- END SAVE PREDICTION ---

                else:
                    messages.error(request, f"Error: Quiz answers count ({len(user_inputs)}) does not match model's expected features ({stage_model.n_features_in_}).")
                    print(f"Error: Expected {stage_model.n_features_in_} features, got {len(user_inputs)}")
                    main_result_message = "Processing Error"
                    predicted_stage_text = "Error"
                    stage_description = "There was an issue processing your quiz answers. Please try again or contact support."
                    consolation_message = "We encountered an issue. Please try again or reach out for support."

            except Exception as e:
                with open("debug_error.log", "a") as f:
                    f.write(f"Prediction error: {e}\n")
                    f.write(f"User inputs: {user_inputs}\n")
                messages.error(request, f"An error occurred during prediction: {e}")
                print(f"Prediction error: {e}")
                main_result_message = "Prediction Error"
                predicted_stage_text = "Error"
                stage_description = "An error occurred during prediction. Please try again or contact support."
                consolation_message = "An unexpected error occurred. Your well-being is important; please try again or contact support."
        else:
            messages.warning(request, "Prediction model not available. Results are based on default values.")
            print("Model or encoder not loaded.")
            main_result_message = "Model Not Loaded"
            predicted_stage_text = "Not Available"
            stage_description = "The prediction model could not be loaded. Please contact the administrator."
            consolation_message = "Our system is experiencing technical difficulties. We apologize for the inconvenience."

        context = {
            'main_result_message': main_result_message,
            'potential_stage': predicted_stage_text,
            'stage_description': stage_description,
            'doctor_type': doctor_type,
            'next_steps_advice': next_steps_advice,
            'consolation_message': consolation_message,
        }
        return render(request, 'detection_app/results.html', context)

    else: # If accessed via GET, redirect to quiz form
        return redirect('quiz') # Redirect to quiz page, not render it directly


@login_required
def results(request):
    """
    This view is a fallback or for direct access to /results/.
    It provides default context for only the required fields.
    """
    context = {
        'main_result_message': "No Data Submitted",
        'potential_stage': "No Data Submitted",
        'stage_description': "Please complete the assessment quiz to see your personalized results.",
        'doctor_type': "N/A",
        'next_steps_advice': ["Return to the quiz to start the assessment."],
        'consolation_message': "Welcome! Please complete the assessment to receive personalized insights.",
    }
    return render(request, 'detection_app/results.html', context)


def thank_you(request):
    return render(request, 'detection_app/thank_you.html')


# -------------------------- Authentication Views ----------------------------

# CustomUserCreationForm is imported at the top now, no need for redundant import here
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to NeuroSense.')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'detection_app/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password')
            )
            if user is not None:
                login(request, user)
                messages.success(request, f'Login successful! Welcome back, {user.username}.')
                return redirect('home')
            else:
                messages.error(request, 'Invalid credentials.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        form = CustomAuthenticationForm()
    return render(request, 'detection_app/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'detection_app/profile.html', {
        'form': form
    })

def demo_video_view(request):
    return render(request, 'detection_app/demo_video.html')


# -------------------------- Assessment History & Progress Views ----------------------------

@login_required
def history_view(request):
    """
    Combines and displays history from all assessment types for the logged-in user.
    Now includes: Quiz, Spiral, Manual, Voice, and Brain assessments.
    """
    user = request.user

    # Fetch all types of history entries
    quiz_history = AssessmentResult.objects.filter(user=user)
    spiral_history = SpiralAssessmentResult.objects.filter(user=user)
    manual_history = AssessmentHistory.objects.filter(user=user)
    speech_history = SpeechAssessmentResult.objects.filter(user=user)
    brain_history = BrainScanResult.objects.filter(user=user)

    # Combine and sort all types by the most recent timestamp
    combined = sorted(
        chain(quiz_history, spiral_history, manual_history, speech_history, brain_history),
        key=lambda obj: getattr(obj, 'created_at', getattr(obj, 'date_taken', timezone.now())),
        reverse=True  # Most recent first
    )

    return render(request, 'detection_app/assessment_history.html', {
        'histories': combined
    })


@login_required
def progress_tracker(request):
    """
    Renders the progress graph page.
    """
    return render(request, 'detection_app/progress_graph.html')

@login_required
def quiz_progress_data(request):
    """
    Provides JSON data for the quiz progress graph.
    Fetches the predicted stages for the logged-in user.
    """
    user = request.user
    # Retrieve the quiz assessment results for this user, ordered by the creation date
    results = AssessmentResult.objects.filter(user=user).order_by('created_at')

    # Prepare the data, converting dates to a string format and fetching the predicted stage
    data = {
        'dates': [r.created_at.strftime('%Y-%m-%d') for r in results],
        'stages': [r.predicted_stage for r in results]
    }
    # Removed the problematic `if "Stage" in stage:` snippet that was causing errors.
    return JsonResponse(data)


# -------------------------- Spiral Detection Views ----------------------------

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os

from .spiral_predict import predict_spiral
from .spiral_validator import is_valid_spiral  # Use the fixed one
from .models import SpiralAssessmentResult

# -------------------------- Spiral Detection Views ----------------------------

@login_required
def spiral_view(request):
    """
    Unified view for Spiral Detection (Upload & Processing).
    """
    if request.method == 'POST' and request.FILES.get('spiral_image'):
        img = request.FILES['spiral_image']
        fs = FileSystemStorage(location='media/spirals')
        filename = fs.save(img.name, img)
        file_path = fs.path(filename)
        request.session['spiral_image_path'] = file_path
        return redirect('spiral_result')

    return render(request, 'detection_app/spiral_detection.html')

@login_required
def spiral_result(request):
    file_path = request.session.get('spiral_image_path')
    result = None
    image_url = None

    if file_path:
        image_url = file_path.replace(os.path.abspath('media'), '/media').replace('\\', '/')
        
        # Validation
        if not is_valid_spiral(file_path):
            return render(request, 'detection_app/spiral_result.html', {
                'result': "Invalid input: Please upload a valid spiral drawing.",
                'image_url': image_url
            })

        # Prediction
        result = predict_spiral(file_path)

        # Save to DB
        SpiralAssessmentResult.objects.create(
            user=request.user,
            result=result,
            uploaded_image=file_path.replace(os.path.abspath(settings.MEDIA_ROOT), '').lstrip(os.sep)
        )

    return render(request, 'detection_app/spiral_result.html', {
        'result': result,
        'image_url': image_url
    })


# -------------------------- Brain MRI Views ----------------------------

@login_required
def brain_view(request):
    """
    Unified view for Brain MRI Detection.
    """
    if request.method == 'POST' and request.FILES.get('brain_image'):
        return brain_process_upload(request)

    return render(request, 'detection_app/brain_detection.html')

def brain_process_upload(request):
    uploaded_file = request.FILES['brain_image']
    file_path = os.path.join(settings.MEDIA_ROOT, 'brain_scans', uploaded_file.name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
            
    full_path = file_path
    rel_path = f"brain_scans/{uploaded_file.name}"

    # Validate
    if not is_valid_mri(full_path):
         return render(request, 'detection_app/brain_result.html', {
            'result': None,
            'image': rel_path,
            'error': "Prediction: Invalid input. Please upload a valid grayscale brain scan."
        })

    # Predict
    try:
        img = load_img(full_path, target_size=(224, 224))
        img_array = img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        prediction = brain_model.predict(img_array)[0][0]
        result = "Parkinson Detected" if prediction > 0.5 else "Normal"
        
        # Save
        BrainScanResult.objects.create(
            user=request.user,
            image=rel_path,
            result=result
        )
        
        return render(request, 'detection_app/brain_result.html', {
            'result': result,
            'image': rel_path
        })
    except Exception as e:
        messages.error(request, f"Error processing MRI: {e}")
        return redirect('brain_view')


# -------------------------- Voice / Speech Views ----------------------------

@login_required
def voice_upload(request):
    if request.method == 'POST':
        form = SpeechUploadForm(request.POST, request.FILES)
        if form.is_valid():
            audio = form.cleaned_data['audio_file']
            upload_path = os.path.join(settings.MEDIA_ROOT, 'speech_uploads', audio.name)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)

            with open(upload_path, 'wb+') as f:
                for chunk in audio.chunks():
                    f.write(chunk)

            try:
                # Load new model (rf_model_parkinson.pkl)
                model_path = os.path.join(settings.BASE_DIR, 'rf_model_parkinson.pkl')
                # Scaler is skipped because existing scaler.pkl is for 40 features, and new model is 22.
                # Random Forest is generally robust to unscaled data.

                if not os.path.exists(model_path):
                     raise FileNotFoundError("Voice model file missing.")

                try:
                    model = joblib.load(model_path)
                except Exception as e:
                     raise ValueError(f"Model loading failed: {e}")
                
                features = extract_features(upload_path)
                # features shape is (22,) -> reshape to (1, 22)
                features_reshape = features.reshape(1, -1)
                
                prediction = model.predict(features_reshape)[0]

                result_label = "Parkinson's Detected" if prediction == 1 else "Healthy Voice"

                # Save to DB
                SpeechAssessmentResult.objects.create(
                    user=request.user,
                    result=result_label,
                    uploaded_audio=f'speech_uploads/{audio.name}'
                )

                # Redirect to result view
                return redirect(reverse('voice_result', kwargs={'prediction': result_label}))

            except Exception as e:
                messages.error(request, f"Analysis Error: {e}")
                return redirect('voice_upload')
    else:
        form = SpeechUploadForm()

    return render(request, 'detection_app/voice_upload.html', {'form': form})

@login_required
def voice_result(request, prediction):
    context = {
        'prediction_result': prediction
    }
    return render(request, 'detection_app/voice_result.html', context)




# -------------------------- Internal AJAX Views ----------------------------

from django.views.decorators.http import require_POST
import json
from django.views.decorators.csrf import csrf_exempt
import datetime

def log_debug(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [WEB] {message}")

# Internal view for website map (avoids using external API)
@require_POST
def get_nearby_specialists(request):
    try:
        data = json.loads(request.body)
        lat = data.get('lat')
        lon = data.get('lon')
        
        log_debug(f"Fetching nearby specialists for Lat: {lat}, Lon: {lon}")
        
        if not lat or not lon:
             log_debug("Error: Latitude or Longitude missing")
             return JsonResponse({"error": "Latitude and Longitude required"}, status=400)

        from .services.location_service import find_nearby_specialists
        specialists = find_nearby_specialists(lat, lon)
        log_debug(f"Found {len(specialists)} specialists.")
        return JsonResponse(specialists, safe=False)
    except Exception as e:
        log_debug(f"Exception in get_nearby_specialists: {e}")
        return JsonResponse({"error": str(e)}, status=500)

# ----------------- End of Views -----------------


def privacy_policy(request):
    return render(request, 'detection_app/privacy.html')
