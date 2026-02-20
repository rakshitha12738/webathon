"""
RAG (Retrieval-Augmented Generation) routes
"""
import os
import tempfile
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.services.firebase_service import FirebaseService
from app.services.rag_service import RAGService
from app.utils.auth_utils import token_required, role_required

rag_bp = Blueprint('rag', __name__)
firebase = FirebaseService()
rag_service = RAGService()

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@rag_bp.route('/upload-discharge', methods=['POST'])
@token_required
@role_required('patient')
def upload_discharge():
    """
    Upload discharge document PDF
    
    Expected: multipart/form-data with 'file' field
    """
    try:
        patient_id = request.current_user['user_id']
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        try:
            # Upload to Firebase Storage
            storage_path = f"discharge_documents/{patient_id}/{filename}"
            file_url = firebase.upload_file(temp_path, storage_path)
            
            # Process document with RAG service
            result = rag_service.upload_discharge_document(patient_id, temp_path, file_url)
            
            return jsonify({
                'message': 'Discharge document uploaded and processed successfully',
                'file_url': file_url,
                'document_id': result['document_id'],
                'chunks_processed': result['chunks_processed']
            }), 201
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({'error': f'Failed to upload discharge document: {str(e)}'}), 500

@rag_bp.route('/ask', methods=['POST'])
@token_required
@role_required('patient')
def ask_question():
    """
    Ask a question about discharge instructions
    
    Expected JSON:
    {
        "question": "string"
    }
    """
    try:
        patient_id = request.current_user['user_id']
        data = request.get_json()
        
        if 'question' not in data:
            return jsonify({'error': 'Question is required'}), 400
        
        question = data['question']
        
        if not question.strip():
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        # Retrieve relevant chunks
        relevant_chunks = rag_service.retrieve_relevant_chunks(patient_id, question, top_k=5)
        
        if not relevant_chunks:
            return jsonify({
                'answer': 'I could not find relevant information in your discharge documents. Please consult your doctor directly.',
                'alert_flag': False,
                'source': 'no_context'
            }), 200
        
        # Generate answer
        result = rag_service.generate_answer(question, relevant_chunks)
        
        return jsonify({
            'answer': result['answer'],
            'alert_flag': result['alert_flag'],
            'source': result['source']
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to process question: {str(e)}'}), 500

