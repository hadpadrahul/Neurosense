import requests
import json
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"
USERNAME = "testuser_api"
PASSWORD = "testpassword123"

def print_status(name, resp):
    status = resp.status_code
    icon = "[OK]" if 200 <= status < 300 else "[FAIL]"
    print(f"{icon} {name}: {status}")
    if status >= 400:
        print(f"   Error: {resp.text[:200]}")

def main():
    print(f"--- API Smoke Test ({BASE_URL}) ---")
    
    # 1. Auth / Token
    token = None
    try:
        resp = requests.post(f"{API_BASE}/token/", data={"username": USERNAME, "password": PASSWORD})
        if resp.status_code == 200:
            token = resp.json().get('access')
            print(f"[OK] Auth: Token obtained")
        else:
            print(f"[FAIL] Auth: Failed ({resp.status_code})")
            # Minimal fallback for testing public endpoints if strictly needed, but usually we stop here.
    except Exception as e:
        print(f"[FAIL] Connection Failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # 2. Endpoints Smoke Check
    endpoints = [
        ("History (GET)", f"{API_BASE}/history/", "GET", None),
        ("Quiz Config (GET)", f"{API_BASE}/assessments/quiz/", "GET", None), # Assuming GET not allowed on POST-only usually, but let's check. Wait, Quiz is POST only?
        # Let's check a known GET endpoint.
        # Alz Emotion Config is GET.
        ("Alz Emotion Config (GET)", f"{API_BASE}/assessments/alzheimer/emotion/config/", "GET", None),
    ]

    for name, url, method, data in endpoints:
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers)
            else:
                resp = requests.post(url, json=data, headers=headers)
            print_status(name, resp)
        except Exception as e:
            print(f"❌ {name}: Exception {e}")

    # 3. Simple POST Smoke (Quiz)
    try:
        data = {f"q{i}": 0 for i in range(1, 21)}
        resp = requests.post(f"{API_BASE}/assessments/quiz/", json=data, headers=headers)
        print_status("Quiz Prediction (POST)", resp)
    except Exception as e:
        print(f"[FAIL] Quiz Failure: {e}")

if __name__ == "__main__":
    main()
