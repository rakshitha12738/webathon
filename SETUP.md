# Quick Setup Guide

## Prerequisites Checklist

- [ ] Python 3.10+ installed
- [ ] Firebase project created
- [ ] Firebase service account key downloaded (`serviceAccountKey.json`)
- [ ] Qdrant server running (Docker or Cloud)
- [ ] OpenAI API key (optional, for RAG)

## Step-by-Step Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

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

### 3. Start Qdrant (if using local)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 4. Place Firebase Credentials

Place your `serviceAccountKey.json` file in the project root directory.

### 5. Run the Application

```bash
python run.py
```

The server will start on `http://localhost:5000`

## Testing the API

### 1. Register a Doctor
```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Smith",
    "email": "doctor@example.com",
    "password": "password123",
    "role": "doctor"
  }'
```

Save the `user_id` from the response.

### 2. Register a Patient
```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "patient@example.com",
    "password": "password123",
    "role": "patient",
    "assigned_doctor_id": "doctor_user_id_here"
  }'
```

### 3. Create Recovery Profile (Firestore)

You need to manually create a recovery profile in Firestore. Go to Firebase Console > Firestore Database and add a document to the `recovery_profiles` collection:

```json
{
  "patient_id": "patient_user_id_here",
  "condition_type": "knee surgery",
  "expected_duration_days": 42,
  "acceptable_pain_week_1": 5,
  "acceptable_pain_week_3": 4,
  "start_date": "2024-01-12T00:00:00"
}
```

### 4. Login as Patient
```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@example.com",
    "password": "password123"
  }'
```

Save the `token` from the response.

### 5. Create Daily Log
```bash
curl -X POST http://localhost:5000/api/patient/daily-log \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "pain_level": 5,
    "mood_level": 3,
    "sleep_hours": 7.5,
    "appetite": "good",
    "swelling": false,
    "body_part": "knee",
    "note_text": "Feeling better today"
  }'
```

## Firestore Indexes

You may need to create composite indexes in Firestore for:
- `daily_logs` collection: `patient_id` + `date` (descending)
- `risk_scores` collection: `patient_id` + `timestamp` (descending)

Firebase will prompt you to create these when you first query them.

## Troubleshooting

### Firebase Credentials Error
- Ensure `serviceAccountKey.json` is in the project root
- Check that the file path in `.env` matches

### Qdrant Connection Error
- Verify Qdrant is running: `curl http://localhost:6333/health`
- Check `QDRANT_HOST` and `QDRANT_PORT` in `.env`

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version: `python --version` (should be 3.10+)

### RAG Not Working
- OpenAI API key is optional - the system will use a fallback response
- Ensure Qdrant is running and accessible
- Check that discharge documents have been uploaded

