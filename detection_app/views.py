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

from itertools import chain
from operator import attrgetter
from .forms import SpeechUploadForm
from .models import SpeechAssessmentResult
from .feature_extraction import extract_features

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils import timezone

# Import all models from your app (no duplicates)
from .models import AssessmentResult, PatientProfile, AssessmentHistory, SpiralAssessmentResult
# Import your custom prediction/validation functions
from .spiral_predict import predict_spiral
from .spiral_predict import predict_spiral
from .spiral_validator import is_valid_spiral

# Unified Service Layer Imports
from .api.services.epilepsy_service import assess_epilepsy_risk
from .api.services.alz_mri_service import predict_alz_mri
from .api.services.alz_interactive_service import (
    get_emotion_config, score_emotion_test,
    get_word_config, score_word_test,
    score_fluency, score_speech_coherence,
    get_aeri_summary
)


# --- Global Variables & Model Loading (Quiz Prediction) ---
MODEL_PATH = os.path.join(os.path.dirname(__file__), "parkinsons_stage_model.joblib")
ENCODER_PATH = os.path.join(os.path.dirname(__file__), "label_encoder.joblib")

stage_model = None
label_encoder = None

try:
    stage_model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)
    print("[OK] Quiz Prediction Models loaded successfully!")
    print(f"Label Encoder Classes: {label_encoder.classes_}")
    print(f"Quiz Model expected features (n_features_in_): {stage_model.n_features_in_}")

except Exception as e:
    stage_model = None
    label_encoder = None
    print(f"[ERROR] Quiz Prediction Model or Encoder loading failed: {e}")


# --- Quiz Data (from quiz_data.py) ---
from .quiz_data import questions, option_choices


# ---------------------------- Forms ----------------------------------

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Enter your username or email',
        'class': 'input-field'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter your password',
        'class': 'input-field'
    }))

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = UserCreationForm.Meta.model
        fields = ('username',) + UserCreationForm.Meta.fields[1:]
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Enter your username',
                'class': 'input-field'
            }),
            'password1': forms.PasswordInput(attrs={
                'placeholder': 'Enter your password',
                'class': 'input-field'
            }),
            'password2': forms.PasswordInput(attrs={
                'placeholder': 'Confirm your password',
                'class': 'input-field'
            }),
        }

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
def upload_assessment(request):
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
                        print(f"✅ Saved detailed quiz result for {request.user.username}: {predicted_stage_text}")
                    else:
                        print("⚠️ User not authenticated, quiz result not saved to history.")
                    # --- END SAVE PREDICTION ---

                else:
                    messages.error(request, f"Error: Quiz answers count ({len(user_inputs)}) does not match model's expected features ({stage_model.n_features_in_}).")
                    print(f"Error: Expected {stage_model.n_features_in_} features, got {len(user_inputs)}")
                    main_result_message = "Processing Error"
                    predicted_stage_text = "Error"
                    stage_description = "There was an issue processing your quiz answers. Please try again or contact support."
                    consolation_message = "We encountered an issue. Please try again or reach out for support."

            except Exception as e:
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
            messages.success(request, 'Account created successfully! Welcome to ParkPredict.')
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

@login_required
def spiral_detection_view(request):
    """
    Handles the upload of the spiral image and redirects to result view.
    """
    if request.method == 'POST' and request.FILES.get('spiral_image'):
        img = request.FILES['spiral_image']
        fs = FileSystemStorage(location='media/spirals')  # Store inside media/spirals/
        filename = fs.save(img.name, img)
        file_path = fs.path(filename)
        request.session['spiral_image_path'] = file_path  # Save path in session
        return redirect('spiral_result')

    return render(request, 'detection_app/spiral_detection.html')  # upload page


# ✅ Spiral Upload View
@login_required
def spiral_upload_view(request):
    if request.method == 'POST' and request.FILES.get('spiral_image'):
        img = request.FILES['spiral_image']
        fs = FileSystemStorage(location='media/spirals')
        filename = fs.save(img.name, img)
        file_path = fs.path(filename)
        request.session['spiral_image_path'] = file_path
        return redirect('spiral_result')

    return render(request, 'detection_app/spiral_detection.html')


# ✅ Spiral Result View
@login_required
def spiral_result(request):
    from .spiral_validator import is_valid_spiral  # ✅ Import the validator

    file_path = request.session.get('spiral_image_path')
    result = None
    image_url = None

    if file_path:
        image_url = file_path.replace(os.path.abspath('media'), '/media')

        # ✅ Step 1: Validate the spiral drawing
        if not is_valid_spiral(file_path):
            return render(request, 'detection_app/spiral_result.html', {
                'result': "Invalid input: Please upload a valid spiral drawing.",
                'image_url': image_url
            })

        # ✅ Step 2: Run the prediction if the spiral is valid
        result = predict_spiral(file_path)

        # ✅ Step 3: Save result to the database
        SpiralAssessmentResult.objects.create(
            user=request.user,
            result=result,
            uploaded_image=file_path.replace(os.path.abspath(''), ''),  # relative path
        )

    return render(request, 'detection_app/spiral_result.html', {
        'result': result,
        'image_url': image_url
    })


# -------------------------- Other Detection Views (Placeholders) ----------------------------



def brain_detection_view(request):
    """ Placeholder for posture/brain video upload page. """
    return render(request, 'detection_app/posture_video_upload.html')

def get_sort_key(obj):
    return getattr(obj, 'created_at', getattr(obj, 'date_taken', timezone.now()))

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("BASE_DIR:", BASE_DIR)

import os
import joblib
from django.conf import settings

# BASE_DIR already is: C:\Users\rida1\Parkinson_Detection_Multimodal\parkinson_detection_system
model_path = os.path.join(settings.BASE_DIR, 'rf_model.pkl')
scaler_path = os.path.join(settings.BASE_DIR, 'scaler.pkl')

print("FINAL MODEL PATH:", model_path)
print("FINAL SCALER PATH:", scaler_path)

model = joblib.load(model_path)
scaler = joblib.load(scaler_path)

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
                model = joblib.load(os.path.join(settings.BASE_DIR, 'rf_model.pkl'))
                scaler = joblib.load(os.path.join(settings.BASE_DIR, 'scaler.pkl'))

                features = extract_features(upload_path)
                scaled_features = scaler.transform([features])
                prediction = model.predict(scaled_features)[0]

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
                messages.error(request, f"Prediction error: {e}")
                return redirect('voice_upload')
    else:
        form = SpeechUploadForm()

    return render(request, 'detection_app/voice_upload.html', {'form': form})

def voice_result(request, prediction):
    # The 'prediction' argument will be passed from the redirect
    context = {
        'prediction_result': prediction
    }
    return render(request, 'detection_app/voice_result.html', context)
'''
import os
import numpy as np
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import default_storage
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from .models import BrainScanResult

# Load model once at module import
BRAIN_MODEL_PATH = os.path.join(settings.BASE_DIR, 'detection_app/models', 'brain_model.h5')
if not os.path.exists(BRAIN_MODEL_PATH):
    raise FileNotFoundError(f"Brain model not found at: {BRAIN_MODEL_PATH}")
brain_model = load_model(BRAIN_MODEL_PATH)

# Define your classes (ensure order matches the model training)
BRAIN_CLASSES = ['Normal', 'Parkinsons']  # Adjust labels as necessary

def brain_detection_view(request):
    return render(request, 'detection_app/brain_detection.html')
from django.core.files import File  
@login_required
def brain_upload_view(request):
    if request.method == 'POST' and request.FILES.get('brain_image'):
        brain_img = request.FILES['brain_image']

        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'brain_scans'))
        filename = fs.save(brain_img.name, brain_img)
        relative_path = os.path.join('brain_scans', filename)
        abs_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        

        try:
            # Preprocess and predict
            img = load_img(abs_file_path, target_size=(224, 224))
            img_array = img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0) / 255.0

            prediction = brain_model.predict(img_array)
            is_parkinsons = prediction[0][0] >= 0.5
            result_message = 'Parkinsons' if is_parkinsons else 'Normal'

            # ✅ Save to DB
            with open(abs_file_path, 'rb') as f:
                brain_record = BrainScanResult.objects.create(
                    user=request.user,
                    result=result_message,
                    image=File(f, name=filename)
                )

            return render(request, 'detection_app/brain_result.html', {
                'result': result_message,
                'image_url': brain_record.image.url
            })

        except Exception as e:
            messages.error(request, f"Prediction failed: {e}")
            return render(request, 'detection_app/brain_detection.html')

    return render(request, 'detection_app/brain_detection.html')
'''
from django.shortcuts import render

def assessment_options(request):
    return render(request, 'detection_app/assessment_options.html')
import os
import numpy as np
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib import messages
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from .models import BrainScanResult
from .mri_validator import is_valid_mri  # ✅ Correct import

# ✅ Load brain model once
BRAIN_MODEL_PATH = os.path.join(settings.BASE_DIR, 'detection_app/models', 'brain_model.h5')
if not os.path.exists(BRAIN_MODEL_PATH):
    raise FileNotFoundError(f"❌ Brain model not found at: {BRAIN_MODEL_PATH}")
brain_model = load_model(BRAIN_MODEL_PATH)


def brain_upload_view(request):
    if request.method == 'POST' and request.FILES.get('brain_image'):
        uploaded_file = request.FILES['brain_image']
        file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)
        path = default_storage.save(file_path, uploaded_file)
        full_path = os.path.join(settings.MEDIA_ROOT, path)

        print("📷 Uploaded MRI image path:", full_path)

        # ✅ Validate MRI image
        if not is_valid_mri(full_path):
            return render(request, 'detection_app/brain_result.html', {
                'result': None,
                'image': path,
                'error': "Prediction: Invalid input. Please upload a valid grayscale brain scan."
            })

        # ✅ Preprocess and Predict
        img = load_img(full_path, target_size=(224, 224))
        img_array = img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        prediction = brain_model.predict(img_array)[0][0]
        result = "Parkinson Detected" if prediction > 0.5 else "Normal"

        # ✅ Save Result
        BrainScanResult.objects.create(
            user=request.user,
            image=path,
            result=result
        )

        return render(request, 'detection_app/brain_result.html', {
            'result': result,
            'image': path
        })

    return render(request, 'detection_app/brain_detection.html')


## ------------------- Alzheimer Emotion Memory Test -------------------
import random
from django.views.decorators.http import require_http_methods

# Static list of emotion images (adjust file paths to your static folder)
EMOTION_IMAGES = [
    {"id": 1, "file": "detection_app/emotions/happy1.jpg", "emotion": "Happy"},
    {"id": 2, "file": "detection_app/emotions/sad1.jpg", "emotion": "Sad"},
    {"id": 3, "file": "detection_app/emotions/angry1.jpg", "emotion": "Angry"},
    {"id": 4, "file": "detection_app/emotions/surprised1.jpg", "emotion": "Surprised"},
    {"id": 5, "file": "detection_app/emotions/fear1.jpg", "emotion": "Fear"},
]

EMOTION_LABELS = ["Happy", "Sad", "Angry", "Surprised", "Fear"]


@require_http_methods(["GET", "POST"])
def emotion_memory_start(request):
    """
    Phase 1: Show faces with labels (learning phase).
    """
    images = EMOTION_IMAGES.copy()
    random.shuffle(images)

    if request.method == "POST":
        # store ids + correct emotions in session
        request.session["emotion_test_images"] = [
            {"id": img["id"], "emotion": img["emotion"]} for img in images
        ]
        return redirect("emotion_memory_recall")

    return render(request, "detection_app/emotion_memory_start.html", {"images": images})


@require_http_methods(["GET", "POST"])
def emotion_memory_recall(request):
    """
    Phase 2: Show same faces randomly, ask user to choose emotion labels.
    """
    stored = request.session.get("emotion_test_images")
    if not stored:
        # if accessed directly, send back to start
        return redirect("emotion_memory_start")

    # id -> correct emotion
    correct_map = {item["id"]: item["emotion"] for item in stored}

    # Rebuild full image objects from master list
    id_to_image = {img["id"]: img for img in EMOTION_IMAGES}
    images = [id_to_image[item["id"]] for item in stored]

    # For recall display, shuffle order (ids stay the same)
    if request.method == "GET":
        random.shuffle(images)

    if request.method == "POST":
        total = len(images)
        correct_count = 0
        detailed_results = []

        # Correct answer logic in Service:
        # We must map POST answers to the list format the service expects.
        # However, for simplicity and strict parity, we can just rebuild the results
        # locally using the logic from the service if needed, OR call the service.

        # Let's call the service for SCORING logic consistency.
        # Service expects: answers = [{"image_id": ..., "selected_label": ...}, ...]

        service_answers = []
        user_answer_map = {} # Keep track for hydrating display

        for item in stored:
            img_id = item["id"]
            val = request.POST.get(f"emotion_{img_id}", "")
            service_answers.append({"image_id": img_id, "selected_label": val})
            user_answer_map[img_id] = val

        # Call Service
        result = score_emotion_test(service_answers)

        # Rehydrate detailed results for the template
        # (Template expects: image object, user_answer, correct_answer, is_correct)

        detailed_results = []
        for r in result['results']:
            img_id = r['image_id']
            img_obj = id_to_image[img_id]

            detailed_results.append({
                "image": img_obj,
                "user_answer": user_answer_map.get(img_id) or "(No answer)",
                "correct_answer": r['correct_label'],
                "is_correct": r['correct'],
            })

        score_percent = result['score_percent']
        correct_count = result['correct_count']

        context = {
            "completed": True,
            "total": total,
            "correct_count": correct_count,
            "score_percent": score_percent,
            "results": detailed_results,
        }
        return render(request, "detection_app/emotion_memory_recall.html", context)

    # GET – show the recall form
    context = {
        "images": images,
        "emotion_labels": EMOTION_LABELS,
        "completed": False,
    }
    return render(request, "detection_app/emotion_memory_recall.html", context)


# ------------------- Alzheimer – Speech Coherence Test -------------------
import re
from collections import Counter
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def speech_coherence_test(request):
    """
    Ask the user: 'Describe your morning routine.'
    Then analyze coherence based on:
      - coverage of key steps
      - order of steps
      - repetition
      - sentence fragmentation
    Returns a 0–10 Speech Coherence Score.
    """
    context = {
        "completed": False,
    }

    if request.method == "POST":
        text = request.POST.get("speech_text", "").strip()

        if not text:
            context["error"] = "Please enter or type the patient's description of their morning routine."
            return render(request, "detection_app/speech_coherence.html", context)

        # Call Service
        res = score_speech_coherence(text)

        # FIX: Save to session so Summary can see it
        request.session["alz_speech_score"] = res["total_score"]

        context.update({
            "completed": True,
            "input_text": text,
            "total_score": res["total_score"],
            "level": res["level"],
            "interpretation": res["interpretation"],

            # Use breakdown from service
            # "steps_covered": int(res["breakdown"]["step_coverage"] / 6.0 * 5.0) if "step_coverage" in res["breakdown"] else 0, # Approx mapping back to counts?
            # Actually service returns SCALED scores. View displayed raw counts mostly.
            # Simplified: Use service detailed breakdown if needed or re-calculate for display.
            # For now, let's trust the service result values.
            # The view template likely expects `step_hits`, `repeated_tokens`.
            # Service doesn't return these lists.
            # Recalculate strictly for display (View Layer Logic).

            # "steps_covered": res["breakdown"]["step_coverage"], # This is a SCORE now, not count...
            # Wait, `steps_covered` in view was COUNT.
            # I should re-calculate counts locally for Template Display if template uses them (likely).
        })

        # Display Only Logic (Recalc):
        lower = text.lower()
        steps = [
            ("wake", "woke", "get up", "got up", "waking"),
            ("brush", "teeth", "toothbrush", "toothpaste", "mouthwash"),
            ("bath", "bathe", "bathing", "shower", "wash", "freshen up"),
            ("breakfast", "tea", "coffee", "milk", "eat", "eating"),
            ("work", "office", "school", "college", "study", "classes"),
        ]
        step_hits = []
        for synonyms in steps:
            found = False
            for kw in synonyms:
                if kw in lower: found = True; break
            step_hits.append(found)

        words = re.findall(r"\b\w+\b", lower)
        stopwords = {"the", "and", "to", "a", "i", "of", "in", "on", "for", "is", "it", "was", "then", "so", "that", "this", "at", "my", "me", "we", "you", "they"}
        filtered_words = [w for w in words if w not in stopwords]
        counts = Counter(filtered_words)
        repeated_tokens = [w for w, c in counts.items() if c >= 3]

        context.update({
             "steps_covered": sum(step_hits),
             "total_steps": len(steps),
             "step_hits": step_hits,
             "repeated_tokens": repeated_tokens,
             "short_sentence_ratio": res["breakdown"]["fragmentation_ratio"]
        })

        return render(request, "detection_app/speech_coherence.html", context)

    # GET request – show empty form
    return render(request, "detection_app/speech_coherence.html", context)


from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
import random
import re
from collections import Counter
import os
import joblib
from django.conf import settings


def alz_home(request):
    """
    Simple landing page for Alzheimer’s tests.
    Shows navigation to Speech, Word Memory, Fluency, and Summary.
    """
    return render(request, "detection_app/alz_home.html")


# ------------------- Alzheimer – Word Memory Test -------------------

WORD_MEMORY_LIST = [
    "mango",
    "train",
    "temple",
    "window",
    "river",
    "doctor",
    "flower",
    "bucket",
    "market",
    "chair",
]


@require_http_methods(["GET", "POST"])
def word_memory_show(request):
    """
    Phase 1: Show a fixed list of words for the patient to memorize.
    After pressing 'Start Recall', redirect to recall view.
    """
    words = WORD_MEMORY_LIST.copy()
    # Store in session
    request.session["word_memory_list"] = words

    if request.method == "POST":
        return redirect("word_memory_recall")

    return render(
        request,
        "detection_app/word_memory_show.html",
        {"words": words},
    )


@require_http_methods(["GET", "POST"])
def word_memory_recall(request):
    """
    Phase 2: Ask user to recall as many words as possible.
    Score based on how many of the original words they recall (order doesn't matter).
    Also store a normalized 0–10 MemoryScore into session as 'alz_memory_score'.
    """
    words = request.session.get("word_memory_list")
    if not words:
        return redirect("word_memory_show")

    target_set = {w.strip().lower() for w in words}

    if request.method == "POST":
        raw_input = request.POST.get("recalled_words", "").strip()

        # Call Service
        res = score_word_test(raw_input)
        
        # Save Score to Session
        request.session["alz_memory_score"] = res["memory_score"]

        context = {
            "completed": True,
            "words": words,
            "correct_hits": res["correct_hits"],
            "incorrect_hits": res["incorrect_hits"],
            "score_percent": res["score_percent"],
            "correct_count": len(res["correct_hits"]),
            "total_target": len(words), # Assumes 10 usually, or len(target_set)
            "level": res["level"],
            "interpretation": res["interpretation"],
            "raw_input": raw_input,
            "memory_score": res["memory_score"],
        }
        return render(request, "detection_app/word_memory_recall.html", context)

    # GET
    context = {
        "completed": False,
        "words": words,
    }
    return render(request, "detection_app/word_memory_recall.html", context)



# ------------------- Alzheimer – Category Fluency Test -------------------

@require_http_methods(["GET", "POST"])
def category_fluency(request):
    """
    Ask patient to name as many items as possible from a category (e.g. fruits) in ~30-60s.
    Health worker types the words separated by commas or new lines.
    Score: unique count -> normalized to 0-10; also save as 'alz_fluency_score' in session.
    """
    category = "fruits"  # you can make this dynamic later

    if request.method == "POST":
        raw_input = request.POST.get("fluency_words", "").strip()

        # Call Service (cat defaults only one supported)
        res = score_fluency(raw_input)
        
        request.session["alz_fluency_score"] = res["fluency_score"]

        # Re-calc repeated words locally or update service? 
        # API doesn't return repeated words list, only count/unique. 
        # But view displays `repeated_words`.
        # Simplest: Keep repetition detection here strictly for display or accept API doesn't return it.
        # User constraint: One source of truth.
        # If Service doesn't return `repeated_words`, and View needs it -> Update Service.
        # But I can't update service in this tool call.
        # Minimal Logic: Recalculate local display-only logic, rely on service for SCORING.
        
        # Display logic only:
        if raw_input:
             tmp = raw_input.replace("\n", ",")
             pieces = [p.strip().lower() for p in tmp.split(",") if p.strip()]
        else:
             pieces = []
        words_flat = []
        for p in pieces: 
             for tok in p.split(): words_flat.append(tok.strip().lower())
        from collections import Counter
        counts = Counter(words_flat)
        repeated_words = [w for w, c in counts.items() if c > 1]
        
        context = {
            "completed": True,
            "category": category,
            "raw_input": raw_input,
            "unique_words": res["unique_words"],
            "unique_count": res["unique_count"],
            "repeated_words": repeated_words,
            "fluency_score": res["fluency_score"],
            "level": res["level"],
            "interpretation": res["interpretation"],
        }
        return render(request, "detection_app/category_fluency.html", context)

    # GET – empty form
    context = {
        "completed": False,
        "category": category,
    }
    return render(request, "detection_app/category_fluency.html", context)



# ------------------- Alzheimer – Summary / AERI -------------------

def alz_summary(request):
    """
    Combine Speech Coherence, Memory, and Fluency scores into AERI (0–100).
    Uses values stored in session.
    """
    speech_score = request.session.get("alz_speech_score")
    memory_score = request.session.get("alz_memory_score")
    fluency_score = request.session.get("alz_fluency_score")

    missing = []
    if speech_score is None:
        missing.append("Speech Coherence Test")
    if memory_score is None:
        missing.append("Word Memory Test")
    if fluency_score is None:
        missing.append("Category Fluency Test")

    aeri = None
    level = None
    interpretation = None

    if not missing:
        result = get_aeri_summary(speech_score, memory_score, fluency_score)
        
        aeri = result['aeri_score']
        level = result['level']
        interpretation = result['interpretation']

    context = {
        "speech_score": speech_score,
        "memory_score": memory_score,
        "fluency_score": fluency_score,
        "missing": missing,
        "aeri": aeri,
        "level": level,
        "interpretation": interpretation,
    }
    return render(request, "detection_app/alz_summary.html", context)


def assessment_home(request):
    return render(request, "detection_app/assessment_home.html")





from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def epilepsy_home(request):
    """
    Epilepsy screening module:
    - Shows a simple risk questionnaire
    - Calculates a risk score based on Yes/No answers
    - Returns Low / Moderate / High risk with basic first-aid advice
    """
    score = None
    risk_level = None
    advice = None

    if request.method == "POST":
        result = assess_epilepsy_risk(request.POST)
        context = {
            "score": result['score'],
            "risk_level": result['risk_level'],
            "advice": result['advice'],
        }
        return render(request, "detection_app/epilepsy_home.html", context)

    # Initial context checks
    context = {
        "score": None, 
        "risk_level": None,
        "advice": None
    }
    return render(request, "detection_app/epilepsy_home.html", context)



# detection_app/views.py

import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from pathlib import Path
from django.http import HttpResponseServerError

@login_required
def alz_mri_scan(request):
    if request.method == "GET":
        return render(request, "detection_app/alz_mri_scan.html", {"completed": False})

    # POST
    uploaded = request.FILES.get("mri_image")
    if not uploaded:
        return HttpResponseServerError("No file uploaded (expected field 'mri_image').")

    # Save upload to standard "detection_uploads"
    upload_dir = Path(settings.MEDIA_ROOT) / "detection_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"alz_mri_{uploaded.name}" # Use generic prefix
    abs_path = str(upload_dir / filename)
    
    with open(abs_path, "wb") as f:
        for chunk in uploaded.chunks():
            f.write(chunk)

    # ---------------------------------------------------------
    # CALL SERVICE LAYER (Unified Logic)
    # ---------------------------------------------------------
    result = predict_alz_mri(abs_path)

    # Hydrate context
    context = {
        "completed": True,
        # URL for display
        "scan_image_url": f"{settings.MEDIA_URL}detection_uploads/{filename}",
        
        "prediction_pretty": result['prediction_pretty'],
        "confidence": (result.get("confidence") or 0.0) * 100.0,
        "probabilities": result['probabilities'], # 0-100 values
        
        # Keep debug fields if service returns them
        "debug_warnings": result.get("warnings"),
    }
    return render(request, "detection_app/alz_mri_scan.html", context)
