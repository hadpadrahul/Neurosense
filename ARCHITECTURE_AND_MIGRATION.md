# Architecture & Migration Guide

## System Overview
The **Parkinson's, Alzheimer's, and Epilepsy Detection System** utilizes a **Hybrid Monolithic Architecture**.
- **Web Interface**: Traditional Django templates (`MVT` pattern) for browser-based access.
- **API Layer**: Stateless REST API (Django REST Framework) for mobile/external access.

Both layers share a unified **Service Layer**, ensuring "Single Source of Truth" for all business logic and ML predictions.

## Service Layer Pattern
The core innovation in this architecture is the extraction of logic from `views.py` into `detection_app/api/services/`.

```mermaid
graph TD
    Web[Web Views (views.py)] --> Service[Service Layer (api/services/)]
    API[API Views (api_views.py)] --> Service
    Service --> ML[ML Models / Logic]
```

### Key Components
1.  **Epilepsy Service** (`epilepsy_service.py`):
    -   Pure function: `assess_epilepsy_risk(answers) -> score`
    -   Used by: `EpilepsyAssessmentAPIView` and `views.epilepsy_home`

2.  **Alzheimer's MRI Service** (`alz_mri_service.py`):
    -   **Pattern B**: Contains `try_load_model_once` and `predict_alz_mri`.
    -   Handles Model loading, image preprocessing, and prediction.

3.  **Alzheimer's Interactive Service** (`alz_interactive_service.py`):
    -   Handles logic for Emotion, Word, Fluency, and Speech tests.
    -   **Stateless**: Functions accept inputs (e.g., user answers) and return scores without reading `request.session`.

## Client-Side State Strategy
For multi-step assessments (like Alzheimer's Interactive Tests), the API adopts a **Client-Side State** model to remain stateless.

| Feature | Legacy Web (Session) | API (Stateless) |
| :--- | :--- | :--- |
| **State Storage** | `request.session['score']` | Client holds `score` variable |
| **Flow Control** | Redirects to next page | Client decides next screen |
| **Final Result** | Server reads session & saves | Client sends all sub-scores to `/summary/` |

**Example Flow (Emotion Test):**
1.  **Config**: Client GETs `/config/` -> receives image URLs.
2.  **Interaction**: Client displays images, collects answers.
3.  **Scoring**: Client POSTs `answers` to `/score/` -> receives `8/10`.
4.  **Next Step**: Client proceeds to Word Test.

## Migration & Parity
The migration process followed strict rules to ensure logic parity:
1.  **Extraction**: Logic moved from `views.py` to `services/` verbatim.
2.  **Wrappers**: New API endpoints wrap these services directly.
3.  **Refactor**: Legacy `views.py` updated to call the same services.
4.  **Verification**: Using `tests/test_api_endpoints.py` to compare expected outputs.

This ensures that the Web App and API always produce identical results given the same input.
