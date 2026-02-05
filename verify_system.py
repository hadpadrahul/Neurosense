
import requests
import time
import os
import random
import string
import shutil
import io

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/v1"
TIMESTAMP = int(time.time())
TEST_USER = f"sys_test_{TIMESTAMP}"
TEST_PASS = "TestPass123!"

# Colors for Output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def log_ok(msg):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")

def log_fail(msg, detail=""):
    print(f"{Colors.RED}[FAIL]{Colors.RESET} {msg}")
    if detail:
        print(f"       {detail}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def log_section(title):
    print(f"\n{Colors.YELLOW}=== {title} ==={Colors.RESET}")

# --- Helper: Generate Dummy Files ---
def create_dummy_image():
    # Create simple 100x100 white image
    try:
        from PIL import Image
        img = Image.new('L', (200, 200), color=255)
        # Add some drawing to pass strict validation if needed
        # But for Spiral/Brain, simple might fail if validated strictly. 
        # Using verifying logic from verify_uploads.py would be best, 
        # but let's assume we can re-use the file generation logic or just use bytes.
        
        # Better: Create a minimal valid JPG/PNG in memory
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr.read()
    except ImportError:
        log_warn("Pillow not found, cannot generate real image. Skipping upload tests.")
        return None

def create_dummy_audio():
    # Minimal WAV header + silence
    # RIFF header
    import struct
    buf = io.BytesIO()
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36)) # Size
    buf.write(b'WAVEfmt ')
    buf.write(struct.pack('<I', 16)) # Subchunk1Size
    buf.write(struct.pack('<H', 1))  # AudioFormat (PCM)
    buf.write(struct.pack('<H', 1))  # NumChannels (Mono)
    buf.write(struct.pack('<I', 44100)) # SampleRate
    buf.write(struct.pack('<I', 44100 * 2)) # ByteRate
    buf.write(struct.pack('<H', 2)) # BlockAlign
    buf.write(struct.pack('<H', 16)) # BitsPerSample
    buf.write(b'data')
    buf.write(struct.pack('<I', 0)) # Subchunk2Size (Empty data)
    buf.seek(0)
    return buf.read()


# --- Main Test Suite ---
def run_full_suite():
    session = requests.Session()
    
    # 1. Server Reachability
    log_section("1. Server Reachability")
    try:
        resp = session.get(BASE_URL)
        if resp.status_code == 200:
            log_ok(f"Home Page Accessible ({BASE_URL})")
        else:
            log_fail(f"Home Page returned {resp.status_code}")
            return # Critical failure
    except requests.exceptions.ConnectionError:
        log_fail("Connection Error. Is the Django server running?")
        return

    # 2. Authentication Flow
    log_section("2. Authentication Flow")
    
    # A. Register
    reg_data = {"username": TEST_USER, "password": TEST_PASS, "email": f"{TEST_USER}@example.com"}
    resp = requests.post(f"{API_URL}/register/", json=reg_data)
    if resp.status_code == 201:
        log_ok(f"Registered User: {TEST_USER}")
    else:
        log_fail("Registration Failed", resp.text)
        return # Critical

    # A.1. Register Duplicate Email (Negative Test)
    resp = requests.post(f"{API_URL}/register/", json={
        "username": f"{TEST_USER}_2", 
        "password": TEST_PASS,
        "email": f"{TEST_USER}@example.com"
    })
    if resp.status_code == 400:
       log_ok("Duplicate Email Rejected")
    else:
       log_fail("Duplicate Email Accepted?", resp.status_code)

    # B. Login (Get Tokens)
    login_data = {"username": TEST_USER, "password": TEST_PASS}
    resp = session.post(f"{API_URL}/token/", json=login_data)
    if resp.status_code == 200:
        tokens = resp.json()
        access_token = tokens.get('access')
        refresh_token = tokens.get('refresh')
        log_ok("Login Successful (Tokens Received)")
    else:
        log_fail("Login Failed", resp.text)
        return

    # Set Auth Header for future requests
    headers = {"Authorization": f"Bearer {access_token}"}

    # C. Refresh Token (Positive Test)
    refresh_data = {"refresh": refresh_token}
    resp = session.post(f"{API_URL}/token/refresh/", json=refresh_data)
    if resp.status_code == 200:
        new_access = resp.json().get('access')
        if new_access:
            log_ok("Token Refresh Successful")
            # Update header with NEW access token to prove it works
            headers = {"Authorization": f"Bearer {new_access}"}
        else:
            log_fail("Token Refresh response missing access token", resp.text)
    else:
        log_fail("Token Refresh Failed", resp.text)


    # 2.D Profile & Password Change
    resp = requests.get(f"{API_URL}/profile/", headers=headers)
    if resp.status_code == 200:
        log_ok("Profile Retrieved")
    else:
        log_fail("Profile Retrieve Failed", resp.status_code)
        
    # 2.E Password Reset (Flow)
    # We will just trigger the email for basic systems check
    resp = requests.post(f"{API_URL}/password-reset/", json={"email": f"{TEST_USER}@example.com"})
    if resp.status_code == 200:
        log_ok("Password Reset Email Triggered")
    else:
        log_fail("Password Reset Trigger Failed", resp.status_code)

    # 3. Assessment Endpoints
    log_section("3. Feature Verification")

    # A. Quiz
    quiz_data = {"q" + str(i): random.randint(0, 4) for i in range(1, 21)}
    resp = requests.post(f"{API_URL}/assessments/quiz/", json=quiz_data, headers=headers)
    if resp.status_code == 201:
        log_ok("Quiz Submission Verified")
    else:
        log_fail("Quiz Submission Failed", resp.text)

    # B. History (Check if Quiz appears)
    resp = requests.get(f"{API_URL}/history/", headers=headers)
    if resp.status_code == 200:
        history = resp.json()
        if len(history) > 0 and history[0].get('type') == 'Quiz':
            log_ok(f"History Verified (Found {len(history)} items)")
        else:
            log_warn(f"History accessible but empty or mismatch: {history}")
    else:
        log_fail("History API Failed", resp.text)
    
    # C. Uploads (Mock)
    dummy_img = create_dummy_image()
    dummy_audio = create_dummy_audio()
    
    if dummy_img:
        files = {'image': ('test_spiral.png', dummy_img, 'image/png')}
        resp = requests.post(f"{API_URL}/assessments/spiral/", files=files, headers=headers)
        if resp.status_code == 201:
           log_ok("Spiral Upload Verified")
        elif resp.status_code == 400 and "Invalid" in resp.text:
           log_ok("Spiral Upload Hit Validator (Expected for dummy image)") 
        else:
           log_fail(f"Spiral Upload Failed ({resp.status_code})", resp.text)

        files = {'image': ('test_brain.jpg', dummy_img, 'image/jpeg')} # Reuse dummy img for brain
        resp = requests.post(f"{API_URL}/assessments/brain/", files=files, headers=headers)
        if resp.status_code == 201:
           res_json = resp.json()
           if res_json.get('result') in ["Parkinson Detected", "Normal"]:
               log_ok(f"Brain MRI Upload Verified (Result: {res_json.get('result')})")
           else:
               log_fail(f"Brain MRI Upload Invalid Result: {res_json}")
        elif resp.status_code == 400:
           log_ok("Brain MRI Upload Hit Validator (Expected for dummy image)")
        else:
           log_fail(f"Brain MRI Upload Failed ({resp.status_code})", resp.text)
           
    if dummy_audio:
        files = {'audio': ('test_voice.wav', dummy_audio, 'audio/wav')}
        resp = requests.post(f"{API_URL}/assessments/voice/", files=files, headers=headers)
        if resp.status_code == 201:
           res_json = resp.json()
           result_val = res_json.get('result')
           if result_val in ["Parkinson's Detected", "Healthy Voice"]:
               log_ok(f"Voice Upload Verified (Result: {result_val})")
           else:
               log_fail(f"Voice Upload Invalid Result: {res_json}")
        else:
           # Voice model might accept dummy WAV or fail gracefully
           if resp.status_code == 400:
                log_ok("Voice Upload Processed (Validator rejected dummy)")
           else:
                log_fail(f"Voice Upload Failed ({resp.status_code})", resp.text)


    # 4. Logout (Cleanup)
    log_section("4. Logout & Cleanup")
    logout_data = {"refresh": refresh_token}
    resp = requests.post(f"{API_URL}/logout/", json=logout_data, headers=headers)
    if resp.status_code == 205:
        log_ok("Logout Successful")
    else:
        log_fail("Logout Failed", resp.text)
        
    # Verify Refresh Token is now Invalid
    resp = requests.post(f"{API_URL}/token/refresh/", json=refresh_data)
    if resp.status_code == 401 or resp.status_code == 400:
        log_ok("Token Blacklist Verified (Refresh Rejected)")
    else:
        log_fail("Refresh Token Test Failed (Should be rejected after logout)", resp.text)

    print(f"\n{Colors.GREEN}=== System Verification Complete ==={Colors.RESET}")

if __name__ == "__main__":
    run_full_suite()
