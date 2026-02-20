"""
auth.py – Authentication routes: register and login.

Endpoints
---------
POST /auth/register   Create a new user account
POST /auth/login      Authenticate and receive a JWT
"""

import logging

import bcrypt
from flask import Blueprint, jsonify, request

from app.services.firebase_service import get_db
from app.utils.auth_utils import generate_token

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/register
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.

    Request body (JSON)
    -------------------
    name              : str   – display name
    email             : str   – unique email address
    password          : str   – plain-text password (hashed before storage)
    role              : str   – "doctor" | "patient"
    assigned_doctor_id: str   – (optional) only relevant for patients

    Returns
    -------
    201  { message, user_id }
    400  { error }  on validation failure
    409  { error }  if email already registered
    500  { error }  on unexpected server error
    """
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "").strip().lower()
    assigned_doctor_id = data.get("assigned_doctor_id", "")

    # ── Validate inputs ──────────────────────────────────────────────────────
    if not all([name, email, password, role]):
        return jsonify({"error": "name, email, password, and role are required"}), 400

    if role not in ("doctor", "patient"):
        return jsonify({"error": "role must be 'doctor' or 'patient'"}), 400

    try:
        db = get_db()

        # Check uniqueness
        existing = db.collection("users").where("email", "==", email).limit(1).get()
        if existing:
            return jsonify({"error": "Email is already registered"}), 409

        # Hash the password
        hashed_pw = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Persist the user document
        user_ref = db.collection("users").document()
        user_ref.set(
            {
                "id": user_ref.id,
                "name": name,
                "email": email,
                "password": hashed_pw,
                "role": role,
                "assigned_doctor_id": assigned_doctor_id,
            }
        )

        logger.info("New user registered: %s (%s)", email, role)
        return jsonify({"message": "User registered successfully", "user_id": user_ref.id}), 201

    except Exception as exc:
        logger.exception("Registration failed for %s", email)
        return jsonify({"error": "Registration failed", "detail": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate an existing user.

    Request body (JSON)
    -------------------
    email    : str
    password : str

    Returns
    -------
    200  { message, token, user_id, role }
    400  { error }  on missing fields
    401  { error }  on invalid credentials
    500  { error }  on unexpected server error
    """
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        db = get_db()
        users = db.collection("users").where("email", "==", email).limit(1).get()

        if not users:
            return jsonify({"error": "Invalid email or password"}), 401

        user_doc = users[0].to_dict()

        if not bcrypt.checkpw(
            password.encode("utf-8"), user_doc["password"].encode("utf-8")
        ):
            return jsonify({"error": "Invalid email or password"}), 401

        token = generate_token(user_doc["id"], user_doc["role"])

        logger.info("User logged in: %s", email)
        return jsonify(
            {
                "message": "Login successful",
                "token": token,
                "user_id": user_doc["id"],
                "role": user_doc["role"],
            }
        ), 200

    except Exception as exc:
        logger.exception("Login failed for %s", email)
        return jsonify({"error": "Login failed", "detail": str(exc)}), 500
