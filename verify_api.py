
import requests
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

# We assume a test user exists or will be created by fixtures, but for smoke test
# we'll try to use 'webuser' / 'password'. If it fails, we report it.
USERNAME = "webuser"
PASSWORD = "password123"

def check(name, success_condition, details=""):
    status = "[OK]" if success_condition else "[FAIL]"
    print(f"{status} {name} {details}")
    return success_condition

def main():
    print(f"--- System Smoke Test ({BASE_URL}) ---")
    
    # 1. Server Connectivity
    try:
        r = requests.get(BASE_URL, timeout=2)
        if not check("Server Reachability", r.status_code == 200, f"({r.status_code})"):
            sys.exit(1)
    except Exception as e:
        check("Server Reachability", False, f"(Exception: {e})")
        sys.exit(1)

    # 2. Web Routes (Public)
    check("Web: Home", requests.get(f"{BASE_URL}/").status_code == 200)
    check("Web: Login", requests.get(f"{BASE_URL}/login/").status_code == 200)
    
    # 3. Web Routes (Protected - Should Redirect)
    r_quiz = requests.get(f"{BASE_URL}/quiz/", allow_redirects=False)
    check("Web: Quiz (Protected)", r_quiz.status_code == 302, f"(Got {r_quiz.status_code})")

    print("\n--- API Endpoints (DRF) ---")
    
    # 4. Auth (Get Token)
    token = None
    try:
        r_auth = requests.post(f"{API_BASE}/token/", json={"username": USERNAME, "password": PASSWORD})
        if r_auth.status_code == 200:
            token = r_auth.json().get("access")
            check("API: Obtain Token", True)
        else:
            check("API: Obtain Token", False, f"(Status: {r_auth.status_code} - User might not exist)")
    except Exception as e:
        check("API: Obtain Token", False, f"(Error: {e})")

    # 5. Protected API Access
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 5.1 History
        r_hist = requests.get(f"{API_BASE}/history/", headers=headers)
        check("API: Get History", r_hist.status_code == 200, f"(Status: {r_hist.status_code})")
        
        # 5.2 Quiz Prediction (Smoke)
        # We send a dummy payload just to see if it accepts it (201 or 400 validation, not 404/500)
        # Sending VALID payload to get 201
        payload = {f"q{i}": 0 for i in range(1, 21)}
        r_quiz = requests.post(f"{API_BASE}/assessments/quiz/", json=payload, headers=headers)
        check("API: Submit Quiz", r_quiz.status_code == 201, f"(Status: {r_quiz.status_code})")
        
    else:
        print("Skipping authenticated API tests due to missing token.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
