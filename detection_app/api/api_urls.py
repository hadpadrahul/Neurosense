from django.urls import path
from .api_views import (
    QuizAssessmentAPIView,
    SpiralAssessmentAPIView,
    VoiceAssessmentAPIView,
    BrainAssessmentAPIView,
    UnifiedHistoryAPIView,
    EpilepsyAssessmentAPIView,
    AlzMRIAssessmentAPIView,
    AlzEmotionConfigAPIView, AlzEmotionScoreAPIView,
    AlzWordConfigAPIView, AlzWordScoreAPIView,
    AlzFluencyScoreAPIView, AlzSpeechScoreAPIView,
    AlzSummaryAPIView
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
    
    # New endpoints
    path('assessments/epilepsy/', EpilepsyAssessmentAPIView.as_view(), name='api_epilepsy_assessment'),
    path('assessments/alzheimer/mri/', AlzMRIAssessmentAPIView.as_view(), name='api_alz_mri_assessment'),
    
    # Phase 4: Interactive Alz Endpoints
    path('assessments/alzheimer/emotion/config/', AlzEmotionConfigAPIView.as_view(), name='api_alz_emotion_config'),
    path('assessments/alzheimer/emotion/score/', AlzEmotionScoreAPIView.as_view(), name='api_alz_emotion_score'),
    path('assessments/alzheimer/word/config/', AlzWordConfigAPIView.as_view(), name='api_alz_word_config'),
    path('assessments/alzheimer/word/score/', AlzWordScoreAPIView.as_view(), name='api_alz_word_score'),
    path('assessments/alzheimer/fluency/score/', AlzFluencyScoreAPIView.as_view(), name='api_alz_fluency_score'),
    path('assessments/alzheimer/speech/score/', AlzSpeechScoreAPIView.as_view(), name='api_alz_speech_score'),
    path('assessments/alzheimer/summary/', AlzSummaryAPIView.as_view(), name='api_alz_summary'),
    
    path('history/', UnifiedHistoryAPIView.as_view(), name='api_history'),
    
    # Auth
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
