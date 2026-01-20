
import os
import requests
import io
from PIL import Image
import numpy as np
import soundfile as sf
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"
USERNAME = "webuser"
PASSWORD = "password123"

def check(name, success, details=""):
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {name} {details}")
    return success

def create_dummy_image(filename="test_image.png", color=(100, 100, 100), size=(300, 300)):
    # Create a simple image that passes basic validation (not pure black/white)
    img = Image.new('RGB', size, color=color)
    # Add some "noise" or patterns so it's not uniform (for MRI validation)
    pixels = img.load()
    for i in range(size[0]):
        for j in range(size[1]):
            if (i+j) % 10 == 0:
                pixels[i,j] = (200, 200, 200)
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def create_dummy_audio(filename="test_audio.wav"):
    # Create 1 second of white noise
    samplerate = 22050
    data = np.random.uniform(-1, 1, samplerate)
    audio_byte_arr = io.BytesIO()
    sf.write(audio_byte_arr, data, samplerate, format='WAV')
    audio_byte_arr.seek(0)
    return audio_byte_arr

def main():
    print(f"--- Comprehensive Upload Verification ({BASE_URL}) ---")
    
    session = requests.Session()

    # 1. Login
    login_url = f"{BASE_URL}/login/"
    # Get CSRF token first
    r = session.get(login_url)
    csrftoken = session.cookies.get('csrftoken')
    
    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        'csrfmiddlewaretoken': csrftoken
    }
    
    r_login = session.post(login_url, data=login_data, headers={'Referer': login_url})
    if check("Login", r_login.url == f"{BASE_URL}/", f"(Final URL: {r_login.url})"):
        pass
    else:
        print("Login failed, aborting upload tests.")
        sys.exit(1)

    # 2. Upload Spiral
    print("\n--- Testing Spiral Upload ---")
    spiral_img = create_dummy_image()
    files = {'spiral_image': ('spiral_test.png', spiral_img, 'image/png')}
    # Get CSRF for this page
    r_spiral_page = session.get(f"{BASE_URL}/spiral-detection/")
    csrftoken = session.cookies.get('csrftoken')
    
    data = {'csrfmiddlewaretoken': csrftoken}
    r_spiral = session.post(f"{BASE_URL}/spiral-detection/", files=files, data=data, headers={'Referer': f"{BASE_URL}/spiral-detection/"})
    check("Spiral Upload", r_spiral.status_code == 200 or r_spiral.status_code == 302, f"(Status: {r_spiral.status_code})")
    
    # 3. Upload Brain MRI
    print("\n--- Testing Brain MRI Upload ---")
    brain_img = create_dummy_image(size=(256, 256), color=(50, 50, 50)) # Grayscale-ish
    files = {'brain_image': ('brain_test.jpg', brain_img, 'image/jpeg')}
    # Get CSRF
    r_brain_page = session.get(f"{BASE_URL}/brain-detection/")
    csrftoken = session.cookies.get('csrftoken')
    
    data = {'csrfmiddlewaretoken': csrftoken}
    r_brain = session.post(f"{BASE_URL}/brain-detection/", files=files, data=data, headers={'Referer': f"{BASE_URL}/brain-detection/"})
    if not check("Brain MRI Upload", "Prediction Result" in r_brain.text or "Parkinson Detected" in r_brain.text or "Normal" in r_brain.text, f"(Status: {r_brain.status_code})"):
        print(f"DEBUG Response Text Snippet: {r_brain.text[:300]}...")

    # 4. Upload Voice
    print("\n--- Testing Voice Upload ---")
    voice_file = create_dummy_audio()
    files = {'audio_file': ('voice_test.wav', voice_file, 'audio/wav')}
    # Get CSRF
    r_voice_page = session.get(f"{BASE_URL}/speech-upload/")
    csrftoken = session.cookies.get('csrftoken')

    data = {'csrfmiddlewaretoken': csrftoken}
    r_voice = session.post(f"{BASE_URL}/speech-upload/", files=files, data=data, headers={'Referer': f"{BASE_URL}/speech-upload/"})
    check("Voice Upload", r_voice.status_code == 200, f"(Status: {r_voice.status_code})")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
