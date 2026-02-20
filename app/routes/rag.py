"""
RAG (Retrieval-Augmented Generation) routes
"""
import os
import tempfile
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.services.firebase_service import FirebaseService
from app.services.rag_service import RAGService
from app.utils.auth_utils import token_required

rag_bp = Blueprint('rag', __name__)
firebase = FirebaseService()
rag_service = RAGService()

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@rag_bp.route('/upload-discharge', methods=['POST'])
@token_required
def upload_discharge():
    """
    Upload discharge document PDF (accessible by both doctors AND patients).

    Expected: multipart/form-data with 'file' field.
    Optional JSON field 'patient_id' – if provided by a doctor, uses that patient's ID;
    otherwise falls back to the authenticated user's own ID.
    """
    try:
        current_user = request.current_user
        # Doctors can upload on behalf of a patient by passing patient_id in form
        patient_id = request.form.get('patient_id') or current_user['user_id']

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)

        try:
            storage_path = f"discharge_documents/{patient_id}/{filename}"
            file_url = firebase.upload_file(temp_path, storage_path)
            result   = rag_service.upload_discharge_document(patient_id, temp_path, file_url)

            return jsonify({
                'message':          'Discharge document uploaded and processed successfully',
                'file_url':         file_url,
                'document_id':      result['document_id'],
                'chunks_processed': result['chunks_processed']
            }), 201
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        return jsonify({'error': f'Failed to upload discharge document: {str(e)}'}), 500


@rag_bp.route('/ask', methods=['POST'])
@token_required
def ask_question():
    """
    Ask a question about discharge instructions.

    Expected JSON:  { "question": "string" }

    Response:  { "answer": "...", "alert_flag": bool, "source": "gemini|fallback|no_docs|..." }
    """
    try:
        patient_id = request.current_user['user_id']
        data       = request.get_json() or {}

        question = data.get('question', '').strip()
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400

        # Retrieve patient-specific context chunks
        relevant_chunks = rag_service.retrieve_relevant_chunks(patient_id, question, top_k=5)

        if not relevant_chunks:
            # No discharge docs – use Gemini for a general answer
            result = rag_service.answer_general_question(question)
        else:
            result = rag_service.generate_answer(question, relevant_chunks)

        return jsonify({
            'answer':     result['answer'],
            'alert_flag': result['alert_flag'],
            'source':     result['source']
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to process question: {str(e)}'}), 500
