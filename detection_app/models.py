# detection_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')], null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class AssessmentResult(models.Model):
    """
    Stores the results of the MCQ quiz assessment, including individual answers
    and the final prediction details.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Store all 20 quiz answers as IntegerFields (0-4 based on ordinal mapping)
    q1 = models.IntegerField()
    q2 = models.IntegerField()
    q3 = models.IntegerField()
    q4 = models.IntegerField()
    q5 = models.IntegerField()
    q6 = models.IntegerField()
    q7 = models.IntegerField()
    q8 = models.IntegerField()
    q9 = models.IntegerField()
    q10 = models.IntegerField()
    q11 = models.IntegerField()
    q12 = models.IntegerField()
    q13 = models.IntegerField()
    q14 = models.IntegerField()
    q15 = models.IntegerField()
    q16 = models.IntegerField()
    q17 = models.IntegerField()
    q18 = models.IntegerField()
    q19 = models.IntegerField()
    q20 = models.IntegerField()

    # Prediction output details
    predicted_stage = models.CharField(max_length=50) # e.g., "No Parkinsons", "Stage 1", "Stage 5"
    main_message = models.TextField()
    stage_description = models.TextField()
    doctor_type = models.CharField(max_length=100)
    consolation_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Timestamp for when the assessment was taken
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Quiz - {self.predicted_stage} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['created_at'] # Default ordering for easier progress tracking


class AssessmentHistory(models.Model):
    """
    Generic history model for other types of assessments if you want to track them
    without specific fields like quiz answers.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    result = models.CharField(max_length=200) # Generic result string
    date_taken = models.DateTimeField(auto_now_add=True)
    test_type = models.CharField(max_length=50) # e.g., 'Quiz', 'Spiral', 'Speech', 'Posture'

    def __str__(self):
        return f"{self.user.username} - {self.test_type} ({self.date_taken.strftime('%Y-%m-%d')})"

    class Meta:
        ordering = ['date_taken'] # Default ordering for easier history viewing


class SpiralAssessmentResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    result = models.CharField(max_length=255)
    
    # ✅ This must be an ImageField
    uploaded_image = models.ImageField(upload_to='spirals/')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.result} - {self.created_at.date()}"
    # models.py
from django.utils import timezone

class SpeechAssessmentResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    result = models.CharField(max_length=255)
    uploaded_audio = models.FileField(upload_to='speech_uploads/')
    created_at = models.DateTimeField(default=timezone.now)  # ✅ Add this line

    def __str__(self):
        return f"{self.user.username} - {self.result}"

    

from django.db import models
from django.contrib.auth.models import User

class BrainScanResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    result = models.CharField(max_length=100)
    image = models.ImageField(upload_to='brain_scans/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.result} ({self.created_at.strftime("%Y-%m-%d")})'
