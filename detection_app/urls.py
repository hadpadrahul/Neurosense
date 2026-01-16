from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('quiz/', views.quiz, name='quiz'),  # Quiz form page
    path('results/', views.results, name='results'),  # (Optional) results with full symptom+analysis output
    path('upload-assessment/', views.upload_assessment, name='upload_assessment'),  # Handles quiz + prediction logic
    path('thank-you/', views.thank_you, name='thank_you'),  # Thank you page after quiz

    # Authentication URLs
    path('register/', views.register_view, name='register'),  # Register
    path('login/', views.login_view, name='login'),  # Login
    path('logout/', views.logout_view, name='logout'),  # Logout

    path('demo-video/', views.demo_video_view, name='demo_video'),  # Demo video

    # Spiral Detection URLs
    path('spiral-detection/', views.spiral_detection_view, name='spiral_detection_view'),
    path('spiral-upload/', views.spiral_upload_view, name='spiral_upload_view'),
    path('spiral-result/', views.spiral_result, name='spiral_result'),


    # History & Progress Tracker URLs
    # Consolidated history view for all assessment types
    path('history/', views.history_view, name='history_view'),
    path('assessment-history/', views.history_view, name='assessment_history'),  # ✅ ADD THIS

    # Page to display the progress graph
    path('progress_tracker/', views.progress_tracker, name='progress_tracker'),
    # API endpoint to provide data for the progress graph
    path('progress_data/', views.quiz_progress_data, name='quiz_progress_data'),

    # Other Detection Views (Voice, Brain/Posture)
    path('speech-upload/', views.voice_upload, name='voice_upload'),
    path('result/<str:prediction>/', views.voice_result, name='voice_result'),
    path('brain-upload/', views.brain_upload_view, name='brain_upload'),
    path('brain-detection/', views.brain_detection_view, name='brain_detection_view'),
    path('assessment-options/', views.assessment_options, name='assessment_options'),
    # Alzheimer Emotion Memory Test
    path('alz/emotion/start/', views.emotion_memory_start, name='emotion_memory_start'),
    path('alz/emotion/recall/', views.emotion_memory_recall, name='emotion_memory_recall'),
    # Alzheimer – Speech Coherence Test
path('alz/speech-coherence/', views.speech_coherence_test, name='speech_coherence_test'),

    # Alzheimer’s module
    path('alz/', views.alz_home, name='alz_home'),
    path('alz/word-memory/show/', views.word_memory_show, name='word_memory_show'),
    path('alz/word-memory/recall/', views.word_memory_recall, name='word_memory_recall'),
    path("alz/mri-scan/", views.alz_mri_scan, name="alz_mri_scan"),
    path('alz/summary/', views.alz_summary, name='alz_summary'),

    path('assessment/', views.assessment_home, name='assessment_home'),
    path('assessment/options/', views.assessment_options, name='assessment_options'),
    path('epilepsy/', views.epilepsy_home, name='epilepsy_home'),



]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

