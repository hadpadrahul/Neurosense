import requests
import os
import sys

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
                print(response.json())
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

def main():
    print("=== INTERACTIVE API TESTER ===")
    print("This script will help you verify the detection APIs.")
    print("Ensure server is running: python manage.py runserver")
    
    token = login()
    if not token:
        print("Aborting due to login failure.")
        return

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
    
    print_separator()
    print("Testing Complete.")

if __name__ == "__main__":
    main()
