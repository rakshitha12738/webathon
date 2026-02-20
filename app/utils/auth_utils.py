"""
auth_utils.py – JWT token helpers and role-based route decorators.
"""

import functools
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from flask import current_app, jsonify, request

# --------------------------------------------------------------------------- #
# Token generation                                                              #
# --------------------------------------------------------------------------- #

def generate_token(user_id: str, role: str) -> str:
    """
    Create a signed JWT access token for *user_id* with the given *role*.

    The token carries:
      - sub  : user document id
      - role : "doctor" | "patient"
      - iat  : issued-at timestamp
      - exp  : expiry timestamp (configurable via JWT_EXPIRY_SECONDS)
    """
    expiry = datetime.now(tz=timezone.utc) + timedelta(
        seconds=current_app.config["JWT_EXPIRY_SECONDS"]
    )
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.now(tz=timezone.utc),
        "exp": expiry,
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


# --------------------------------------------------------------------------- #
# Token decoding                                                                #
# --------------------------------------------------------------------------- #

def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT *token*.

    Returns the decoded payload dict on success, or ``None`` on failure.
    """
    try:
        return jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _extract_bearer_token() -> Optional[str]:
    """Extract the raw token string from the *Authorization: Bearer <token>* header."""
    auth_header = request.headers.get("Authorization", "")
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# --------------------------------------------------------------------------- #
# Decorators                                                                   #
# --------------------------------------------------------------------------- #

def login_required(f):
    """
    Decorator – require a valid JWT in the *Authorization* header.

    Injects the decoded token payload as the keyword argument ``current_user``
    into the wrapped view function.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401
        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(*args, current_user=payload, **kwargs)

    return wrapper


def role_required(*roles):
    """
    Decorator factory – require the caller's role to be in *roles*.

    Must be applied **after** ``@login_required`` so that ``current_user``
    is already present.

    Usage::

        @bp.route("/admin")
        @login_required
        @role_required("doctor")
        def admin_view(current_user):
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user", {})
            if current_user.get("role") not in roles:
                return jsonify({"error": "Forbidden – insufficient role"}), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator
