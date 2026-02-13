from django.urls import path
from .api_views import (
    QuizAssessmentAPIView,
    SpiralAssessmentAPIView,
    VoiceAssessmentAPIView,
    BrainAssessmentAPIView,
    UnifiedHistoryAPIView,
    RegisterAPIView,
    LogoutAPIView,
    ProfileAPIView,
    ChangePasswordAPIView,
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView,
    NearbySpecialistsView,
    RiskScoreAPIView,
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
    path('risk-score/', RiskScoreAPIView.as_view(), name='api_risk_score'),
    
    # Auth
    path('register/', RegisterAPIView.as_view(), name='api_register'),
    path('profile/', ProfileAPIView.as_view(), name='api_profile'),
    path('profile/password/', ChangePasswordAPIView.as_view(), name='api_change_password'),
    path('password-reset/', PasswordResetRequestAPIView.as_view(), name='api_password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmAPIView.as_view(), name='api_password_reset_confirm'),
    path('logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Location service
    path('nearby-specialists/', NearbySpecialistsView.as_view(), name='api_nearby_specialists'),
]
