# Firebase Setup — All Variables & Steps

To fix **"Firebase is not initialized. Place serviceAccountKey.json in the project root"** and get patient details, logs, and alerts working, do the following.

---

## 1. Variables the app uses for Firebase

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FIREBASE_CREDENTIALS_PATH` | **Yes** (for real DB) | `serviceAccountKey.json` | Path to the service account JSON file (relative to project root or absolute). |
| `FIREBASE_STORAGE_BUCKET` | No | `''` | Storage bucket name, e.g. `your-project-id.appspot.com`. Only needed for discharge document uploads. |

These are read from **environment variables** or from a **`.env`** file in the project root. The app also uses `Config.FIREBASE_CREDENTIALS_PATH` and `Config.FIREBASE_STORAGE_BUCKET` from `app/utils/config.py`.

---

## 2. Create and download the service account key (no variables to “generate”)

You do **not** generate Firebase variables yourself. You create a project in Firebase, then **download** one JSON file.

### Step 1: Create a Firebase project

1. Go to [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** (or use an existing project).
3. Follow the wizard (Google Analytics optional).

### Step 2: Enable Firestore and the Cloud Firestore API

Firestore in Firebase automatically enables the **Cloud Firestore API** in Google Cloud. If you see a 403 error like *"Cloud Firestore API has not been used in project ... or it is disabled"*:

1. **Enable the API directly:**  
   Open this link (replace `YOUR_PROJECT_ID` with your project ID, e.g. `webathon-52f94`):  
   **https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=YOUR_PROJECT_ID**  
   Then click **Enable**.

2. **Or enable via Firebase:**  
   In the project, go to **Build → Firestore Database** → **Create database** (if you haven’t already). This also enables the API.

3. Wait 1–2 minutes after enabling, then retry your request.

### Step 3: (Optional) Enable Storage

Only needed if you use discharge document uploads.

1. Go to **Build → Storage**.
2. Click **Get started** and accept defaults if you want.

### Step 4: Get the service account JSON key

1. Click the **gear icon** next to “Project Overview” → **Project settings**.
2. Open the **Service accounts** tab.
3. Click **Generate new private key** → **Generate key**.
4. A JSON file will download (e.g. `your-project-name-firebase-adminsdk-xxxxx.json`).

### Step 5: Place the file in the project root

1. Rename the downloaded file to **`serviceAccountKey.json`** (or keep the name and set `FIREBASE_CREDENTIALS_PATH` to that name).
2. Put it in the **project root** (same folder as `run.py`):

   ```
   webathon/
   ├── run.py
   ├── serviceAccountKey.json   ← here
   ├── app/
   ├── frontend/
   └── .env
   ```

3. **Do not** commit this file to git. Add to `.gitignore` (e.g. `serviceAccountKey.json`).

---

## 3. Set environment variables

Create a file named **`.env`** in the project root (same folder as `run.py`) with at least:

```env
# Required for Firebase (Firestore + optional Storage)
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com

# App secrets
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
```

Replace `your-project-id` with your Firebase project ID (from Project settings → General).

If the JSON key file has a different name or path, set:

```env
FIREBASE_CREDENTIALS_PATH=path/to/your-key-file.json
```

---

## 4. What the service account JSON contains

The downloaded file looks like this (you never edit it by hand; Firebase generates it):

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...@your-project-id.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "...",
  "client_x509_cert_url": "..."
}
```

The app only needs the **file path** via `FIREBASE_CREDENTIALS_PATH`; it loads this JSON internally. You don’t set these fields as separate env vars.

---

## 5. Checklist

- [ ] Firebase project created.
- [ ] Firestore Database enabled.
- [ ] Service account key generated and downloaded.
- [ ] File renamed to `serviceAccountKey.json` and placed in project root (or path set in `.env`).
- [ ] `.env` created with `FIREBASE_CREDENTIALS_PATH` (and optionally `FIREBASE_STORAGE_BUCKET`).
- [ ] Backend restarted (`python run.py`).

After this, “Firebase is not initialized” should be resolved and patient details should load (assuming the patient exists in Firestore and is assigned to the doctor).
