# RECOVER.AI – Intelligent Post-Discharge Recovery Monitoring System

A production-quality Flask backend for monitoring patient recovery after hospital discharge.  
It combines rule-based risk scoring, Firebase Firestore persistence, and a RAG (Retrieval-Augmented Generation) pipeline backed by Qdrant to answer patient questions from their discharge documents.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Server](#running-the-server)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Postman Examples](#postman-examples)
- [Data Models](#data-models)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Framework | Flask 3 |
| CORS | Flask-CORS |
| Auth | JWT (PyJWT) + bcrypt |
| Database | Firebase Firestore |
| File Storage | Firebase Storage |
| Vector DB | Qdrant |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| LLM | google/flan-t5-base (HuggingFace) |
| PDF Parsing | pypdf |
| Production server | Gunicorn |

---

## Project Structure

```
/app
  /routes
    auth.py          # POST /auth/register, POST /auth/login
    patient.py       # POST /patient/daily-log, GET /patient/my-logs, GET /patient/guidance
    doctor.py        # GET /doctor/patients, GET /doctor/patient/<id>
    rag.py           # POST /rag/upload-discharge, POST /rag/ask
  /services
    firebase_service.py   # Firestore + Storage initialisation helpers
    risk_engine.py        # Rule-based risk scoring
    rag_service.py        # Qdrant vector store + LLM inference
  /utils
    auth_utils.py    # JWT helpers, @login_required, @role_required decorators
    config.py        # Configuration loaded from environment variables
  __init__.py        # Flask application factory
run.py               # Entry point
requirements.txt
README.md
```

---

## Prerequisites

1. **Python 3.10+** installed.
2. **Firebase project** – create one at https://console.firebase.google.com.
   - Enable Firestore (Native mode).
   - (Optional) Enable Firebase Storage.
   - Download the service-account key: *Project Settings → Service Accounts → Generate new private key*.  
     Save as `serviceAccountKey.json` in the project root.
3. **Qdrant** running locally or accessible via network.  
   Quickstart with Docker:
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

---

## Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd webathon

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Place your Firebase service-account key
cp /path/to/serviceAccountKey.json .

# 5. Configure environment variables (see below or create a .env file)
export SECRET_KEY="your-secret-key"
export FIREBASE_CREDENTIALS_PATH="serviceAccountKey.json"
export FIREBASE_STORAGE_BUCKET="your-project.appspot.com"  # optional
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
```

---

## Running the Server

**Development:**
```bash
python run.py
```

**Production (Gunicorn):**
```bash
gunicorn "run:app" --bind 0.0.0.0:5000 --workers 4
```

The server will start on `http://0.0.0.0:5000`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | JWT signing secret – **always override in production** |
| `JWT_EXPIRY_SECONDS` | `86400` | Token lifetime in seconds (default 24 h) |
| `FIREBASE_CREDENTIALS_PATH` | `serviceAccountKey.json` | Path to Firebase service-account JSON |
| `FIREBASE_STORAGE_BUCKET` | *(empty)* | Firebase Storage bucket name (optional) |
| `QDRANT_HOST` | `localhost` | Qdrant server hostname |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `QDRANT_COLLECTION` | `discharge_documents` | Qdrant collection name |
| `QDRANT_VECTOR_SIZE` | `384` | Embedding dimension (must match model) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence-transformer model |
| `LLM_MODEL` | `google/flan-t5-base` | HuggingFace text-generation model |
| `FLASK_DEBUG` | `false` | Set to `true` for debug mode |

---

## API Reference

All endpoints return JSON.  
Protected endpoints require the header: `Authorization: Bearer <token>`.

### Auth

#### `POST /auth/register`
Register a new user.

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "securepassword",
  "role": "patient",
  "assigned_doctor_id": "doctor-uid-123"
}
```

#### `POST /auth/login`
```json
{
  "email": "jane@example.com",
  "password": "securepassword"
}
```
Returns `{ "token": "...", "user_id": "...", "role": "patient" }`.

---

### Patient (requires `role: patient`)

#### `POST /patient/daily-log`
```json
{
  "pain_level": 6,
  "mood_level": 7,
  "sleep_hours": 5.5,
  "appetite": "normal",
  "swelling": false,
  "body_part": "left knee",
  "note_text": "Feeling slightly better today."
}
```
Returns `{ "log_id": "...", "risk": { "score": 0.69, "status": "stable", ... } }`.

#### `GET /patient/my-logs`
Returns `{ "logs": [...] }`.

#### `GET /patient/guidance`
Returns stage-based recovery tips based on days since `start_date` in the recovery profile.

---

### Doctor (requires `role: doctor`)

#### `GET /doctor/patients`
Returns all patients assigned to the authenticated doctor with their latest risk status.

#### `GET /doctor/patient/<patient_id>`
Returns full patient detail: user info, recovery profile, all logs, and latest risk score.

---

### RAG (requires `role: patient`)

#### `POST /rag/upload-discharge`
Multipart form upload.  Field name: `file` (PDF).  
Extracts text, embeds chunks, stores in Qdrant, and saves metadata in Firestore.

#### `POST /rag/ask`
```json
{
  "question": "What medications should I take after discharge?"
}
```
Returns `{ "answer": "...", "alert": false, "sources": [...] }`.  
`alert: true` means the retrieved context contains danger keywords (e.g. "seek immediate care").

---

## Postman Examples

### Register (Doctor)
```json
POST /auth/register
{
  "name": "Dr. Smith",
  "email": "drsmith@hospital.com",
  "password": "Password123!",
  "role": "doctor"
}
```

### Register (Patient)
```json
POST /auth/register
{
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "password": "Password123!",
  "role": "patient",
  "assigned_doctor_id": "<doctor_user_id>"
}
```

### Login
```json
POST /auth/login
{
  "email": "alice@example.com",
  "password": "Password123!"
}
```

### Submit Daily Log
```json
POST /patient/daily-log
Authorization: Bearer <token>
{
  "pain_level": 7,
  "mood_level": 6,
  "sleep_hours": 6,
  "appetite": "poor",
  "swelling": true,
  "body_part": "right ankle",
  "note_text": "Ankle feels swollen after standing."
}
```

### Ask RAG Question
```json
POST /rag/ask
Authorization: Bearer <token>
{
  "question": "Can I take ibuprofen with my current medication?"
}
```

---

## Data Models

### `users`
| Field | Type | Description |
|---|---|---|
| id | string | Document ID |
| name | string | Display name |
| email | string | Unique email |
| password | string | bcrypt hash |
| role | string | "doctor" or "patient" |
| assigned_doctor_id | string | Doctor's user ID (patients only) |

### `recovery_profiles`
| Field | Type | Description |
|---|---|---|
| id | string | Document ID |
| patient_id | string | Reference to users |
| condition_type | string | e.g. "knee replacement" |
| expected_duration_days | int | Expected recovery days |
| acceptable_pain_week_1 | int | Max acceptable pain score in week 1 |
| acceptable_pain_week_3 | int | Max acceptable pain score from week 3 |
| start_date | string | ISO-8601 date "YYYY-MM-DD" |

### `daily_logs`
| Field | Type | Description |
|---|---|---|
| id | string | Document ID |
| patient_id | string | Reference to users |
| date | string | ISO date "YYYY-MM-DD" |
| pain_level | int | 0–10 |
| mood_level | int | 0–10 |
| sleep_hours | float | Hours slept |
| appetite | string | e.g. "good", "poor" |
| swelling | bool | Swelling present |
| body_part | string | Affected area |
| note_text | string | Free-text note |
| risk_status | string | Computed by risk engine |

### `risk_scores`
| Field | Type | Description |
|---|---|---|
| id | string | Document ID |
| patient_id | string | Reference to users |
| score | float | Normalised 0–1 |
| status | string | stable / monitor / needs_review / high_risk |
| deviation_flag | bool | Pain outside acceptable range |
| complication_index | string | e.g. "35%" or "0%" |

### `discharge_documents`
| Field | Type | Description |
|---|---|---|
| id | string | Document ID |
| patient_id | string | Reference to users |
| file_url | string | Firebase Storage URL |
| extracted_text | string | Full extracted PDF text |
| chunks_stored | int | Number of vector chunks in Qdrant |
