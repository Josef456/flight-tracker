"""Customs inspector area: the audit queue, filters, and review actions."""
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload

from .. import db
from ..forms import ReviewForm
from ..models import (
    Declaration,
    Flight,
    RISK_LEVELS,
    STATUS_CLEARED,
    STATUS_FLAGGED,
    STATUS_INSPECTED,
    STATUSES,
)
from ..queries import declarations_query
from ..security import current_user, inspector_required
from ..services import record_audit, utcnow

inspector_bp = Blueprint("inspector", __name__, url_prefix="/inspector")

_DECISION_STATUS = {
    "cleared": STATUS_CLEARED,
    "flagged": STATUS_FLAGGED,
    "inspected": STATUS_INSPECTED,
}


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


@inspector_bp.route("/")
@inspector_required
def queue():
    # Inspector audit filters: status, risk, flight, free-text search, date range.
    filters = {
        "status": request.args.get("status", "").strip() or None,
        "risk": request.args.get("risk", "").strip() or None,
        "flight_id": request.args.get("flight_id", type=int),
        "search": request.args.get("search", "").strip() or None,
        "date_from": _parse_date(request.args.get("date_from")),
        "date_to": _parse_date(request.args.get("date_to")),
    }
    # Drop filter values that are not in the allowed sets.
    if filters["status"] not in STATUSES:
        filters["status"] = None
    if filters["risk"] not in RISK_LEVELS:
        filters["risk"] = None

    declarations = declarations_query(filters).limit(200).all()
    flights = Flight.query.order_by(Flight.scheduled_arrival.desc()).all()
    return render_template(
        "inspector/queue.html",
        declarations=declarations,
        flights=flights,
        filters=filters,
        statuses=STATUSES,
        risk_levels=RISK_LEVELS,
        raw_args=request.args,
    )


@inspector_bp.route("/arrivals")
@inspector_required
def arrivals():
    flights = Flight.query.order_by(Flight.scheduled_arrival.desc()).all()
    return render_template("inspector/arrivals.html", flights=flights)


@inspector_bp.route("/declaration/<reference>", methods=["GET", "POST"])
@inspector_required
def review(reference):
    declaration = (
        Declaration.query.options(
            joinedload(Declaration.traveler),
            joinedload(Declaration.flight),
            joinedload(Declaration.items),
            joinedload(Declaration.reviewer),
        )
        .filter_by(reference=reference)
        .first_or_404()
    )
    form = ReviewForm(risk_level=declaration.risk_level)

    if form.validate_on_submit():
        new_status = _DECISION_STATUS.get(form.decision.data)
        if new_status is None:
            abort(400)
        user = current_user()
        declaration.status = new_status
        declaration.risk_level = form.risk_level.data
        declaration.inspector_note = (form.inspector_note.data or "").strip() or None
        declaration.reviewed_by_id = user.id
        declaration.reviewed_at = utcnow()
        record_audit(
            declaration, user, new_status,
            f"risk={form.risk_level.data}" + (
                f"; {declaration.inspector_note}" if declaration.inspector_note else ""
            ),
        )
        db.session.commit()
        flash(f"Declaration {declaration.reference} marked {new_status}.", "success")
        return redirect(url_for("inspector.review", reference=reference))

    return render_template("inspector/review.html", declaration=declaration, form=form)
