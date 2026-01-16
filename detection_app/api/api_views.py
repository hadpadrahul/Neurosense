from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
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

from .serializers import (
    AssessmentResultSerializer,
    SpiralAssessmentResultSerializer,
    SpeechAssessmentResultSerializer,
    BrainScanResultSerializer,
    UnifiedHistorySerializer,
    EpilepsyAssessmentSerializer,
    AlzheimerMRIRequestSerializer,
    AlzheimerMRIResponseSerializer,
    AlzEmotionScoreRequestSerializer,
    AlzWordScoreRequestSerializer,
    AlzFluencyRequestSerializer,
    AlzSpeechRequestSerializer,
    AlzSummaryRequestSerializer
)
from .services.prediction_service import (
    predict_quiz, 
    predict_spiral_wrapper, 
    is_valid_spiral_wrapper,
    predict_voice_wrapper,
    predict_brain_wrapper,
    is_valid_mri_wrapper
)
from .services.epilepsy_service import assess_epilepsy_risk
from .services.alz_mri_service import predict_alz_mri
from .services.alz_interactive_service import (
    get_emotion_config, score_emotion_test,
    get_word_config, score_word_test,
    score_fluency, score_speech_coherence,
    get_aeri_summary
)

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

# ----------------- Epilepsy Assessment -----------------

class EpilepsyAssessmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request, *args, **kwargs):
        # Allow default false values, so input can be sparse
        serializer = EpilepsyAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Pass validated data to service (logic extracted from views.py)
        result = assess_epilepsy_risk(serializer.validated_data)
        
        # Return combined struct
        return Response(result, status=status.HTTP_200_OK)

# ----------------- Alzheimer MRI Assessment -----------------

class AlzMRIAssessmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        if 'image' not in request.FILES:
             return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
             
        uploaded_file = request.FILES['image']
        
        # We need to save the file to disk for the model to read it, 
        # mirroring the web view logic which saves to settings.MEDIA_ROOT/detection_uploads (or alz_mri_scans)
        
        # The service expects an absolute file path.
        # We'll use a temp save logic similar to the view's "debug" logic or standard file storage
        
        try:
            # Replicating the storage logic from detection_app/views.py (Definition 2)
            # "upload_dir = Path(settings.MEDIA_ROOT) / 'detection_uploads'"
            upload_dir = Path(settings.MEDIA_ROOT) / "detection_uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Use specific name pattern or keep original
            filename = f"api_alz_mri_{uploaded_file.name}"
            abs_path = str(upload_dir / filename)
            
            with open(abs_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            
            # Call service (verbatim logic wrapper)
            result = predict_alz_mri(abs_path)
            
            # Serialize response
            resp_serializer = AlzheimerMRIResponseSerializer(result)
            return Response(resp_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


# ----------------- Phase 4: Interactive Alz Views -----------------

class AlzEmotionConfigAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        config = get_emotion_config()
        return Response(config)

class AlzEmotionScoreAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        serializer = AlzEmotionScoreRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = score_emotion_test(serializer.validated_data['answers'])
        return Response(result)

class AlzWordConfigAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        config = get_word_config()
        return Response(config)

class AlzWordScoreAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = AlzWordScoreRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = score_word_test(serializer.validated_data['recalled_text'])
        return Response(result)

class AlzFluencyScoreAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = AlzFluencyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # category defaults to 'fruits' in serializer if missing
        result = score_fluency(
            serializer.validated_data['raw_text'], 
            serializer.validated_data.get('category', 'fruits')
        )
        return Response(result)

class AlzSpeechScoreAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = AlzSpeechRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = score_speech_coherence(serializer.validated_data['text'])
        return Response(result)

class AlzSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = AlzSummaryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = get_aeri_summary(
            data['speech_score'], 
            data['memory_score'], 
            data['fluency_score']
        )
        return Response(result)

