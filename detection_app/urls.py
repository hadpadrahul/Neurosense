from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('quiz/', views.quiz, name='quiz'),  # Quiz form page
    path('results/', views.results, name='results'),  # (Optional) results with full symptom+analysis output
    path('quiz-result/', views.quiz_result, name='quiz_result'),  # Handles quiz + prediction logic
    path('thank-you/', views.thank_you, name='thank_you'),  # Thank you page after quiz

    # Authentication URLs
    path('register/', views.register_view, name='register'),  # Register
    path('login/', views.login_view, name='login'),  # Login
    path('logout/', views.logout_view, name='logout'),  # Logout
    path('profile/', views.profile_view, name='profile'), # User Profile

    # Password Reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    path('demo-video/', views.demo_video_view, name='demo_video'),  # Demo video

    # Spiral Detection URLs
    path('spiral-detection/', views.spiral_view, name='spiral_view'),
    path('spiral-result/', views.spiral_result, name='spiral_result'),

    # History & Progress Tracker URLs
    path('history/', views.history_view, name='history_view'),
    path('assessment-history/', views.history_view, name='assessment_history'),

    # Page to display the progress graph
    path('progress_tracker/', views.progress_tracker, name='progress_tracker'),
    # API endpoint to provide data for the progress graph
    path('progress_data/', views.quiz_progress_data, name='quiz_progress_data'),

    
    # Other Detection Views (Voice, Brain/Posture)
    path('speech-upload/', views.voice_upload, name='voice_upload'),
    path('result/<str:prediction>/', views.voice_result, name='voice_result'),
    path('brain-detection/', views.brain_view, name='brain_view'),




]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

