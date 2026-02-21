"""
Flask application initialization
"""
from flask import Flask
from flask_cors import CORS
from app.utils.config import Config

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.patient import patient_bp
    from app.routes.doctor import doctor_bp
    from app.routes.rag import rag_bp
    from app.routes.community import community_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
    app.register_blueprint(rag_bp, url_prefix='/api/rag')
    app.register_blueprint(community_bp, url_prefix='/api/community')
    
    return app

