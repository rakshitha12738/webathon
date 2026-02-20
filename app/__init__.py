"""
app/__init__.py – Flask application factory.

Usage::

    from app import create_app
    app = create_app()
"""

import logging

from flask import Flask
from flask_cors import CORS

from app.utils.config import Config


def create_app(config_class: type = Config) -> Flask:
    """
    Create and configure the Flask application.

    Parameters
    ----------
    config_class:
        Configuration class to load settings from.  Defaults to
        :class:`app.utils.config.Config`.

    Returns
    -------
    Flask
        Configured Flask application instance ready to be served.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Expose the config object directly so services can access typed attributes
    app.config["APP_CONFIG"] = config_class()

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins_raw = config_class.CORS_ORIGINS
    cors_origins = (
        [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
        if cors_origins_raw != "*"
        else "*"
    )
    CORS(app, resources={r"/*": {"origins": cors_origins}})

    # ── Logging ──────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.DEBUG if app.config["DEBUG"] else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s – %(message)s",
    )

    # Warn loudly when running with the default insecure secret key
    if app.config["SECRET_KEY"] == "change-me-in-production":
        app.logger.warning(
            "SECRET_KEY is set to the insecure default value. "
            "Set the SECRET_KEY environment variable before deploying."
        )

    # ── Firebase ─────────────────────────────────────────────────────────────
    _init_firebase(app)

    # ── Qdrant collection bootstrap ──────────────────────────────────────────
    _init_qdrant(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.auth import bp as auth_bp
    from app.routes.patient import bp as patient_bp
    from app.routes.doctor import bp as doctor_bp
    from app.routes.rag import bp as rag_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(rag_bp)

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _init_firebase(app: Flask) -> None:
    """Initialise the Firebase Admin SDK; log a warning on failure."""
    from app.services.firebase_service import init_firebase

    try:
        init_firebase(
            credentials_path=app.config["FIREBASE_CREDENTIALS_PATH"],
            storage_bucket=app.config["FIREBASE_STORAGE_BUCKET"],
        )
    except FileNotFoundError as exc:
        app.logger.warning(
            "Firebase not initialised: %s. "
            "Set FIREBASE_CREDENTIALS_PATH to a valid serviceAccountKey.json.",
            exc,
        )
    except Exception as exc:
        app.logger.error("Firebase initialisation failed: %s", exc)


def _init_qdrant(app: Flask) -> None:
    """Bootstrap the Qdrant collection; log a warning on failure."""
    from app.services.rag_service import ensure_collection

    cfg: Config = app.config["APP_CONFIG"]
    try:
        ensure_collection(
            host=cfg.QDRANT_HOST,
            port=cfg.QDRANT_PORT,
            collection=cfg.QDRANT_COLLECTION,
            vector_size=cfg.QDRANT_VECTOR_SIZE,
        )
    except Exception as exc:
        app.logger.warning(
            "Qdrant not available at %s:%s – RAG features will be unavailable. Error: %s",
            cfg.QDRANT_HOST,
            cfg.QDRANT_PORT,
            exc,
        )
