# Neurosense: Parkinson's Detection System
**Version:** 2.1 (Stable) | **Architecture:** Hybrid Monolithic (Web + API)

Neurosense is a comprehensive multi-modal assessment system designed to detect early signs of Parkinson's Disease. It leverages machine learning to analyze user inputs across four distinct diagnostic modalities, accessible via both a traditional Web Interface and a robust REST API.

## Documentation
- **[API Reference](API_REFERENCE.md)**: Complete guide to REST API endpoints (Auth, Assessment, History).

---

## Key Features

### 1. Dual-Mode Accessibility
*   **Web App:** User-friendly browser interface with real-time feedback and visualizations.
*   **REST API:** Fully documented endpoints for mobile/external integrations, secured with JWT Authentication.

### 2. Diagnostic Modules
| Module | Method | Model | Input |
| :--- | :--- | :--- | :--- |
| **Early Screening Quiz** | Self-report survey (20 questions) | Random Forest | JSON / Form Data |
| **Spiral Analysis** | Handwriting tremor detection | VGG16 CNN | Image (.png/.jpg) |
| **Voice Analysis** | Acoustic feature extraction (MFCC) | Random Forest | Audio (.wav) |
| **Brain MRI Scan** | Deep Learning structural analysis | Custom CNN | MRI Scan (.jpg) |

### 3. Secure & Robust
*   **Authentication:** JWT-based stateless auth for API; Session-based for Web.
*   **User Management:** Email registration, Profile management, and Forgot Password flow.
*   **Validation:** Strict input validation strategies (Image contrast/ratio, Audio format).
*   **Safety:** Exception handling ensures server stability even with malformed inputs.
*   **Geolocation Map:** Integrated Leaflet.js map to find nearby specialists (Neurologists/Hospitals) within a 15km radius, with a default 3-5km visual zoom for immediate relevance.

---

## Installation & Setup

### Prerequisites
*   Python 3.10+
*   Python 3.12 (recommended)
*   pip
*   **FFmpeg** (Recommended for robust audio processing):
    *   Download from [ffmpeg.org](https://ffmpeg.org/download.html)
    *   Add `bin` folder to System PATH.

### 1. Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd parkinson_detection_system

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
# Apply migrations (including token blacklist)
python manage.py migrate
```

### 4. Run the Server
```bash
python manage.py runserver
```
*   **Web App:** `http://127.0.0.1:8000/`
*   **API Base:** `http://127.0.0.1:8000/api/v1/`

---

## Verification & Health Checks

We provide a unified system verification suite to ensure all components (Server, Auth, ML Models, File Handling) are functioning correctly.

### Run System Check
```bash
python verify_system_script.py
```
**What this tests:**
1.  **Server Reachability:** Confirms Django is up.
2.  **Auth Cycle:** Registers a test user -> Logins -> Refreshes Token -> Logs out -> Confirms Blacklist.
3.  **Feature Test:** Submits dummy data to Quiz, Spiral, Voice, and Brain endpoints to verify the full inference pipeline.

### Run Frontend Tests
To verify the Website integration (Views, Protected Pages, Auth Redirects):
```bash
python manage.py test tests.test_website
```

## Verification
To verify the entire system (including new Privacy Policy and Risk Score API), run:
```bash
python verify_system_script.py
```
This script acts as a comprehensive integration test.

## Interactive Testing
For manual testing of APIs:
```bash
python interactive_api_test.py
```
Menu options include:
- Register/Login
- Test Quiz, Spiral, Voice, Brain APIs
- View History & Profile
- **Test Nearby Specialists**
- **Test Risk Score API**

*   Helper utility to login, retrieve tokens, and upload your local files to verify Spiral, Voice, and Brain models interactively.

---

## Project Structure

```
parkinson_detection_system/
├── detection_app/              # Main Application Core
│   ├── api/                    # REST API Layer
│   │   ├── services/           # Business Logic (Unified Service Layer)
│   │   ├── serializers.py      # Data Serialization
│   │   └── api_views.py        # API Endpoints
│   ├── models/                 # Database Models
│   ├── templates/              # Django HTML Templates (Web UI)
│   ├── views.py                # Web Logic
│   └── ...
├── tests/                      # Consolidated Website Tests
├── media/                      # User Uploads (Git-ignored)
├── parkinson_detection_system/ # Project Settings
├── verify_system_script.py     # Master Verification Script
├── interactive_api_test.py     # Interactive Manual Testing Tool
├── manage.py                   # Django CLI
├── requirements.txt            # Pinned Dependencies
└── API_REFERENCE.md            # API Documentation
```

---

## Architecture
The system employs a **Service-Oriented Logic** pattern within a Modular Monolith. 
*   **Web Views** and **API Views** act as interface layers.
*   Both consume the same **Unified Service Layer** (`detection_app/api/services/prediction_service.py`), ensuring that business logic and ML predictions are identical regardless of the access method.

---

## Security
*   **Token Blacklisting:** Logout invalidates refresh tokens server-side.
*   **Input Sanitization:** All file uploads are validated before processing.
*   **Media Isolation:** User files are stored in a dedicated `media/` directory.
