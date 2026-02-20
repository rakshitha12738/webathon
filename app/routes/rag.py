"""
rag.py – Retrieval-Augmented Generation endpoints.

Endpoints
---------
POST /rag/upload-discharge   Upload a PDF discharge document and index it
POST /rag/ask                Ask a question grounded in discharge documents
"""

import logging
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

from app.services.firebase_service import get_bucket, get_db
from app.services.rag_service import process_and_store_document, retrieve_and_answer
from app.utils.auth_utils import login_required, role_required

logger = logging.getLogger(__name__)
bp = Blueprint("rag", __name__, url_prefix="/rag")


# ─────────────────────────────────────────────────────────────────────────────
# POST /rag/upload-discharge
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/upload-discharge", methods=["POST"])
@login_required
@role_required("patient")
def upload_discharge(current_user):
    """
    Upload a PDF discharge document.

    The PDF is:
      1. Stored in Firebase Storage (if a bucket is configured)
      2. Text is extracted and chunked
      3. Chunks are embedded and stored in Qdrant
      4. Extracted text & metadata are persisted in Firestore

    Request (multipart/form-data)
    -----------------------------
    file : PDF file upload (field name "file")

    Returns
    -------
    201  { message, document_id, chunks_stored }
    400  { error }
    500  { error }
    """
    patient_id = current_user["sub"]

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use field name 'file'."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"error": "Uploaded file has no filename."}), 400

    if not uploaded_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    try:
        file_bytes = uploaded_file.read()
        document_id = str(uuid.uuid4())

        # ── Upload to Firebase Storage (optional) ────────────────────────────
        file_url = ""
        bucket = get_bucket()
        if bucket:
            blob_path = f"discharge_documents/{patient_id}/{document_id}.pdf"
            blob = bucket.blob(blob_path)
            blob.upload_from_string(file_bytes, content_type="application/pdf")
            # Use a time-limited signed URL to keep medical documents private
            import datetime as _dt
            expiry = _dt.timedelta(seconds=cfg.STORAGE_SIGNED_URL_EXPIRY)
            file_url = blob.generate_signed_url(expiration=expiry, method="GET")

        # ── RAG pipeline: extract → chunk → embed → store in Qdrant ─────────
        cfg = current_app.config["APP_CONFIG"]
        result = process_and_store_document(file_bytes, patient_id, document_id, cfg)

        # ── Persist metadata in Firestore ────────────────────────────────────
        db = get_db()
        doc_ref = db.collection("discharge_documents").document(document_id)
        doc_ref.set(
            {
                "id": document_id,
                "patient_id": patient_id,
                "file_url": file_url,
                "extracted_text": result["extracted_text"],
                "chunks_stored": result["chunks_stored"],
                "uploaded_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )

        return jsonify(
            {
                "message": "Discharge document uploaded and indexed successfully",
                "document_id": document_id,
                "chunks_stored": result["chunks_stored"],
            }
        ), 201

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to upload discharge document for patient %s", patient_id)
        return jsonify({"error": "Upload failed", "detail": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /rag/ask
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/ask", methods=["POST"])
@login_required
@role_required("patient")
def ask(current_user):
    """
    Ask a question grounded strictly in the patient's discharge documents.

    Request body (JSON)
    -------------------
    question : str  – the patient's free-text question

    Returns
    -------
    200  { answer, alert, sources }
         alert is True if retrieved context contains danger keywords.
    400  { error }
    500  { error }
    """
    patient_id = current_user["sub"]
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "question field is required"}), 400

    try:
        cfg = current_app.config["APP_CONFIG"]
        result = retrieve_and_answer(question, patient_id, cfg)
        return jsonify(result), 200

    except Exception as exc:
        logger.exception("RAG ask failed for patient %s", patient_id)
        return jsonify({"error": "Failed to process question", "detail": str(exc)}), 500
