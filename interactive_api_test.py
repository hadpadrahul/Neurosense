import requests
import os
import sys
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_separator():
    print("-" * 50)

def login():
    print_separator()
    print("STEP 1: LOGIN")
    username = input("Enter Username: ").strip()
    password = input("Enter Password: ").strip()
    
    url = f"{BASE_URL}/token/"
    payload = {"username": username, "password": password}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens.get("access")
            print("[SUCCESS] Login successful!")
            print(f"Token obtained (starts with): {access_token[:15]}...")
            return access_token
        else:
            print(f"[FAIL] Login failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return None

def test_endpoint(token, endpoint_name, endpoint_url, file_param, file_ext):
    print_separator()
    print(f"STEP: TEST {endpoint_name.upper()}")
    
    while True:
        file_path = input(f"Enter path to a test {file_ext} file (or 'skip' to skip): ").strip()
        
        if file_path.lower() == 'skip':
            print("Skipping...")
            return

        # Handle quotes if user copies path as "C:\path\to\file"
        file_path = file_path.strip('"').strip("'")
        
        if not os.path.exists(file_path):
            print(f"[ERROR] File not found: {file_path}")
            continue
            
        try:
            headers = {"Authorization": f"Bearer {token}"}
            with open(file_path, 'rb') as f:
                files = {file_param: f}
                print(f"Sending request to {endpoint_url}...")
                response = requests.post(endpoint_url, headers=headers, files=files)
                
            if response.status_code in [200, 201]:
                print(f"[SUCCESS] {endpoint_name} Analysis Complete!")
                print("Response:")
                print(json.dumps(response.json(), indent=2))
                break
            else:
                print(f"[FAIL] API Error ({response.status_code}):")
                print(response.text)
                retry = input("Try again? (y/n): ").lower()
                if retry != 'y':
                    break
                    
        except Exception as e:
            print(f"[ERROR] Request failed: {e}")
            break

def test_get_endpoint(token, endpoint_name, endpoint_url):
    print_separator()
    print(f"TESTING: {endpoint_name}")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(endpoint_url, headers=headers)
        
        if response.status_code == 200:
            print(f"[SUCCESS] {endpoint_name} Retrieved!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"[FAIL] Error ({response.status_code}):")
            print(response.text)
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

def test_quiz(token, type="healthy"):
    print_separator()
    print(f"TESTING: Submit Quiz ({type.upper()})")
    
    # Generate dummy data
    if type == "healthy":
        # All 0s (Never)
        payload = {f"q{i}": 0 for i in range(1, 21)}
    else:
        # All 4s (Always)
        payload = {f"q{i}": 4 for i in range(1, 21)}
        
    url = f"{BASE_URL}/assessments/quiz/"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"[SUCCESS] Quiz Submitted!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"[FAIL] Error ({response.status_code}):")
            print(response.text)
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

def test_nearby_specialists(token):
    print_separator()
    print("TESTING: Nearby Specialists")
    # Coordinates for Nashik, India (as per user context)
    payload = {"lat": 19.9975, "lon": 73.7898} 
    print(f"Sending request for Nashik: {payload}")
    
    url = f"{BASE_URL}/nearby-specialists/"
    
    try:
        # Note: This endpoint is AllowAny, but we can send token anyway
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            print(f"[SUCCESS] Specialists Found!")
            data = response.json()
            print(f"Count: {len(data)}")
            if data:
                print("Top 3 results:")
                print(json.dumps(data[:3], indent=2))
        else:
            print(f"[FAIL] Error ({response.status_code}):")
            print(response.text)
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

def test_risk_score(token):
    print_separator()
    print("TESTING: Risk Score API")
    url = f"{BASE_URL}/risk-score/"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print(f"[SUCCESS] Risk Score Retrieved!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"[FAIL] Error ({response.status_code}):")
            print(response.text)
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

def run_model_tests(token):
    # Test Spiral
    test_endpoint(
        token, 
        "Spiral Drawing", 
        f"{BASE_URL}/assessments/spiral/", 
        "image", 
        ".png/.jpg"
    )

    # Test Voice
    test_endpoint(
        token, 
        "Voice Analysis", 
        f"{BASE_URL}/assessments/voice/", 
        "audio", 
        ".wav"
    )

    # Test Brain
    test_endpoint(
        token, 
        "Brain MRI", 
        f"{BASE_URL}/assessments/brain/", 
        "image", 
        ".jpg"
    )


def register_user():
    print_separator()
    print("TEST: REGISTER")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    email = input("Email: ").strip()
    
    url = f"{BASE_URL}/register/"
    try:
        response = requests.post(url, json={"username": username, "password": password, "email": email})
        print(f"Status: {response.status_code}")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

def view_profile(token):
    test_get_endpoint(token, "User Profile", f"{BASE_URL}/profile/")

def update_password(token):
    print("Feature not fully implemented in this script (requires old password). Skipping.")

def view_history(token):
    test_get_endpoint(token, "Assessment History", f"{BASE_URL}/history/")

def main():
    print("=== INTERACTIVE API TESTER ===")
    print("This script will help you verify the detection APIs.")
    print("Ensure server is running: python manage.py runserver")
    
    # Global token for the session
    token = None
    
    while True:
        print_separator()
        if token:
            print(f"Logged in. Token: {token[:10]}...")
        else:
            print("Not Logged In")
            
        print("=== MENU ===")
        print("1. Register User")
        print("2. Login")
        print("3. View Profile")
        print("4. Test Quiz API")
        print("5. Test Spiral API (Real Image)")
        print("6. Test Voice API (Real Audio)")
        print("7. Test Brain MRI API (Real Image)")
        print("8. View History")
        print("9. Test Nearby Specialists")
        print("10. Test Risk Score API")
        print("0. Exit")
        
        choice = input("Enter choice: ").strip()
        
        if choice == '0':
            print("Goodbye!")
            break
            
        if choice == '1':
            register_user()
            continue
            
        if choice == '2':
            t = login()
            if t:
                token = t
            continue
            
        if not token:
            print("[WARN] You must login first (Option 2).")
            continue
            
        if choice == '3':
            view_profile(token)
        elif choice == '4':
            type_q = input("Quiz Type (healthy/parkinson): ").strip().lower()
            if not type_q: type_q = "healthy"
            test_quiz(token, type_q)
        elif choice == '5':
            test_endpoint(token, "Spiral", f"{BASE_URL}/assessments/spiral/", "image", ".png/.jpg")
        elif choice == '6':
            test_endpoint(token, "Voice", f"{BASE_URL}/assessments/voice/", "audio", ".wav")
        elif choice == '7':
            test_endpoint(token, "Brain", f"{BASE_URL}/assessments/brain/", "image", ".jpg")
        elif choice == '8':
            view_history(token)
        elif choice == '9':
            test_nearby_specialists(token)
        elif choice == '10':
            test_risk_score(token)
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
