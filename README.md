# RECOVER.AI – Intelligent Post-Discharge Recovery Monitoring System

A production-quality Flask backend for monitoring patient recovery after hospital discharge using Firebase Firestore, Qdrant vector database, and AI-powered risk assessment.

## Features

- **Authentication**: JWT-based authentication with bcrypt password hashing
- **Patient Management**: Daily log tracking, risk assessment, and adaptive guidance
- **Doctor Dashboard**: Patient monitoring with risk scores and complication indices
- **RAG System**: Intelligent Q&A system using discharge documents with Qdrant vector search
- **Risk Engine**: Real-time risk assessment based on pain trends, swelling, and recovery stage

## Tech Stack

- Python 3.10+
- Flask 3.0.0
- Flask-CORS 4.0.0
- Firebase Admin SDK (Firestore & Storage)
- Qdrant (Vector Database)
- OpenAI API (for RAG responses)
- Sentence Transformers (for embeddings)
- bcrypt (password hashing)
- PyJWT (JWT tokens)

## Project Structure

```
/app
  /routes
    auth.py          # Authentication routes
    patient.py       # Patient routes
    doctor.py        # Doctor routes
    rag.py           # RAG routes
  /services
    firebase_service.py  # Firebase operations
    risk_engine.py       # Risk assessment engine
    rag_service.py       # RAG service
  /utils
    auth_utils.py    # Authentication utilities
    config.py        # Configuration
  __init__.py        # Flask app initialization
run.py              # Application entry point
requirements.txt    # Python dependencies
README.md          # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10 or higher
- Firebase project with Firestore and Storage enabled
- Qdrant server (local or cloud)
- OpenAI API key (optional, for RAG responses)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Firebase Setup

1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Firestore Database
3. Enable Firebase Storage
4. Generate a service account key:
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - Save the JSON file as `serviceAccountKey.json` in the project root

### 4. Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=discharge_documents
OPENAI_API_KEY=your-openai-api-key-here
```

### 5. Qdrant Setup

#### Option A: Local Qdrant (Docker)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

#### Option B: Qdrant Cloud

Use your Qdrant Cloud URL and update `QDRANT_HOST` in `.env`

### 6. Firestore Collections

The following collections will be created automatically:
- `users` - User accounts
- `recovery_profiles` - Patient recovery profiles
- `daily_logs` - Daily patient logs
- `discharge_documents` - Discharge document metadata
- `risk_scores` - Risk assessment scores

### 7. Run the Application

```bash
python run.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### Authentication

#### POST `/api/register`
Register a new user

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123",
  "role": "patient",
  "assigned_doctor_id": "doctor_id_here"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user_id": "user_id_here",
  "token": "jwt_token_here",
  "role": "patient"
}
```

#### POST `/api/login`
Login user

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user_id": "user_id_here",
  "token": "jwt_token_here",
  "role": "patient",
  "name": "John Doe"
}
```

### Patient Routes

All patient routes require authentication header:
```
Authorization: Bearer <token>
```

#### POST `/api/patient/daily-log`
Create a daily log entry

**Request Body:**
```json
{
  "date": "2024-01-15",
  "pain_level": 5,
  "mood_level": 3,
  "sleep_hours": 7.5,
  "appetite": "good",
  "swelling": false,
  "body_part": "knee",
  "note_text": "Feeling better today"
}
```

**Response:**
```json
{
  "message": "Daily log created successfully",
  "log_id": "log_id_here",
  "risk_status": "monitor",
  "risk_score": 25,
  "deviation_flag": false,
  "complication_index": 0
}
```

#### GET `/api/patient/my-logs`
Get all daily logs for the current patient

**Response:**
```json
{
  "logs": [
    {
      "id": "log_id",
      "patient_id": "patient_id",
      "date": "2024-01-15",
      "pain_level": 5,
      "mood_level": 3,
      "sleep_hours": 7.5,
      "appetite": "good",
      "swelling": false,
      "body_part": "knee",
      "note_text": "Feeling better",
      "risk_status": "monitor"
    }
  ],
  "count": 1
}
```

#### GET `/api/patient/guidance`
Get stage-based recovery guidance

**Response:**
```json
{
  "stage": "Week 1",
  "days_since_start": 3,
  "focus": "Rest and initial healing",
  "recommendations": [
    "Take prescribed medications as directed",
    "Rest the affected area",
    "Apply ice if recommended"
  ],
  "acceptable_pain_range": "0-5",
  "warning_signs": [
    "Severe pain (8+)",
    "Signs of infection"
  ],
  "current_risk_status": "stable",
  "risk_score": 15
}
```

### Doctor Routes

All doctor routes require authentication header:
```
Authorization: Bearer <token>
```

#### GET `/api/doctor/patients`
Get all patients assigned to the doctor

**Response:**
```json
{
  "patients": [
    {
      "id": "patient_id",
      "name": "John Doe",
      "email": "john@example.com",
      "latest_risk_status": "monitor",
      "latest_risk_score": 25,
      "deviation_flag": false,
      "complication_index": 0
    }
  ],
  "count": 1
}
```

#### GET `/api/doctor/patient/<patient_id>`
Get detailed patient information

**Response:**
```json
{
  "patient": {
    "id": "patient_id",
    "name": "John Doe",
    "email": "john@example.com",
    "role": "patient"
  },
  "recovery_profile": {
    "id": "profile_id",
    "patient_id": "patient_id",
    "condition_type": "knee surgery",
    "expected_duration_days": 42,
    "acceptable_pain_week_1": 5,
    "acceptable_pain_week_3": 4,
    "start_date": "2024-01-12T00:00:00"
  },
  "daily_logs": [...],
  "log_count": 5,
  "latest_risk_score": {
    "score": 25,
    "status": "monitor",
    "deviation_flag": false,
    "complication_index": 0
  },
  "recent_risk_scores": [...],
  "complication_index": 0
}
```

### RAG Routes

#### POST `/api/rag/upload-discharge`
Upload discharge document PDF

**Request:** multipart/form-data
- `file`: PDF file

**Response:**
```json
{
  "message": "Discharge document uploaded and processed successfully",
  "file_url": "https://storage.googleapis.com/...",
  "document_id": "doc_id",
  "chunks_processed": 15
}
```

#### POST `/api/rag/ask`
Ask a question about discharge instructions

**Request Body:**
```json
{
  "question": "When can I start exercising?"
}
```

**Response:**
```json
{
  "answer": "Based on your discharge documents, you can start light exercises after 2 weeks...",
  "alert_flag": false,
  "source": "openai"
}
```

## Risk Engine Logic

The risk engine evaluates:

1. **Pain >= 8** → `needs_review`
2. **Swelling + Pain >= 7** → `high_risk`
3. **Increasing pain trend** (3 consecutive days) → `monitor`
4. **Deviation from acceptable range** → `deviation_flag = True`
5. **Complication Index**: If `deviation_flag + swelling + sleep < 4` → `complication_index = 35%`

**Risk Status Levels:**
- `stable`: Low risk, normal recovery
- `monitor`: Moderate risk, continue monitoring
- `needs_review`: Elevated risk, doctor review recommended
- `high_risk`: High risk, immediate attention needed

## Sample Postman Collection

### Register Patient
```json
POST http://localhost:5000/api/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "patient@example.com",
  "password": "password123",
  "role": "patient",
  "assigned_doctor_id": "doctor_id_here"
}
```

### Register Doctor
```json
POST http://localhost:5000/api/register
Content-Type: application/json

{
  "name": "Dr. Smith",
  "email": "doctor@example.com",
  "password": "password123",
  "role": "doctor"
}
```

### Login
```json
POST http://localhost:5000/api/login
Content-Type: application/json

{
  "email": "patient@example.com",
  "password": "password123"
}
```

### Create Daily Log
```json
POST http://localhost:5000/api/patient/daily-log
Content-Type: application/json
Authorization: Bearer <token>

{
  "pain_level": 5,
  "mood_level": 3,
  "sleep_hours": 7.5,
  "appetite": "good",
  "swelling": false,
  "body_part": "knee",
  "note_text": "Feeling better today"
}
```

### Ask Question
```json
POST http://localhost:5000/api/rag/ask
Content-Type: application/json
Authorization: Bearer <token>

{
  "question": "When can I start exercising?"
}
```

## Security Notes

- All passwords are hashed using bcrypt
- JWT tokens expire after 24 hours
- Role-based access control for routes
- Input validation on all endpoints
- Secure file upload handling

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `409`: Conflict
- `500`: Internal Server Error

## Development

To run in development mode:

```bash
export FLASK_ENV=development
python run.py
```

## Production Deployment

1. Set `FLASK_ENV=production`
2. Use a production WSGI server (e.g., Gunicorn)
3. Configure proper CORS origins
4. Use environment variables for all secrets
5. Enable Firebase security rules
6. Use HTTPS

## License

This project is created for hackathon purposes.

