"""
Patient routes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.services.firebase_service import FirebaseService
from app.services.risk_engine import RiskEngine
from app.utils.auth_utils import token_required, role_required

patient_bp = Blueprint('patient', __name__)
firebase = FirebaseService()
risk_engine = RiskEngine()

@patient_bp.route('/daily-log', methods=['POST'])
@token_required
@role_required('patient')
def create_daily_log():
    """
    Create a daily log entry
    
    Expected JSON:
    {
        "date": "YYYY-MM-DD" (optional, defaults to today),
        "pain_level": int (0-10),
        "mood_level": int (1-5),
        "sleep_hours": float,
        "appetite": "good" | "fair" | "poor",
        "swelling": bool,
        "body_part": "string",
        "note_text": "string"
    }
    """
    try:
        patient_id = request.current_user['user_id']
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['pain_level', 'mood_level', 'sleep_hours', 'appetite']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate pain level range
        if not (0 <= data['pain_level'] <= 10):
            return jsonify({'error': 'Pain level must be between 0 and 10'}), 400
        
        # Get recovery profile
        recovery_profile = firebase.get_recovery_profile_by_patient(patient_id)
        if not recovery_profile:
            return jsonify({'error': 'Recovery profile not found. Please contact your doctor.'}), 404
        
        # Prepare log data
        log_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        log_data = {
            'patient_id': patient_id,
            'date': log_date,
            'pain_level': data['pain_level'],
            'mood_level': data['mood_level'],
            'sleep_hours': data['sleep_hours'],
            'appetite': data['appetite'],
            'swelling': data.get('swelling', False),
            'body_part': data.get('body_part', ''),
            'note_text': data.get('note_text', ''),
            'risk_status': 'stable'  # Will be updated by risk engine
        }
        
        # Calculate risk score
        risk_data = risk_engine.calculate_risk_score(patient_id, log_data, recovery_profile)
        log_data['risk_status'] = risk_data['status']
        
        # Save risk score
        risk_engine.save_risk_score(patient_id, risk_data)
        
        # Create daily log
        log_id = firebase.create_daily_log(log_data)
        
        return jsonify({
            'message': 'Daily log created successfully',
            'log_id': log_id,
            'risk_status': risk_data['status'],
            'risk_score': risk_data['score'],
            'deviation_flag': risk_data['deviation_flag'],
            'complication_index': risk_data['complication_index']
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Failed to create daily log: {str(e)}'}), 500

@patient_bp.route('/my-logs', methods=['GET'])
@token_required
@role_required('patient')
def get_my_logs():
    """
    Get all daily logs for the current patient
    """
    try:
        patient_id = request.current_user['user_id']
        
        logs = firebase.get_patient_logs(patient_id)
        
        return jsonify({
            'logs': logs,
            'count': len(logs)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve logs: {str(e)}'}), 500

@patient_bp.route('/guidance', methods=['GET'])
@token_required
@role_required('patient')
def get_guidance():
    """
    Get stage-based adaptive recovery guidance
    """
    try:
        patient_id = request.current_user['user_id']
        
        # Get recovery profile
        recovery_profile = firebase.get_recovery_profile_by_patient(patient_id)
        if not recovery_profile:
            return jsonify({'error': 'Recovery profile not found'}), 404
        
        # Calculate days since start
        start_date_str = recovery_profile.get('start_date')
        if not start_date_str:
            return jsonify({'error': 'Start date not found in recovery profile'}), 400
        
        try:
            if isinstance(start_date_str, str):
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            else:
                start_date = start_date_str
            
            days_since_start = (datetime.now() - start_date.replace(tzinfo=None)).days
        except Exception as e:
            return jsonify({'error': f'Invalid start date format: {str(e)}'}), 400
        
        # Determine recovery stage
        if days_since_start <= 7:
            stage = "Week 1"
            guidance = {
                'stage': stage,
                'days_since_start': days_since_start,
                'focus': 'Rest and initial healing',
                'recommendations': [
                    'Take prescribed medications as directed',
                    'Rest the affected area',
                    'Apply ice if recommended',
                    'Monitor for signs of infection',
                    'Keep follow-up appointments'
                ],
                'acceptable_pain_range': f"0-{recovery_profile.get('acceptable_pain_week_1', 5)}",
                'warning_signs': [
                    'Severe pain (8+)',
                    'Signs of infection',
                    'Excessive swelling',
                    'Difficulty breathing'
                ]
            }
        elif days_since_start <= 21:
            stage = "Week 2-3"
            guidance = {
                'stage': stage,
                'days_since_start': days_since_start,
                'focus': 'Gradual activity increase',
                'recommendations': [
                    'Begin gentle exercises as recommended',
                    'Gradually increase activity level',
                    'Continue medication as needed',
                    'Monitor pain levels',
                    'Attend physical therapy if prescribed'
                ],
                'acceptable_pain_range': f"0-{recovery_profile.get('acceptable_pain_week_3', 4)}",
                'warning_signs': [
                    'Increasing pain trend',
                    'Pain exceeding acceptable range',
                    'Swelling that worsens',
                    'Limited mobility'
                ]
            }
        else:
            stage = "Week 4+"
            guidance = {
                'stage': stage,
                'days_since_start': days_since_start,
                'focus': 'Continued recovery and strength building',
                'recommendations': [
                    'Continue prescribed exercises',
                    'Gradually return to normal activities',
                    'Monitor for any complications',
                    'Follow up with doctor as scheduled',
                    'Report any concerns immediately'
                ],
                'acceptable_pain_range': '0-3',
                'warning_signs': [
                    'Persistent high pain',
                    'New symptoms',
                    'Complications',
                    'Regression in recovery'
                ]
            }
        
        # Get latest risk status
        latest_risk = firebase.get_latest_risk_score(patient_id)
        if latest_risk:
            guidance['current_risk_status'] = latest_risk.get('status', 'stable')
            guidance['risk_score'] = latest_risk.get('score', 0)
        
        return jsonify(guidance), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve guidance: {str(e)}'}), 500

