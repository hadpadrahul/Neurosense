# Parkinson's, Alzheimer's, and Epilepsy Detection System

A unified comprehensive healthcare platform for detecting early signs of Parkinson's Disease, Alzheimer's Disease, and Epilepsy using Machine Learning and interactive assessments.

## Documentation
- **[API Reference](API_REFERENCE.md)**: Full documentation of all REST API endpoints.
- **[Architecture & Migration](ARCHITECTURE_AND_MIGRATION.md)**: System design, service layer explanation, and migration details.
- **[Project Audit](PROJECT_AUDIT_AND_STATUS.md)**: Final redundancy check and implementation status.

---

## Features

### 1. Parkinson's Detection
- **Quiz Assessment**: 20-question survey using Random Forest.
- **Spiral Drawing Test**: Image-based detection using CNN.
- **Voice Analysis**: Audio feature analysis (Jitter, Shimmer, HNR).

### 2. Alzheimer's Detection
- **Brain MRI Analysis**: Deep Learning model for classifying MRI scans (Non-Demented, Very Mild, Mild, Moderate).
- **Interactive Tests**:
    - Emotion Memory Test
    - Word Memory Recall
    - Category Fluency
    - Speech Coherence Analysis (AERI Score)

### 3. Epilepsy Risk Assessment
- **Symptom Questionnaire**: 8-question risk evaluation algorithm.

## Technology Stack
- **Backend**: Django & Django REST Framework (DRF)
- **ML/AI**: TensorFlow, Keras, Scikit-learn, OpenCV, Librosa
- **Database**: SQLite (Default)
- **Authentication**: JWT (JSON Web Tokens)

---

## Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone <repo_url>
   cd parkinson_detection_system_final
   ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This project requires typical ML libraries (TensorFlow, OpenCV). Ensure you have necessary system libraries installed.*

4. **Apply Migrations**:
   ```bash
   python manage.py migrate
   ```

## Running the Application

### Start Development Server
```bash
python manage.py runserver
```
Access the web interface at `http://127.0.0.1:8000/`.

---

## API Documentation
The system provides a stateless REST API for integration with mobile apps or other clients.

**Base URL**: `/api/v1/`
See **[API_REFERENCE.md](API_REFERENCE.md)** for full details.

### Quick Start (Auth)
Obtain a JWT token to access protected endpoints.
- **POST** `/api/v1/token/`
  - Body: `{"username": "...", "password": "..."}`
  - Response: `access` (token), `refresh`

---

## Testing & Verification

### Run Automated Tests
The project includes a consolidated test suite covering both legacy views and new API services.
```bash
python manage.py test detection_app.tests
```

### Smoke Test (API)
A lightweight script is available to verify API health.
```bash
python verify_api.py
```
