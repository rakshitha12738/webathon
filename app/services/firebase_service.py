"""
Firebase service for Firestore and Storage operations
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
from app.utils.config import Config
import os
import uuid

class FirebaseService:
    """Service for Firebase operations"""
    
    _instance = None
    _db = None
    _bucket = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Firebase Admin SDK"""
        try:
            if not firebase_admin._apps:
                cred_path = Config.FIREBASE_CREDENTIALS_PATH
                if not os.path.exists(cred_path):
                    # Fall back to an in-memory stub so the backend can run without
                    # external Firebase during local development / smoke tests.
                    print(
                        f"[WARNING] Firebase credentials not found at '{cred_path}'. "
                        "Using in-memory datastore for local testing."
                    )
                    self._in_memory = True
                    # initialize simple in-memory collections
                    self._store = {
                        'users': {},
                        'recovery_profiles': {},
                        'daily_logs': {},
                        'risk_scores': {},
                        'discharge_documents': {}
                    }
                    return

                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': Config.FIREBASE_STORAGE_BUCKET
                })

            self._db = firestore.client()
            if Config.FIREBASE_STORAGE_BUCKET:
                self._bucket = storage.bucket(Config.FIREBASE_STORAGE_BUCKET)
            self._in_memory = False
        except Exception as e:
            print(f"[WARNING] Firebase initialization failed: {e}. Using in-memory datastore.")
            self._in_memory = True
            self._store = {
                'users': {},
                'recovery_profiles': {},
                'daily_logs': {},
                'risk_scores': {},
                'discharge_documents': {}
            }
    
    @property
    def db(self):
        """Get Firestore database instance"""
        if self._db is None:
            raise RuntimeError(
                "Firebase is not initialized. Place serviceAccountKey.json in the project root."
            )
        return self._db
    
    @property
    def bucket(self):
        """Get Storage bucket instance"""
        return self._bucket
    
    # User operations
    def create_user(self, user_data: dict) -> str:
        """
        Create a new user in Firestore
        
        Args:
            user_data: User data dictionary
            
        Returns:
            User document ID
        """
        if getattr(self, '_in_memory', False):
            user_id = str(uuid.uuid4())
            # store a copy
            self._store['users'][user_id] = dict(user_data)
            return user_id

        doc_ref = self._db.collection('users').document()
        doc_ref.set(user_data)
        return doc_ref.id
    
    def get_user_by_email(self, email: str) -> dict:
        """
        Get user by email
        
        Args:
            email: User email
            
        Returns:
            User document data with ID, or None if not found
        """
        if getattr(self, '_in_memory', False):
            for uid, data in self._store['users'].items():
                if data.get('email') == email:
                    out = dict(data)
                    out['id'] = uid
                    return out
            return None

        users_ref = self._db.collection('users')
        query = users_ref.where('email', '==', email).limit(1).stream()
        
        for doc in query:
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            return user_data
        
        return None
    
    def get_user_by_id(self, user_id: str) -> dict:
        """
        Get user by ID
        
        Args:
            user_id: User document ID
            
        Returns:
            User document data with ID, or None if not found
        """
        if getattr(self, '_in_memory', False):
            data = self._store['users'].get(user_id)
            if data:
                out = dict(data)
                out['id'] = user_id
                return out
            return None

        doc_ref = self._db.collection('users').document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            return user_data
        
        return None
    
    # Recovery profile operations
    def create_recovery_profile(self, profile_data: dict) -> str:
        """
        Create a recovery profile
        
        Args:
            profile_data: Recovery profile data
            
        Returns:
            Profile document ID
        """
        if getattr(self, '_in_memory', False):
            pid = str(uuid.uuid4())
            self._store['recovery_profiles'][pid] = dict(profile_data)
            return pid

        doc_ref = self._db.collection('recovery_profiles').document()
        doc_ref.set(profile_data)
        return doc_ref.id
    
    def get_recovery_profile_by_patient(self, patient_id: str) -> dict:
        """
        Get recovery profile for a patient
        
        Args:
            patient_id: Patient user ID
            
        Returns:
            Recovery profile data with ID, or None if not found
        """
        if getattr(self, '_in_memory', False):
            for pid, data in self._store['recovery_profiles'].items():
                if data.get('patient_id') == patient_id:
                    out = dict(data)
                    out['id'] = pid
                    return out
            return None

        profiles_ref = self._db.collection('recovery_profiles')
        query = profiles_ref.where('patient_id', '==', patient_id).limit(1).stream()
        
        for doc in query:
            profile_data = doc.to_dict()
            profile_data['id'] = doc.id
            return profile_data
        
        return None
    
    # Daily log operations
    def create_daily_log(self, log_data: dict) -> str:
        """
        Create a daily log entry
        
        Args:
            log_data: Daily log data
            
        Returns:
            Log document ID
        """
        if getattr(self, '_in_memory', False):
            lid = str(uuid.uuid4())
            self._store['daily_logs'][lid] = dict(log_data)
            return lid

        doc_ref = self._db.collection('daily_logs').document()
        doc_ref.set(log_data)
        return doc_ref.id
    
    def get_patient_logs(self, patient_id: str, limit: int = None) -> list:
        """
        Get all daily logs for a patient
        
        Args:
            patient_id: Patient user ID
            limit: Optional limit on number of logs
            
        Returns:
            List of log documents with IDs
        """
        if getattr(self, '_in_memory', False):
            logs = []
            for lid, data in self._store['daily_logs'].items():
                if data.get('patient_id') == patient_id:
                    out = dict(data)
                    out['id'] = lid
                    logs.append(out)
            # sort by date if present (assume ISO strings)
            logs.sort(key=lambda x: x.get('date', ''), reverse=True)
            if limit:
                return logs[:limit]
            return logs

        logs_ref = self._db.collection('daily_logs')
        # Filter only — no order_by so no composite index is required
        query = logs_ref.where('patient_id', '==', patient_id)

        if limit:
            query = query.limit(limit)

        logs = []
        for doc in query.stream():
            log_data = doc.to_dict()
            log_data['id'] = doc.id
            logs.append(log_data)

        # Sort by date descending in Python (avoids Firestore composite index)
        logs.sort(key=lambda x: x.get('date', ''), reverse=True)
        return logs
    
    def get_recent_patient_logs(self, patient_id: str, count: int = 3) -> list:
        """
        Get recent daily logs for a patient
        
        Args:
            patient_id: Patient user ID
            count: Number of recent logs to retrieve
            
        Returns:
            List of recent log documents with IDs
        """
        return self.get_patient_logs(patient_id, limit=count)
    
    # Risk score operations
    def create_risk_score(self, risk_data: dict) -> str:
        """
        Create a risk score entry
        
        Args:
            risk_data: Risk score data
            
        Returns:
            Risk score document ID
        """
        if getattr(self, '_in_memory', False):
            rid = str(uuid.uuid4())
            self._store['risk_scores'][rid] = dict(risk_data)
            return rid

        doc_ref = self._db.collection('risk_scores').document()
        doc_ref.set(risk_data)
        return doc_ref.id
    
    def get_latest_risk_score(self, patient_id: str) -> dict:
        """
        Get latest risk score for a patient
        
        Args:
            patient_id: Patient user ID
            
        Returns:
            Latest risk score data with ID, or None if not found
        """
        if getattr(self, '_in_memory', False):
            candidates = []
            for rid, data in self._store['risk_scores'].items():
                if data.get('patient_id') == patient_id:
                    out = dict(data)
                    out['id'] = rid
                    candidates.append(out)
            if not candidates:
                return None
            # assume higher 'score' means latest here
            candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
            return candidates[0]

        scores_ref = self._db.collection('risk_scores')
        # Filter only, sort in Python — avoids needing a composite index
        query = scores_ref.where('patient_id', '==', patient_id)

        candidates = []
        for doc in query.stream():
            score_data = doc.to_dict()
            score_data['id'] = doc.id
            candidates.append(score_data)

        if not candidates:
            return None

        # Sort by timestamp if available, otherwise by score
        candidates.sort(
            key=lambda x: str(x.get('timestamp', x.get('score', 0))),
            reverse=True
        )
        return candidates[0]
    
    # Discharge document operations
    def create_discharge_document(self, doc_data: dict) -> str:
        """
        Create a discharge document entry
        
        Args:
            doc_data: Discharge document data
            
        Returns:
            Document ID
        """
        if getattr(self, '_in_memory', False):
            did = str(uuid.uuid4())
            self._store['discharge_documents'][did] = dict(doc_data)
            return did

        doc_ref = self._db.collection('discharge_documents').document()
        doc_ref.set(doc_data)
        return doc_ref.id
    
    def get_discharge_documents_by_patient(self, patient_id: str) -> list:
        """
        Get all discharge documents for a patient
        
        Args:
            patient_id: Patient user ID
            
        Returns:
            List of discharge document data with IDs
        """
        if getattr(self, '_in_memory', False):
            documents = []
            for did, data in self._store['discharge_documents'].items():
                if data.get('patient_id') == patient_id:
                    out = dict(data)
                    out['id'] = did
                    documents.append(out)
            return documents

        docs_ref = self._db.collection('discharge_documents')
        # Fixed: only one .stream() call (was accidentally called twice)
        query = docs_ref.where('patient_id', '==', patient_id)

        documents = []
        for doc in query.stream():
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            documents.append(doc_data)

        return documents
    
    # Doctor operations
    def get_doctor_patients(self, doctor_id: str) -> list:
        """
        Get all patients assigned to a doctor
        
        Args:
            doctor_id: Doctor user ID
            
        Returns:
            List of patient documents with IDs
        """
        if getattr(self, '_in_memory', False):
            patients = []
            for uid, data in self._store['users'].items():
                if data.get('assigned_doctor_id') == doctor_id and data.get('role') == 'patient':
                    out = dict(data)
                    out['id'] = uid
                    patients.append(out)
            return patients

        users_ref = self._db.collection('users')
        # Fixed: only one .stream() call (was accidentally called twice)
        query = users_ref.where('assigned_doctor_id', '==', doctor_id).where('role', '==', 'patient')

        patients = []
        for doc in query.stream():
            patient_data = doc.to_dict()
            patient_data['id'] = doc.id
            patients.append(patient_data)

        return patients
    
    # Storage operations
    def upload_file(self, file_path: str, destination_path: str) -> str:
        """
        Upload a file to Firebase Storage
        
        Args:
            file_path: Local file path
            destination_path: Destination path in storage
            
        Returns:
            Public URL of uploaded file
        """
        if getattr(self, '_in_memory', False):
            raise ValueError("Firebase Storage not available in in-memory mode")

        if not self._bucket:
            raise ValueError("Firebase Storage bucket not configured")
        
        blob = self._bucket.blob(destination_path)
        blob.upload_from_filename(file_path)
        blob.make_public()
        return blob.public_url

