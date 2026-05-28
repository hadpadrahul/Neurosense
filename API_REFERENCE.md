# API & Route Reference
**Application:** Neurosense (Parkinson's Detection)
**Base URL:** `http://127.0.0.1:8000`

---

## Part 1: Web Interface Routes (Django Templates)
These routes render HTML pages for browser usage.

### Authentication
| Method | URL | Description |
|:---|:---|:---|
| `GET/POST` | `/login/` | User Login Page |
| `GET/POST` | `/register/` | User Registration Page |
| `GET` | `/logout/` | Logs out the user |

### Assessments
| Method | URL | Description |
|:---|:---|:---|
| `GET` | `/` | Home Dashboard |
| `GET` | `/quiz/` | Quiz Form |
| `POST` | `/upload-assessment/` | Handles Quiz Submission |
| `GET/POST` | `/spiral-detection/` | Spiral Upload & Analysis |
| `GET/POST` | `/speech-upload/` | Voice Upload & Analysis |
| `GET/POST` | `/brain-detection/` | MRI Upload & Analysis |

---

## Part 2: REST API Endpoints (DRF)
**Base Path:** `/api/v1/`
**Authentication:** JWT Bearer Token (header `Authorization: Bearer <token>`)

### Authentication

#### 1. Register
*   **URL:** `/api/v1/register/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "username": "newuser",
        "password": "password123",
        "email": "user@example.com"
    }
    ```
*   **Response (201 Created):**
    ```json
    {
        "user": {"id": 1, "username": "newuser", "email": "user@example.com"},
        "message": "User created successfully..."
    }
    ```

#### 2. Obtain Token (Login)
*   **URL:** `/api/v1/token/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "username": "testuser",
        "password": "password123"
    }
    ```
*   **Response:**
    ```json
    {
        "refresh": "ey...",
        "access": "ey..."
    }
    ```

#### 3. Refresh Token
*   **URL:** `/api/v1/token/refresh/`
*   **Method:** `POST`
*   **Body:** `{"refresh": "ey..."}`
*   **Response:** `{"access": "ey_new..."}`

#### 4. User Profile
*   **URL:** `/api/v1/profile/`
*   **Method:** `GET`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response:**
    ```json
    {"username": "testuser", "email": "test@example.com"}
    ```

#### 5. Change Password
*   **URL:** `/api/v1/profile/password/`
*   **Method:** `PUT` / `PATCH`
*   **Headers:** `Authorization: Bearer <token>`
*   **Body:**
    ```json
    {
        "old_password": "current_pass",
        "new_password": "new_pass",
        "confirm_password": "new_pass"
    }
    ```

#### 6. Forgot Password (Request)
*   **URL:** `/api/v1/password-reset/`
*   **Method:** `POST`
*   **Body:** `{"email": "user@example.com"}`
*   **Response:** `{"message": "Password reset email sent...", "uid": "...", "token": "..."}`
    *(Note: In production, uid/token are sent via email only)*

#### 7. Forgot Password (Confirm)
*   **URL:** `/api/v1/password-reset-confirm/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "uid": "...",
        "token": "...",
        "new_password": "new_secure_pass"
    }
    ```

#### 8. Logout
*   **URL:** `/api/v1/logout/`
*   **Method:** `POST`
*   **Headers:** `Authorization: Bearer <token>`
*   **Body:** `{"refresh": "ey..."}`
    *(Invalidates the refresh token server-side)*


---

### Assessments

#### 1. Submit Quiz
*   **URL:** `/api/v1/assessments/quiz/`
*   **Method:** `POST`
*   **Headers:** `Authorization: Bearer <token>`
*   **Body:**
    ```json
    {
        "q1": 0, "q2": 1, "q3": 0, ..., "q20": 4
    }
    ```
*   **Response (201 Created):**
    ```json
    {
        "predicted_stage": "Stage 1",
        "main_message": "Preliminary Indication...",
        "next_steps_advice": ["See a neurologist..."]
    }
    ```

#### 2. Spiral Analysis
*   **URL:** `/api/v1/assessments/spiral/`
*   **Method:** `POST`
*   **Headers:** `Authorization: Bearer <token>`
*   **Content-Type:** `multipart/form-data`
*   **Body:**
    *   `image`: (File Binary .png/.jpg)
*   **Response:**
    ```json
    {
        "result": "Parkinson Detected",
        "uploaded_image": "/media/spirals/test.png"
    }
    ```

#### 3. Voice Analysis
*   **URL:** `/api/v1/assessments/voice/`
*   **Method:** `POST`
*   **Headers:** `Authorization: Bearer <token>`
*   **Content-Type:** `multipart/form-data`
*   **Body:**
    *   `audio`: (File Binary .wav)
*   **Response:**
    ```json
    {
        "result": "Healthy Voice",
        "uploaded_audio": "/media/speech_uploads/test.wav"
    }
    ```

#### 4. Brain MRI Analysis
*   **URL:** `/api/v1/assessments/brain/`
*   **Method:** `POST`
*   **Headers:** `Authorization: Bearer <token>`
*   **Content-Type:** `multipart/form-data`
*   **Body:**
    *   `image`: (File Binary .jpg)
*   **Response:**
    ```json
    {
        "result": "Normal",
        "image": "/media/brain_scans/scan.jpg"
    }
    ```

---

### History
#### Get User History
*   **URL:** `/api/v1/history/`
*   **Method:** `GET`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response:**
    ```json
    [
        {
            "id": 1,
            "type": "Quiz",
            "date": "2026-01-17T10:00:00Z",
            "result": "Stage 1"
        },
        {
            "id": 2,
            "type": "Spiral",
            "date": "2026-01-17T10:05:00Z",
            "result": "Parkinson Detected",
            "file_url": "http://.../media/spirals/..."
        }
    ]
    ```

---


---

### 6.1 Get Risk Score
**Endpoint:** `GET /api/v1/risk-score/`
**Auth Required:** Yes (JWT)

**Response:**
```json
{
    "risk_percentage": 45.0,
    "message": "Risk score based on latest assessments.",
    "components": {
        "quiz": {"score": 20, "available": true},
        "spiral": {"score": 100, "available": true},
        "voice": {"score": 0, "available": true},
        "brain": {"score": 0, "available": false}
    }
}
```
**Notes:** 
- Calculates weighted average of latest results.
- `risk_percentage` is between 0 and 100.
- `components` breakdown showing individual test scores (0-100) and availability.

---

### Nearby Specialists (Maps Feature)
This feature allows the frontend to display a map of nearby neurologists and healthcare facilities.

#### Usage Context
**Frontend Note:** This endpoint should be triggered **automatically** when any assessment (Quiz, Spiral, Voice, Brain) returns a positive result (e.g., "Parkinson Detected", "Stage 1-5"). It provides immediate, actionable "Next Steps" for the user.

#### Find Specialists
*   **URL:** `/api/v1/nearby-specialists/`
*   **Method:** `POST`
*   **Permissions:** `AllowAny` (No token required)
*   **Headers:** `Content-Type: application/json`
*   **Body:**
    ```json
    {
        "lat": 19.9975,   // User's Latitude (Float)
        "lon": 73.7898    // User's Longitude (Float)
    }
    ```
*   **Response (200 OK):**
    Returns a list of location objects.
    ```json
    [
        {
            "name": "City Care Hospital",
            "lat": 19.9980,
            "lon": 73.7900,
            "type": "hospital",
            "distance_km": 0.5,
            "address": "Mahatma Gandhi Road, Nashik"
        },
        {
            "name": "Dr. Sharma Neurology Clinic",
            "lat": 19.9960,
            "lon": 73.7850,
            "type": "clinic",
            "distance_km": 1.2,
            "address": "College Road, Nashik"
        }
    ]
    ```
*   **Error Responses:**
    *   `400 Bad Request`: If `lat` or `lon` are missing.
    *   `500 Internal Server Error`: If the specific location service (Overpass API) fails.
