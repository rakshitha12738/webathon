"""
firebase_service.py – Firebase Admin SDK initialisation (Firestore + Storage).

Call ``init_firebase()`` once during application start-up.  After that, use
``get_db()`` and ``get_bucket()`` from anywhere in the application.
"""

import logging
import os

import firebase_admin
from firebase_admin import credentials, firestore, storage

logger = logging.getLogger(__name__)

# Module-level singletons populated by init_firebase()
_db = None
_bucket = None


def init_firebase(credentials_path: str, storage_bucket: str) -> None:
    """
    Initialise the Firebase Admin SDK.

    Parameters
    ----------
    credentials_path:
        Filesystem path to the ``serviceAccountKey.json`` file.
    storage_bucket:
        Firebase Storage bucket name (e.g. ``"my-project.appspot.com"``).
        Pass an empty string to skip Storage initialisation.
    """
    global _db, _bucket

    if firebase_admin._apps:
        # Already initialised – nothing to do
        return

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Firebase credentials not found at '{credentials_path}'. "
            "Set FIREBASE_CREDENTIALS_PATH to the correct path."
        )

    cred = credentials.Certificate(credentials_path)
    options = {"storageBucket": storage_bucket} if storage_bucket else {}
    firebase_admin.initialize_app(cred, options)

    _db = firestore.client()
    _bucket = storage.bucket() if storage_bucket else None

    logger.info("Firebase Admin SDK initialised successfully.")


def get_db():
    """
    Return the Firestore client.

    Raises
    ------
    RuntimeError
        If :func:`init_firebase` has not been called yet.
    """
    if _db is None:
        raise RuntimeError(
            "Firestore client is not initialised. "
            "Call init_firebase() before using get_db()."
        )
    return _db


def get_bucket():
    """
    Return the Firebase Storage bucket.

    May return ``None`` if no storage bucket was configured.
    """
    return _bucket
