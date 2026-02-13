from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import F
from itertools import chain
from operator import attrgetter

from detection_app.models import (
    AssessmentResult, 
    SpiralAssessmentResult, 
    SpeechAssessmentResult, 
    BrainScanResult,
    AssessmentHistory
)
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from pathlib import Path
import os

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail

from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegistrationSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserSerializer,
    AssessmentResultSerializer,
    SpiralAssessmentResultSerializer,
    SpeechAssessmentResultSerializer,
    BrainScanResultSerializer,
    UnifiedHistorySerializer
)
from .services.prediction_service import (
    predict_quiz, 
    predict_spiral_wrapper, 
    is_valid_spiral_wrapper,
    predict_voice_wrapper,
    predict_brain_wrapper,
    is_valid_mri_wrapper
)

import datetime

def log_api(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [API] {message}")

# ----------------- Authentication -----------------

class RegisterAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegistrationSerializer

    def post(self, request, *args, **kwargs):
        log_api(f"Registration request for username: {request.data.get('username')}")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "user": UserSerializer(user).data,
                "message": "User created successfully. Now perform Login to get token",
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class ProfileAPIView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class ChangePasswordAPIView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(serializer.data.get("new_password"))
            user.save()
            return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Generate Token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Print to Console (Simulating Email)
            reset_link = f"http://localhost:8000/api/v1/password-reset-confirm/?uid={uid}&token={token}"
            print("\n" + "="*50)
            print("PASSWORD RESET EMAIL (DEV MODE)")
            print(f"To: {email}")
            print(f"Click here to reset: {reset_link}")
            print("UID:", uid)
            print("Token:", token)
            print("="*50 + "\n")
            
            return Response({"message": "Password reset email sent (check console).", "uid": uid, "token": token}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uid = serializer.validated_data['uid']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                user_id = force_str(urlsafe_base64_decode(uid))
                user = User.objects.get(pk=user_id)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                user = None

            if user is not None and default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
            else:
                 return Response({"error": "Invalid token or user ID"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ----------------- Quiz Assessment -----------------

class QuizAssessmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        # Expecting data like {"q1": 0, "q2": 1, ... "q20": 4}
        data = request.data
        
        # Validating inputs (basic check)
        question_keys = [f"q{i}" for i in range(1, 21)]
        clean_data = {}
        for key in question_keys:
            val = data.get(key)
            if val is None:
                 # Default to 0 if missing, or we could return 400
                 clean_data[key] = 0
            else:
                 try:
                     clean_data[key] = int(val)
                 except ValueError:
                     return Response({f"error": f"Invalid value for {key}"}, status=status.HTTP_400_BAD_REQUEST)

        # Call the service (Orchestration Pattern B)
        # This returns the full prediction dict
        prediction_result = predict_quiz(clean_data)
        
        # Save to DB
        try:
            # We need to explicitly pass keys when unpacking if they are not in the dict, 
            # but clean_data has them.
            # Convert list of advice to string if needed by model? 
            # Model definition for 'next_steps_advice'? 
            # Checked models.py: next_steps_advice IS NOT IN THE MODEL. 
            # The model has: user, q1..q20, predicted_stage, main_message, stage_description, doctor_type, consolation_message, created_at.
            # So next_steps_advice is purely transient in the view context/template.
            
            assessment = AssessmentResult.objects.create(
                user=request.user,
                **clean_data,
                predicted_stage=prediction_result['predicted_stage'],
                main_message=prediction_result['main_message'],
                stage_description=prediction_result['stage_description'],
                doctor_type=prediction_result['doctor_type'],
                consolation_message=prediction_result['consolation_message']
            )
            
            # Serialize the saved object to return it
            # We can also add the extra transient data (advice) to the response
            serializer = AssessmentResultSerializer(assessment)
            response_data = serializer.data
            response_data['next_steps_advice'] = prediction_result['next_steps_advice']
            
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ----------------- Spiral Assessment -----------------

class SpiralAssessmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        
        # We need to save the file first to check it/validate it properly via path? 
        # Or validate in memory? The existing validation logic uses cv2.imread(path).
        # So we MUST save it to disk first.
        
        # Option: Save to a temp location or use the model's save method first?
        # Let's use the model to save the file, then process.
        
        try:
            # Create object but don't commit result yet? 
            # Or just save file manually?
            # Model: SpiralAssessmentResult(user, result, uploaded_image)
            
            # We'll save it with a placeholder result first to get the path
            spiral_obj = SpiralAssessmentResult.objects.create(
                user=request.user,
                result="Processing...",
                uploaded_image=image_file
            )
            
            file_path = spiral_obj.uploaded_image.path
            
            # Validate
            if not is_valid_spiral_wrapper(file_path):
                spiral_obj.delete() # cleanup
                return Response({'error': 'Invalid spiral image'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Predict
            result = predict_spiral_wrapper(file_path)
            
            # Update DB
            spiral_obj.result = result
            spiral_obj.save()
            
            serializer = SpiralAssessmentResultSerializer(spiral_obj, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----------------- Voice Assessment -----------------

class VoiceAssessmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if 'audio' not in request.FILES:
            return Response({"error": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        audio_file = request.FILES['audio']
        
        try:
            # Save first
            voice_obj = SpeechAssessmentResult.objects.create(
                user=request.user,
                result="Processing...",
                uploaded_audio=audio_file
            )
            
            file_path = voice_obj.uploaded_audio.path
            
            # Predict
            result = predict_voice_wrapper(file_path)
            
            # Update DB
            voice_obj.result = result
            voice_obj.save()
            
            serializer = SpeechAssessmentResultSerializer(voice_obj, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ----------------- Brain MRI Assessment -----------------

class BrainAssessmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        image_file = request.FILES['image']
        
        try:
            brain_obj = BrainScanResult.objects.create(
                user=request.user,
                result="Processing...",
                image=image_file
            )
            
            file_path = brain_obj.image.path
            
            # Validate
            if not is_valid_mri_wrapper(file_path):
                brain_obj.delete()
                return Response({'error': 'Invalid MRI image'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Predict
            result = predict_brain_wrapper(file_path)
            
            # Update DB
            brain_obj.result = result
            brain_obj.save()
            
            serializer = BrainScanResultSerializer(brain_obj, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ----------------- End of API Views -----------------

class UnifiedHistoryAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UnifiedHistorySerializer

    def get_queryset(self):
        # This returns a list, not a queryset, so we override list() behavior or serializer input
        return [] # Placeholder, real logic in list()

    def list(self, request, *args, **kwargs):
        user = request.user
        
        # Fetch all
        quiz = AssessmentResult.objects.filter(user=user)
        spiral = SpiralAssessmentResult.objects.filter(user=user)
        speech = SpeechAssessmentResult.objects.filter(user=user)
        brain = BrainScanResult.objects.filter(user=user)
        history = AssessmentHistory.objects.filter(user=user)
        
        # Combine
        combined = list(chain(quiz, spiral, speech, brain, history))
        
        # Sort by date (descending)
        # Different fields: created_at vs date_taken
        combined.sort(
            key=lambda x: getattr(x, 'created_at', getattr(x, 'date_taken', None)), 
            reverse=True
        )
        
        serializer = self.get_serializer(combined, many=True)
        return Response(serializer.data)


class NearbySpecialistsView(APIView):
    """
    API View to fetch nearby specialists based on lat/lon.
    """
    permission_classes = [AllowAny] # Allow frontend to call generic location service easily

    def post(self, request):
        lat = request.data.get('lat')
        lon = request.data.get('lon')
        
        if not lat or not lon:
            return Response({"error": "Latitude and Longitude required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from detection_app.services.location_service import find_nearby_specialists
            specialists = find_nearby_specialists(lat, lon)
            return Response(specialists, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RiskScoreAPIView(APIView):
    """
    API View to calculate and return the consolidated risk score based on latest assessments.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .services.prediction_service import calculate_risk_score
        try:
            risk_data = calculate_risk_score(request.user)
            return Response(risk_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
