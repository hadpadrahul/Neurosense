# API Reference

**Base URL**: `/api/v1/`
**Authentication**: JWT (Bearer Token) required for all endpoints except where noted.

---

## Authentication

### Obtain Token
**POST** `/token/`
Get access and refresh tokens.
- **Body**:
  ```json
  {
      "username": "your_username",
      "password": "your_password"
  }
  ```
- **Response**:
  ```json
  {
      "access": "eyJ0eX...",
      "refresh": "eyJ0eX..."
  }
  ```

### Refresh Token
**POST** `/token/refresh/`
Get a new access token using a refresh token.
- **Body**:
  ```json
  {
      "refresh": "your_refresh_token"
  }
  ```

---

## Parkinson's Assessments

### Quiz Assessment
**POST** `/assessments/quiz/`
Predict Parkinson's stage based on 20 questions.
- **Body**:
  ```json
  {
      "q1": 0, "q2": 1, ..., "q20": 0
  }
  ```
- **Response**:
  ```json
  {
      "prediction": "Stage 1",
      "confidence": 0.85
  }
  ```

### Spiral Assessment
**POST** `/assessments/spiral/`
Predict Parkinson's from a spiral drawing image.
- **Body (Multipart)**:
  - `image`: File (jpg, png)
- **Response**:
  ```json
  {
      "prediction": "Healthy",
      "confidence": 0.92
  }
  ```

### Voice Assessment
**POST** `/assessments/voice/`
Predict Parkinson's from a voice recording.
- **Body (Multipart)**:
  - `audio`: File (wav, mp3)
- **Response**:
  ```json
  {
      "prediction": "Parkinson's Detected",
      "confidence": 0.78
  }
  ```

### Brain MRI Assessment
**POST** `/assessments/brain/`
Predict Parkinson's from a brain MRI scan.
- **Body (Multipart)**:
  - `image`: File (jpg, png)
- **Response**:
  ```json
  {
      "prediction": "Abnormal",
      "confidence": 0.88
  }
  ```

---

## Epilepsy Assessment

### Risk Assessment
**POST** `/assessments/epilepsy/`
Evaluate epilepsy risk based on symptoms. **Stateless**.
- **Body**:
  ```json
  {
      "q1": true,
      "q2": false,
      "q3": true,
      "q4": false,
      "q5": false,
      "q6": false,
      "q7": false,
      "q8": false
  }
  ```
- **Response**:
  ```json
  {
      "score": 25,
      "risk_level": "Moderate Risk",
      "advice": "Consult a neurologist..."
  }
  ```

---

## Alzheimer's Assessments

### Brain MRI Analysis
**POST** `/assessments/alzheimer/mri/`
Classify Alzheimer's stage from MRI.
- **Body (Multipart)**:
  - `image`: File (jpg, png)
- **Response**:
  ```json
  {
      "prediction_label": "Very Mild Demented",
      "confidence": 95.5,
      "prediction_pretty": "Very Mild Demented (95.5%)"
  }
  ```

### Emotion Memory Test
**GET** `/assessments/alzheimer/emotion/config/`
Get list of images for the test.
- **Response**:
  ```json
  {
      "images": [
          {"id": "img1", "url": "/static/dataset/emotion/1.jpg"},
          ...
      ]
  }
  ```

**POST** `/assessments/alzheimer/emotion/score/`
Score the test answers.
- **Body**:
  ```json
  {
      "answers": {
          "img1": "Happy",
          "img2": "Sad"
      }
  }
  ```
- **Response**:
  ```json
  {
      "score": 8,
      "total": 10
  }
  ```

### Word Memory Test
**GET** `/assessments/alzheimer/word/config/`
Get list of words to display.
- **Response**:
  ```json
  {
      "words": ["Apple", "Table", "Penny", ...]
  }
  ```

**POST** `/assessments/alzheimer/word/score/`
Score the user's recall input.
- **Body**:
  ```json
  {
      "original_words": ["Apple", "Table", "Penny"],
      "user_input": "Apple, Table"
  }
  ```
- **Response**:
  ```json
  {
      "score": 2,
      "recalled_words": ["Apple", "Table"],
      "missed_words": ["Penny"]
  }
  ```

### Category Fluency Test
**POST** `/assessments/alzheimer/fluency/score/`
Score verbal fluency (e.g., naming animals).
- **Body**:
  ```json
  {
      "category": "animals",
      "user_input": "cat dog bird dog fish"
  }
  ```
- **Response**:
  ```json
  {
      "score": 4,
      "unique_words": ["cat", "dog", "bird", "fish"],
      "repeated_words_count": 1
  }
  ```

### Speech Coherence Test
**POST** `/assessments/alzheimer/speech/score/`
Analyze speech transcription for coherence.
- **Body**:
  ```json
  {
      "text": "I was walking park yesterday."
  }
  ```
- **Response**:
  ```json
  {
      "score": 75.0,
      "grammar_issues": 1,
      "features": {...}
  }
  ```

### AERI Summary
**POST** `/assessments/alzheimer/summary/`
Aggregate all Alzheimer's test scores into a final report.
- **Body**:
  ```json
  {
      "speech_score": 80,
      "memory_score": 7,
      "fluency_score": 15
  }
  ```
- **Response**:
  ```json
  {
      "aeri_score": 78.5,
      "risk_level": "Low Risk",
      "breakdown": {...}
  }
  ```

---

## History

### User History
**GET** `/history/`
Get chronological list of all past assessments.
- **Response**:
  ```json
  [
      {
          "type": "Parkinson's Quiz",
          "date": "2024-03-15T10:00:00Z",
          "result": "Stage 1",
          "details": {...}
      },
      {
          "type": "Epilepsy",
          "date": "2024-03-14T14:30:00Z",
          "result": "Low Risk",
          "details": {...}
      }
  ]
  ```
