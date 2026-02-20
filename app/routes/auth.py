"""
Authentication routes
"""
from flask import Blueprint, request, jsonify
from app.services.firebase_service import FirebaseService
from app.utils.auth_utils import hash_password, verify_password, generate_token

auth_bp = Blueprint('auth', __name__)
firebase = FirebaseService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    
    Expected JSON:
    {
        "name": "string",
        "email": "string",
        "password": "string",
        "role": "doctor" | "patient",
        "assigned_doctor_id": "string" (optional, for patients)
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'password', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate role
        if data['role'] not in ['doctor', 'patient']:
            return jsonify({'error': 'Role must be either "doctor" or "patient"'}), 400
        
        # Check if email already exists
        existing_user = firebase.get_user_by_email(data['email'])
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409
        
        # Hash password
        hashed_password = hash_password(data['password'])
        
        # Create user data
        user_data = {
            'name': data['name'],
            'email': data['email'],
            'password': hashed_password,
            'role': data['role'],
            'assigned_doctor_id': data.get('assigned_doctor_id')
        }
        
        # Create user in Firestore
        user_id = firebase.create_user(user_data)
        
        # Generate token
        token = generate_token(user_id, data['role'])
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'token': token,
            'role': data['role']
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user
    
    Expected JSON:
    {
        "email": "string",
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Get user by email
        user = firebase.get_user_by_email(data['email'])
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Verify password
        if not verify_password(data['password'], user['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Generate token
        token = generate_token(user['id'], user['role'])
        
        return jsonify({
            'message': 'Login successful',
            'user_id': user['id'],
            'token': token,
            'role': user['role'],
            'name': user['name']
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

