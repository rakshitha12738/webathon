"""
patient.py – Patient-facing endpoints.

Endpoints
---------
POST /patient/daily-log    Submit a daily health log
GET  /patient/my-logs      Retrieve own log history
GET  /patient/guidance     Get stage-based recovery guidance
"""

import logging
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from app.services.firebase_service import get_db
from app.services.risk_engine import compute_risk
from app.utils.auth_utils import login_required, role_required

logger = logging.getLogger(__name__)
bp = Blueprint("patient", __name__, url_prefix="/patient")

# Valid ranges for scored fields
_MIN_SCORE = 0
_MAX_SCORE = 10


# ─────────────────────────────────────────────────────────────────────────────
# POST /patient/daily-log
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/daily-log", methods=["POST"])
@login_required
@role_required("patient")
def submit_daily_log(current_user):
    """
    Submit a daily health log and receive a computed risk assessment.

    Request body (JSON)
    -------------------
    pain_level  : int   0–10
    mood_level  : int   0–10
    sleep_hours : float
    appetite    : str   e.g. "good" | "poor" | "normal"
    swelling    : bool
    body_part   : str
    note_text   : str   (optional free-text note)

    Returns
    -------
    201  { message, log_id, risk }
    400  { error }
    500  { error }
    """
    data = request.get_json(silent=True) or {}
    patient_id = current_user["sub"]

    # ── Validate required fields ─────────────────────────────────────────────
    required = ["pain_level", "mood_level", "sleep_hours", "appetite", "swelling", "body_part"]
    missing = [f for f in required if data.get(f) is None]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        pain_level = int(data["pain_level"])
        mood_level = int(data["mood_level"])
        sleep_hours = float(data["sleep_hours"])
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid numeric value: {exc}"}), 400

    if not (_MIN_SCORE <= pain_level <= _MAX_SCORE) or not (_MIN_SCORE <= mood_level <= _MAX_SCORE):
        return jsonify({"error": f"pain_level and mood_level must be between {_MIN_SCORE} and {_MAX_SCORE}"}), 400

    today_str = date.today().isoformat()

    try:
        db = get_db()

        # ── Fetch recovery profile ───────────────────────────────────────────
        profiles = (
            db.collection("recovery_profiles")
            .where("patient_id", "==", patient_id)
            .limit(1)
            .get()
        )
        recovery_profile = profiles[0].to_dict() if profiles else None

        # ── Fetch last 2 logs for trend analysis ────────────────────────────
        recent_docs = (
            db.collection("daily_logs")
            .where("patient_id", "==", patient_id)
            .order_by("date")
            .limit_to_last(2)
            .get()
        )
        recent_logs = [d.to_dict() for d in recent_docs]

        current_log_data = {
            "pain_level": pain_level,
            "swelling": bool(data["swelling"]),
            "sleep_hours": sleep_hours,
            "date": today_str,
        }

        # ── Risk engine ──────────────────────────────────────────────────────
        risk = compute_risk(current_log_data, recent_logs, recovery_profile)

        # ── Persist log ──────────────────────────────────────────────────────
        log_ref = db.collection("daily_logs").document()
        log_data = {
            "id": log_ref.id,
            "patient_id": patient_id,
            "date": today_str,
            "pain_level": pain_level,
            "mood_level": mood_level,
            "sleep_hours": sleep_hours,
            "appetite": data["appetite"],
            "swelling": bool(data["swelling"]),
            "body_part": data["body_part"],
            "note_text": data.get("note_text", ""),
            "risk_status": risk["status"],
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        log_ref.set(log_data)

        # ── Persist risk score ───────────────────────────────────────────────
        risk_ref = db.collection("risk_scores").document()
        risk_ref.set(
            {
                "id": risk_ref.id,
                "patient_id": patient_id,
                "log_id": log_ref.id,
                "score": risk["score"],
                "status": risk["status"],
                "deviation_flag": risk["deviation_flag"],
                "complication_index": risk["complication_index"],
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )

        return jsonify({"message": "Log submitted", "log_id": log_ref.id, "risk": risk}), 201

    except Exception as exc:
        logger.exception("Failed to submit daily log for patient %s", patient_id)
        return jsonify({"error": "Failed to submit log", "detail": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /patient/my-logs
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/my-logs", methods=["GET"])
@login_required
@role_required("patient")
def get_my_logs(current_user):
    """
    Return all daily logs for the authenticated patient.

    Returns
    -------
    200  { logs: [...] }
    500  { error }
    """
    patient_id = current_user["sub"]

    try:
        db = get_db()
        logs_docs = (
            db.collection("daily_logs")
            .where("patient_id", "==", patient_id)
            .order_by("date")
            .get()
        )
        logs = [doc.to_dict() for doc in logs_docs]
        return jsonify({"logs": logs}), 200

    except Exception as exc:
        logger.exception("Failed to retrieve logs for patient %s", patient_id)
        return jsonify({"error": "Failed to retrieve logs", "detail": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /patient/guidance
# ─────────────────────────────────────────────────────────────────────────────

# Stage-based recovery advice keyed by week buckets
_GUIDANCE: dict[str, dict] = {
    "week_1": {
        "stage": "Early Recovery",
        "focus": "Rest and wound care",
        "tips": [
            "Keep the affected area elevated to reduce swelling.",
            "Take prescribed medications on schedule.",
            "Do not strain yourself – minimal movement only.",
            "Report any pain above 7 or unexpected swelling immediately.",
        ],
        "exercise": "Gentle breathing exercises and light walking (5 min/day).",
    },
    "week_2_3": {
        "stage": "Active Recovery",
        "focus": "Light mobility and nutrition",
        "tips": [
            "Begin gentle physiotherapy exercises as prescribed.",
            "Maintain a protein-rich diet to support tissue repair.",
            "Track pain and sleep daily.",
            "Attend any scheduled follow-up appointments.",
        ],
        "exercise": "Short walks (10–15 min twice daily) and stretching.",
    },
    "week_4_plus": {
        "stage": "Rehabilitation",
        "focus": "Strength and return to routine",
        "tips": [
            "Gradually increase activity levels.",
            "Discuss return-to-work or exercise plans with your doctor.",
            "Monitor for any unusual pain or fatigue.",
        ],
        "exercise": "Physiotherapy programme as directed by your care team.",
    },
}


@bp.route("/guidance", methods=["GET"])
@login_required
@role_required("patient")
def get_guidance(current_user):
    """
    Return stage-based adaptive guidance based on days since recovery start.

    Returns
    -------
    200  { stage, days_since_start, guidance }
    404  { error }  if no recovery profile exists
    500  { error }
    """
    patient_id = current_user["sub"]

    try:
        db = get_db()
        profiles = (
            db.collection("recovery_profiles")
            .where("patient_id", "==", patient_id)
            .limit(1)
            .get()
        )

        if not profiles:
            return jsonify({"error": "No recovery profile found for this patient"}), 404

        profile = profiles[0].to_dict()
        start_date_raw = profile.get("start_date")

        if not start_date_raw:
            return jsonify({"error": "Recovery start date is not set"}), 400

        # Parse start_date (supports both Firestore Timestamp and ISO string)
        if hasattr(start_date_raw, "date"):
            start = start_date_raw.date()
        else:
            start = date.fromisoformat(str(start_date_raw))

        days_since_start = (date.today() - start).days

        # Select guidance bucket
        if days_since_start <= 7:
            guidance = _GUIDANCE["week_1"]
        elif days_since_start <= 21:
            guidance = _GUIDANCE["week_2_3"]
        else:
            guidance = _GUIDANCE["week_4_plus"]

        return jsonify(
            {
                "days_since_start": days_since_start,
                "expected_duration_days": profile.get("expected_duration_days"),
                "condition_type": profile.get("condition_type"),
                "guidance": guidance,
            }
        ), 200

    except Exception as exc:
        logger.exception("Failed to get guidance for patient %s", patient_id)
        return jsonify({"error": "Failed to retrieve guidance", "detail": str(exc)}), 500
