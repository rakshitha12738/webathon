"""
risk_engine.py – Compute risk score and status from a patient's daily log.

Rules (in priority order):
  1. pain >= 8                                    → needs_review
  2. swelling == True AND pain >= 7              → high_risk
  3. Increasing pain trend over last 3 days      → monitor
  4. Pain exceeds acceptable range for the week  → deviation_flag = True

Complication Prediction Index:
  If deviation_flag AND swelling AND sleep_hours < 4 → complication_index = 35 %
  Otherwise                                          → complication_index = 0 %

The ``score`` field is a normalised float in [0, 1] representing overall risk.
"""

from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk(
    current_log: dict[str, Any],
    recent_logs: list[dict[str, Any]],
    recovery_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Evaluate the risk level for a single daily log entry.

    Parameters
    ----------
    current_log:
        The log entry just submitted by the patient.
        Expected keys: pain_level (int), swelling (bool), sleep_hours (float).
    recent_logs:
        The *previous* logs for this patient, ordered oldest → newest.
        Only the last 2 entries are used for trend detection.
    recovery_profile:
        The patient's recovery profile document.  Used to determine acceptable
        pain ranges per week.  If ``None``, week-range deviation is skipped.

    Returns
    -------
    dict with keys:
        score            float  normalised risk in [0, 1]
        status           str    "stable" | "monitor" | "needs_review" | "high_risk"
        deviation_flag   bool
        complication_index str  e.g. "35%" or "0%"
    """
    pain: int = int(current_log.get("pain_level", 0))
    swelling: bool = bool(current_log.get("swelling", False))
    sleep_hours: float = float(current_log.get("sleep_hours", 8.0))

    status = "stable"
    deviation_flag = False

    # ── Rule 1: high absolute pain ───────────────────────────────────────────
    if pain >= 8:
        status = "needs_review"

    # ── Rule 2: swelling + high pain (overrides rule 1) ─────────────────────
    if swelling and pain >= 7:
        status = "high_risk"

    # ── Rule 3: increasing pain trend over 3 consecutive days ───────────────
    # We need at least 2 previous logs plus the current one to form a trend.
    if len(recent_logs) >= 2 and status not in ("high_risk", "needs_review"):
        prev_two = recent_logs[-2:]  # [older, newer]
        older_pain = int(prev_two[0].get("pain_level", 0))
        newer_pain = int(prev_two[1].get("pain_level", 0))
        if older_pain < newer_pain < pain:
            status = "monitor"

    # ── Rule 4: deviation from acceptable weekly pain range ──────────────────
    if recovery_profile:
        deviation_flag = _check_pain_deviation(
            pain, current_log, recovery_profile
        )

    # ── Complication Prediction Index ────────────────────────────────────────
    if deviation_flag and swelling and sleep_hours < 4:
        complication_index = "35%"
    else:
        complication_index = "0%"

    # ── Normalised score ─────────────────────────────────────────────────────
    score = _compute_score(status, pain, deviation_flag)

    return {
        "score": round(score, 3),
        "status": status,
        "deviation_flag": deviation_flag,
        "complication_index": complication_index,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check_pain_deviation(
    pain: int,
    current_log: dict[str, Any],
    recovery_profile: dict[str, Any],
) -> bool:
    """
    Return True if *pain* exceeds the acceptable threshold for the current
    recovery week as defined in *recovery_profile*.

    The profile carries:
      - start_date               : ISO-8601 date string ("YYYY-MM-DD")
      - acceptable_pain_week_1   : int – max acceptable pain in week 1
      - acceptable_pain_week_3   : int – max acceptable pain from week 3 onward
    """
    from datetime import date

    start_date_raw = recovery_profile.get("start_date")
    if not start_date_raw:
        return False

    try:
        if hasattr(start_date_raw, "date"):
            # Firestore Timestamp / datetime object
            start = start_date_raw.date()
        else:
            start = date.fromisoformat(str(start_date_raw))
    except (ValueError, AttributeError):
        return False

    log_date_raw = current_log.get("date")
    try:
        if hasattr(log_date_raw, "date"):
            log_date = log_date_raw.date()
        elif log_date_raw:
            log_date = date.fromisoformat(str(log_date_raw))
        else:
            log_date = date.today()
    except (ValueError, AttributeError):
        log_date = date.today()

    days_elapsed = (log_date - start).days
    week = days_elapsed // 7 + 1  # week number starting at 1

    if week <= 1:
        threshold = int(recovery_profile.get("acceptable_pain_week_1", 10))
    elif week <= 3:
        # Linear interpolation between week-1 and week-3 thresholds
        w1 = int(recovery_profile.get("acceptable_pain_week_1", 10))
        w3 = int(recovery_profile.get("acceptable_pain_week_3", 10))
        threshold = round(w1 + (w3 - w1) * ((week - 1) / 2))
    else:
        threshold = int(recovery_profile.get("acceptable_pain_week_3", 10))

    return pain > threshold


def _compute_score(status: str, pain: int, deviation_flag: bool) -> float:
    """
    Map qualitative risk *status* to a normalised score in [0, 1].

    The score blends the categorical status with a pain contribution and
    a small deviation penalty.
    """
    base = {
        "stable": 0.1,
        "monitor": 0.4,
        "needs_review": 0.7,
        "high_risk": 0.9,
    }.get(status, 0.1)

    # Pain contribution: pain/10 scaled to at most 0.1 extra
    pain_contrib = (pain / 10.0) * 0.1

    # Deviation adds a small penalty
    deviation_contrib = 0.05 if deviation_flag else 0.0

    return min(1.0, base + pain_contrib + deviation_contrib)
