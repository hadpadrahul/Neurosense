from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import json
from unittest.mock import patch, MagicMock

# Import services for logic parity checks
from detection_app.api.services.prediction_service import predict_quiz
from detection_app.api.services.epilepsy_service import assess_epilepsy_risk

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
        self.epilepsy_url = reverse('api_epilepsy_assessment')

    def test_quiz_assessment(self):
        data = {f'q{i}': 1 for i in range(1, 21)}
        response = self.client.post(self.quiz_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('predicted_stage', response.data)

    def test_epilepsy_assessment(self):
        # Test High Risk case
        data = {"q1": True, "q2": True, "q5": True, "q3": True} # Sum > 10
        response = self.client.post(self.epilepsy_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['score'], 10)
        self.assertIn("High", response.data['risk_level'])

        # Test Low Risk case
        data_low = {"q1": False, "q2": False} # Defaults to false for others
        response_low = self.client.post(self.epilepsy_url, data_low, format='json')
        self.assertEqual(response_low.status_code, status.HTTP_200_OK)
        self.assertLessEqual(response_low.data['score'], 4)

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

    def test_epilepsy_logic_parity(self):
        # 1. High Risk Logic Check
        # Weights: q1=3, q2=3, q3=2, q5=3 -> Total 11 (>10)
        data = {"q1": True, "q2": True, "q3": True, "q5": True}
        result = assess_epilepsy_risk(data)
        self.assertEqual(result['score'], 11)
        self.assertEqual(result['risk_level'], "High Epilepsy Risk – Recommend Specialist Referral")
        
        # 2. Moderate Risk Logic Check
        # Weights: q1=3, q3=2 -> Total 5 (<=10 and >4)
        data_mod = {"q1": True, "q3": True}
        result_mod = assess_epilepsy_risk(data_mod)
        self.assertEqual(result_mod['score'], 5)
        self.assertEqual(result_mod['risk_level'], "Moderate Epilepsy Risk")

