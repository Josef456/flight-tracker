"""Domain logic shared by the controllers."""
from datetime import datetime, timezone

from . import db
from .models import AuditLog, Declaration, RISK_HIGH, RISK_LOW, RISK_MEDIUM


# Categories that always warrant a closer look at the border.
_SENSITIVE_CATEGORIES = {"currency", "medical", "commercial"}


def generate_reference():
    """Human-readable, unique declaration reference, e.g. EBB-7F3A2C."""
    import secrets

    while True:
        ref = "EBB-" + secrets.token_hex(3).upper()
        if not Declaration.query.filter_by(reference=ref).first():
            return ref


def score_risk(total_value, currency, items):
    """Deterministic risk score used to pre-sort the inspector queue.

    Travelers never set their own risk level; the system computes it from the
    declared value and the categories present so the rating cannot be gamed.
    """
    value = float(total_value or 0)
    categories = {getattr(i, "category", None) for i in items}

    # Rough USD-equivalent threshold; UGX amounts are far larger per unit.
    high_threshold = 10000 if currency != "UGX" else 35000000
    medium_threshold = 2000 if currency != "UGX" else 7000000

    if value >= high_threshold or categories & _SENSITIVE_CATEGORIES:
        if value >= high_threshold and categories & _SENSITIVE_CATEGORIES:
            return RISK_HIGH
        return RISK_HIGH if value >= high_threshold else RISK_MEDIUM
    if value >= medium_threshold:
        return RISK_MEDIUM
    return RISK_LOW


def record_audit(declaration, actor, action, detail=None):
    entry = AuditLog(
        declaration_id=declaration.id,
        actor_id=actor.id,
        action=action,
        detail=detail,
    )
    db.session.add(entry)
    return entry


def utcnow():
    return datetime.now(timezone.utc)
