from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock

# Import services
from detection_app.api.services.alz_interactive_service import (
    score_emotion_test,
    score_word_test,
    score_fluency,
    score_speech_coherence,
    EMOTION_IMAGES
)

class AlzInteractiveAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='apiuser_alz', password='password')
        self.client.force_authenticate(user=self.user)
        self.base_url = '/api/v1/assessments/alzheimer'

    def test_emotion_flow(self):
        # 1. Config
        resp_config = self.client.get(f'{self.base_url}/emotion/config/')
        self.assertEqual(resp_config.status_code, 200)
        self.assertIn('images', resp_config.data)
        self.assertEqual(len(resp_config.data['images']), 5)
        
        # 2. Score
        # Pick correct answers manually from source of truth for test
        answers = []
        for img in EMOTION_IMAGES:
            answers.append({"image_id": img['id'], "selected_label": img['emotion']})
            
        resp_score = self.client.post(f'{self.base_url}/emotion/score/', {"answers": answers}, format='json')
        self.assertEqual(resp_score.status_code, 200)
        self.assertEqual(resp_score.data['correct_count'], 5)
        self.assertEqual(resp_score.data['score_percent'], 100.0)

    def test_word_flow(self):
        # 1. Config
        resp_config = self.client.get(f'{self.base_url}/word/config/')
        self.assertEqual(resp_config.status_code, 200)
        self.assertEqual(len(resp_config.data['words']), 10)
        
        # 2. Score
        # "mango train" -> 2 correct
        resp_score = self.client.post(f'{self.base_url}/word/score/', {"recalled_text": "mango train"}, format='json')
        self.assertEqual(resp_score.status_code, 200)
        self.assertEqual(resp_score.data['memory_score'], 2.0) # 2/10 * 10
        
    def test_fluency(self):
        # "apple banana" -> 2 unique
        resp = self.client.post(f'{self.base_url}/fluency/score/', {"raw_text": "apple banana apple"}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['unique_count'], 2)
        # Score computation: (2/15) * 10 = 1.33 -> 1.3
        self.assertEqual(resp.data['fluency_score'], 1.3)

    def test_speech(self):
        # High coherence text
        text = "I woke up in the morning, brushed my teeth, took a bath, and had breakfast before going to work."
        resp = self.client.post(f'{self.base_url}/speech/score/', {"text": text}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(resp.data['total_score'], 8.0)

    def test_summary(self):
        data = {
            "speech_score": 10.0,
            "memory_score": 10.0,
            "fluency_score": 10.0
        }
        resp = self.client.post(f'{self.base_url}/summary/', data, format='json')
        self.assertEqual(resp.status_code, 200)
        # 30+40+30 = 100
        self.assertEqual(resp.data['aeri_score'], 100.0)

class LogicParityTests(TestCase):
    """
    Verifies that the new services produce output consistent with expected logic 
    (mimicking legacy behavior, even if we can't easily import the legacy functions 
    because they are embedded in views).
    """

    def test_word_score_parity(self):
        # Legacy logic: clean, lower, split, dedupe.
        # Input: "MangO, Train   TRAIN"
        # Expected: mango, train -> 2.
        
        result = score_word_test("MangO, Train   TRAIN")
        self.assertEqual(len(result['correct_hits']), 2)
        self.assertIn('mango', result['correct_hits'])
        self.assertIn('train', result['correct_hits'])
        # Parity check: legacy view uses 'mango', 'train' etc default list. 
        
    def test_fluency_parity_dedupe(self):
        # Input: "apple, APPLE, banana"
        # Expected: apple, banana -> 2 unique.
        result = score_fluency("apple, APPLE, banana")
        self.assertEqual(result['unique_count'], 2)
        
    def test_speech_step_coverage(self):
        # Verify checking of "wake", "brush" etc.
        text = "I woke up."
        result = score_speech_coherence(text)
        # Woke matches step 1.
        self.assertGreater(result['breakdown']['step_coverage'], 0)
