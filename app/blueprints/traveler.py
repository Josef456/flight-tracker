"""Traveler area: submit and track your own customs declarations.

Row-level access is enforced everywhere: a traveler can only ever read or touch
declarations whose traveler_id matches their own session user.
"""
from decimal import Decimal

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from sqlalchemy.orm import joinedload

from .. import db
from ..forms import DeclarationForm
from ..models import (
    Declaration,
    DeclarationItem,
    Flight,
    STATUS_PENDING,
)
from ..security import current_user, login_required, role_required
from ..models import ROLE_TRAVELER
from ..services import generate_reference, record_audit, score_risk

traveler_bp = Blueprint("traveler", __name__, url_prefix="/traveler")


@traveler_bp.route("/")
@role_required(ROLE_TRAVELER)
def dashboard():
    user = current_user()
    declarations = (
        Declaration.query.options(joinedload(Declaration.flight))
        .filter_by(traveler_id=user.id)
        .order_by(Declaration.created_at.desc())
        .all()
    )
    return render_template("traveler/dashboard.html", declarations=declarations)


@traveler_bp.route("/declare", methods=["GET", "POST"])
@role_required(ROLE_TRAVELER)
def declare():
    user = current_user()
    form = DeclarationForm()
    flights = Flight.query.order_by(Flight.scheduled_arrival.desc()).all()
    form.flight_id.choices = [
        (f.id, f"{f.flight_number}  {f.origin} to Entebbe") for f in flights
    ]

    if form.validate_on_submit():
        # Build items, keeping only the rows the traveler actually filled in.
        items = []
        total = Decimal("0")
        for entry in form.items.entries:
            desc = (entry.form.description.data or "").strip()
            if not desc:
                continue
            qty = entry.form.quantity.data or 1
            unit = Decimal(str(entry.form.unit_value.data or 0))
            items.append(
                DeclarationItem(
                    description=desc,
                    category=entry.form.category.data,
                    quantity=qty,
                    unit_value=unit,
                )
            )
            total += unit * qty

        if form.has_goods_to_declare.data and not items:
            flash("Add at least one item, or switch to 'nothing to declare'.", "error")
            return render_template("traveler/declare.html", form=form)

        declaration = Declaration(
            reference=generate_reference(),
            traveler_id=user.id,
            flight_id=form.flight_id.data,
            currency=form.currency.data,
            total_value=total,
            has_goods_to_declare=form.has_goods_to_declare.data,
            traveler_note=(form.traveler_note.data or "").strip() or None,
            status=STATUS_PENDING,
            items=items,
        )
        declaration.risk_level = score_risk(total, form.currency.data, items)
        db.session.add(declaration)
        db.session.flush()
        record_audit(declaration, user, "submitted",
                     f"{len(items)} item(s), {form.currency.data} {total:.2f}")
        db.session.commit()
        flash(f"Declaration {declaration.reference} submitted for clearance.", "success")
        return redirect(url_for("traveler.view", reference=declaration.reference))

    return render_template("traveler/declare.html", form=form)


@traveler_bp.route("/declaration/<reference>")
@login_required
def view(reference):
    declaration = (
        Declaration.query.options(
            joinedload(Declaration.flight),
            joinedload(Declaration.items),
            joinedload(Declaration.reviewer),
        )
        .filter_by(reference=reference)
        .first_or_404()
    )
    user = current_user()
    # A traveler may only open their own declaration.
    if user.role == ROLE_TRAVELER and declaration.traveler_id != user.id:
        abort(403)
    return render_template("traveler/detail.html", declaration=declaration)
