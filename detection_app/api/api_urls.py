from django.urls import path
from .api_views import (
    QuizAssessmentAPIView,
    SpiralAssessmentAPIView,
    VoiceAssessmentAPIView,
    BrainAssessmentAPIView,
    UnifiedHistoryAPIView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('assessments/quiz/', QuizAssessmentAPIView.as_view(), name='api_quiz_assessment'),
    path('assessments/spiral/', SpiralAssessmentAPIView.as_view(), name='api_spiral_assessment'),
    path('assessments/voice/', VoiceAssessmentAPIView.as_view(), name='api_voice_assessment'),
    path('assessments/brain/', BrainAssessmentAPIView.as_view(), name='api_brain_assessment'),
    
    path('history/', UnifiedHistoryAPIView.as_view(), name='api_history'),
    
    # Auth
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
