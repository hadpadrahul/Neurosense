from rest_framework import serializers
from detection_app.models import (
    AssessmentResult, 
    SpiralAssessmentResult, 
    SpeechAssessmentResult, 
    BrainScanResult,
    AssessmentHistory
)
from django.contrib.auth.models import User

# ----------------- User Serializers -----------------

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data['email']
        )
        return user

# ----------------- Profile & Password Serializers -----------------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # We verify if user exists, but for security, usually we don't return error if not found.
        # But for this internal tool request, checking existence helps.
        if not User.objects.filter(email=value).exists():
             raise serializers.ValidationError("User with this email not found.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()
# ----------------- Assessment Serializers -----------------

class AssessmentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentResult
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'predicted_stage', 'main_message', 'stage_description', 'doctor_type', 'consolation_message']

class SpiralAssessmentResultSerializer(serializers.ModelSerializer):
    uploaded_image = serializers.ImageField(use_url=True)
    
    class Meta:
        model = SpiralAssessmentResult
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'result']

class SpeechAssessmentResultSerializer(serializers.ModelSerializer):
    uploaded_audio = serializers.FileField(use_url=True)

    class Meta:
        model = SpeechAssessmentResult
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'result']

class BrainScanResultSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = BrainScanResult
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'result']

# ----------------- Unified History Serializer -----------------

class UnifiedHistorySerializer(serializers.Serializer):
    """
    Custom serializer to handle mixed types of assessment results for the history view.
    It standardizes the output format regardless of the source model.
    """
    id = serializers.IntegerField()
    type = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    def get_type(self, obj):
        if isinstance(obj, AssessmentResult):
            return "Quiz"
        elif isinstance(obj, SpiralAssessmentResult):
            return "Spiral"
        elif isinstance(obj, SpeechAssessmentResult):
            return "Voice"
        elif isinstance(obj, BrainScanResult):
            return "Brain MRI"
        elif isinstance(obj, AssessmentHistory):
            return obj.test_type
        return "Unknown"

    def get_date(self, obj):
        # Handle different field names for date
        dt = getattr(obj, 'created_at', getattr(obj, 'date_taken', None))
        return dt.isoformat() if dt else None

    def get_result(self, obj):
        # Handle different field names for the main result
        if isinstance(obj, AssessmentResult):
            return obj.predicted_stage
        return getattr(obj, 'result', 'N/A')

    def get_details(self, obj):
        # Provide extra context if available
        if isinstance(obj, AssessmentResult):
            return obj.main_message
        return None

    def get_file_url(self, obj):
        # Return URL to the uploaded file if applicable
        request = self.context.get('request')
        url = None
        if isinstance(obj, SpiralAssessmentResult) and obj.uploaded_image:
            url = obj.uploaded_image.url
        elif isinstance(obj, SpeechAssessmentResult) and obj.uploaded_audio:
            url = obj.uploaded_audio.url
        elif isinstance(obj, BrainScanResult) and obj.image:
            url = obj.image.url
            
        if request and url:
            return request.build_absolute_uri(url)
        return url

# ----------------- End of Serializers -----------------


