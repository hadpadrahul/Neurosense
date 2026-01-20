from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import json
from unittest.mock import patch, MagicMock

# Import services for logic parity checks

# Import services for logic parity checks
from detection_app.api.services.prediction_service import predict_quiz

class LegacySiteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_home_page_renders(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

class APIEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='apiuser', password='password')
        self.client.force_authenticate(user=self.user)
        
        self.quiz_url = reverse('api_quiz_assessment')
        self.history_url = reverse('api_history')

    def test_quiz_assessment(self):
        data = {f'q{i}': 1 for i in range(1, 21)}
        response = self.client.post(self.quiz_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('predicted_stage', response.data)

    def test_history_endpoint(self):
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)

class LogicParityTests(TestCase):
    @patch('detection_app.api.services.prediction_service.stage_model')
    @patch('detection_app.api.services.prediction_service.label_encoder')
    def test_quiz_logic_parity(self, mock_encoder, mock_model):
        mock_model.n_features_in_ = 20
        mock_model.predict.return_value = [1]
        mock_encoder.inverse_transform.return_value = ["Stage 1"]
        
        input_data = {f"q{i}": 0 for i in range(1, 21)}
        result = predict_quiz(input_data)
        
        self.assertEqual(result['predicted_stage'], "Stage 1")
        self.assertIn("Early Stage Symptoms", result['main_message'])


