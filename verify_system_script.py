import os
import sys
import django
import requests
import json

# Setup Django for standalone script usage (models, settings)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parkinson_detection_system.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient

def print_result(test_name, success, message=""):
    status = "PASS" if success else "FAIL"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"[{color}{status}{reset}] {test_name}: {message}")

def run_verification():
    print("--- Starting Automated System Verification ---")
    client = APIClient()
    
    # 1. Test Registration
    username = "verify_user_auto"
    password = "SafePassword123!"
    email = "verify@example.com"
    
    # Cleanup previous run
    User.objects.filter(username=username).delete()
    
    reg_data = {"username": username, "password": password, "email": email}
    response = client.post('/api/v1/register/', reg_data, format='json')
    print_result("Registration", response.status_code == 201, f"Status: {response.status_code}")

    # 2. Test Login (Get Token)
    login_data = {"username": username, "password": password}
    response = client.post('/api/v1/token/', login_data, format='json')
    if response.status_code == 200:
        token = response.data['access']
        print_result("Login", True, "Token received")
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    else:
        print_result("Login", False, f"Failed to get token. Status: {response.status_code}")
        return

    # 3. Test Profile
    response = client.get('/api/v1/profile/')
    print_result("Profile Fetch", response.status_code == 200, f"User: {response.data.get('username')}")

    # 4. Test Quiz API (Healthy)
    quiz_data = {f"q{i}": 0 for i in range(1, 21)}
    response = client.post('/api/v1/assessments/quiz/', quiz_data, format='json')
    print_result("Quiz API (Healthy)", response.status_code in [200, 201], f"Prediction: {response.data.get('predicted_stage')} - {response.data.get('main_message')}")

    # 5. Test Nearby Specialists
    location_data = {"lat": 19.9975, "lon": 73.7898} # Nashik
    response = client.post('/api/v1/nearby-specialists/', location_data, format='json')
    success = response.status_code == 200 and isinstance(response.data, list)
    print_result("Nearby Specialists API", success, f"Found {len(response.data) if success else 0} results")

    # 6. Test Model APIs (Mock/Dummy if files not present, but using client handles View logic)
    # We won't upload real large files here to keep it fast, but we check if endpoint is reachable
    # and handles bad input correctly (which verifies the View is active).
    
    # Voice (Empty)
    response = client.post('/api/v1/assessments/voice/', {}, format='multipart')
    print_result("Voice API Reachability", response.status_code == 400, "Correctly rejected empty request")

    # Spiral (Empty)
    response = client.post('/api/v1/assessments/spiral/', {}, format='multipart')
    print_result("Spiral API Reachability", response.status_code == 400, "Correctly rejected empty request")

    # Brain (Empty)
    response = client.post('/api/v1/assessments/brain/', {}, format='multipart')
    print_result("Brain API Reachability", response.status_code == 400, "Correctly rejected empty request")

    # 7. Test Privacy Policy Page (Web)
    response = client.get('/privacy-policy/')
    print_result("Privacy Policy Page", response.status_code == 200, "Page accessible")

    # 8. Test Risk Score API
    # Re-use the authenticated client from step 2
    response = client.get('/api/v1/risk-score/')
    success = response.status_code == 200
    risk_val = response.data.get('risk_percentage') if success else "N/A"
    print_result("Risk Score API", success, f"Initial Score: {risk_val}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    run_verification()
