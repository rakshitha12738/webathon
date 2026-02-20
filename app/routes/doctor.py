"""
doctor.py – Doctor-facing endpoints.

Endpoints
---------
GET /doctor/patients                    List all assigned patients with latest risk
GET /doctor/patient/<patient_id>        Full patient detail (profile, logs, risk)
"""

import logging

from flask import Blueprint, jsonify

from app.services.firebase_service import get_db
from app.utils.auth_utils import login_required, role_required

logger = logging.getLogger(__name__)
bp = Blueprint("doctor", __name__, url_prefix="/doctor")


# ─────────────────────────────────────────────────────────────────────────────
# GET /doctor/patients
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/patients", methods=["GET"])
@login_required
@role_required("doctor")
def get_patients(current_user):
    """
    Return all patients assigned to the authenticated doctor along with their
    latest risk status.

    Returns
    -------
    200  { patients: [ { ...user, latest_risk_status } ] }
    500  { error }
    """
    doctor_id = current_user["sub"]

    try:
        db = get_db()

        # Fetch all patients assigned to this doctor
        patient_docs = (
            db.collection("users")
            .where("role", "==", "patient")
            .where("assigned_doctor_id", "==", doctor_id)
            .get()
        )

        result = []
        for doc in patient_docs:
            patient = doc.to_dict()
            patient.pop("password", None)  # never expose hashed password

            # Latest risk score
            risk_docs = (
                db.collection("risk_scores")
                .where("patient_id", "==", patient["id"])
                .order_by("created_at")
                .limit_to_last(1)
                .get()
            )
            latest_risk = risk_docs[0].to_dict() if risk_docs else {}

            patient["latest_risk_status"] = latest_risk.get("status", "unknown")
            result.append(patient)

        return jsonify({"patients": result}), 200

    except Exception as exc:
        logger.exception("Failed to fetch patients for doctor %s", doctor_id)
        return jsonify({"error": "Failed to retrieve patients", "detail": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /doctor/patient/<patient_id>
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/patient/<patient_id>", methods=["GET"])
@login_required
@role_required("doctor")
def get_patient_detail(patient_id, current_user):
    """
    Return the full profile for a specific patient.

    Includes:
      - User info (no password)
      - Recovery profile
      - All daily logs (ordered by date)
      - Latest risk score & complication index

    Returns
    -------
    200  { patient, recovery_profile, logs, risk_score }
    403  { error }  if patient is not assigned to this doctor
    404  { error }  if patient not found
    500  { error }
    """
    doctor_id = current_user["sub"]

    try:
        db = get_db()

        # ── Fetch patient user doc ───────────────────────────────────────────
        patient_doc = db.collection("users").document(patient_id).get()
        if not patient_doc.exists:
            return jsonify({"error": "Patient not found"}), 404

        patient = patient_doc.to_dict()
        patient.pop("password", None)

        # ── Authorisation: ensure patient is assigned to this doctor ─────────
        if patient.get("assigned_doctor_id") != doctor_id:
            return jsonify({"error": "This patient is not assigned to you"}), 403

        # ── Recovery profile ─────────────────────────────────────────────────
        profile_docs = (
            db.collection("recovery_profiles")
            .where("patient_id", "==", patient_id)
            .limit(1)
            .get()
        )
        recovery_profile = profile_docs[0].to_dict() if profile_docs else {}

        # ── All daily logs ───────────────────────────────────────────────────
        log_docs = (
            db.collection("daily_logs")
            .where("patient_id", "==", patient_id)
            .order_by("date")
            .get()
        )
        logs = [d.to_dict() for d in log_docs]

        # ── Latest risk score ────────────────────────────────────────────────
        risk_docs = (
            db.collection("risk_scores")
            .where("patient_id", "==", patient_id)
            .order_by("created_at")
            .limit_to_last(1)
            .get()
        )
        risk_score = risk_docs[0].to_dict() if risk_docs else {}

        return jsonify(
            {
                "patient": patient,
                "recovery_profile": recovery_profile,
                "logs": logs,
                "risk_score": risk_score,
            }
        ), 200

    except Exception as exc:
        logger.exception(
            "Failed to fetch patient detail for patient %s (doctor %s)",
            patient_id,
            doctor_id,
        )
        return jsonify({"error": "Failed to retrieve patient detail", "detail": str(exc)}), 500
