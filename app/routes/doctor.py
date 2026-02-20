"""
Doctor routes
"""
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from app.services.firebase_service import FirebaseService
from app.utils.auth_utils import token_required, role_required

doctor_bp = Blueprint('doctor', __name__)
firebase = FirebaseService()

@doctor_bp.route('/patients', methods=['GET'])
@token_required
@role_required('doctor')
def get_patients():
    """
    Get all patients assigned to the current doctor
    Includes latest risk status for each patient
    """
    try:
        doctor_id = request.current_user['user_id']
        
        # Get assigned patients
        patients = firebase.get_doctor_patients(doctor_id)
        
        # Enrich with latest risk status
        enriched_patients = []
        for patient in patients:
            patient_id = patient['id']
            latest_risk = firebase.get_latest_risk_score(patient_id)
            
            patient_data = {
                'id': patient_id,
                'name': patient.get('name'),
                'email': patient.get('email'),
                'latest_risk_status': latest_risk.get('status', 'stable') if latest_risk else 'stable',
                'latest_risk_score': latest_risk.get('score', 0) if latest_risk else 0,
                'deviation_flag': latest_risk.get('deviation_flag', False) if latest_risk else False,
                'complication_index': latest_risk.get('complication_index', 0) if latest_risk else 0
            }
            enriched_patients.append(patient_data)
        
        return jsonify({
            'patients': enriched_patients,
            'count': len(enriched_patients)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve patients: {str(e)}'}), 500

@doctor_bp.route('/patient/<patient_id>', methods=['GET'])
@token_required
@role_required('doctor')
def get_patient_details(patient_id):
    """
    Get detailed information about a specific patient
    
    Includes:
    - Patient profile
    - Recovery profile
    - All daily logs
    - Risk scores
    - Complication index
    """
    try:
        doctor_id = request.current_user['user_id']
        
        # Get patient
        patient = firebase.get_user_by_id(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Verify patient is assigned to this doctor
        if patient.get('assigned_doctor_id') != doctor_id:
            return jsonify({'error': 'Patient not assigned to you'}), 403
        
        # Get recovery profile
        recovery_profile = firebase.get_recovery_profile_by_patient(patient_id)
        
        # Get all logs
        logs = firebase.get_patient_logs(patient_id)
        
        # Get latest risk score
        latest_risk = firebase.get_latest_risk_score(patient_id)
        
        # Get all risk scores — filter only, sort in Python (avoids composite index requirement)
        risk_scores_ref = firebase.db.collection('risk_scores')
        risk_scores_query = risk_scores_ref.where('patient_id', '==', patient_id).limit(10)
        all_risk_scores = []
        for doc in risk_scores_query.stream():
            score_data = doc.to_dict()
            score_data['id'] = doc.id
            all_risk_scores.append(score_data)
        # Sort descending by timestamp (or score as fallback)
        all_risk_scores.sort(
            key=lambda x: str(x.get('timestamp', x.get('score', 0))),
            reverse=True
        )
        
        # Calculate complication index (use latest if available)
        complication_index = latest_risk.get('complication_index', 0) if latest_risk else 0
        
        response_data = {
            'patient': {
                'id': patient['id'],
                'name': patient.get('name'),
                'email': patient.get('email'),
                'role': patient.get('role')
            },
            'recovery_profile': recovery_profile,
            'daily_logs': logs,
            'log_count': len(logs),
            'latest_risk_score': latest_risk,
            'recent_risk_scores': all_risk_scores,
            'complication_index': complication_index
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve patient details: {str(e)}'}), 500

