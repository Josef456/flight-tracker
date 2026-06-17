"""Supervisor area: analytics dashboard, flight roster, and user management."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db
from ..forms import FlightForm, UserAdminForm
from ..models import Flight, ROLES, User
from ..queries import (
    kpi_summary,
    recent_audit,
    risk_breakdown,
    status_breakdown,
    top_flights,
)
from ..security import admin_required, current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        kpis=kpi_summary(),
        status=status_breakdown(),
        risk=risk_breakdown(),
        top=top_flights(),
        audit=recent_audit(),
    )


@admin_bp.route("/flights", methods=["GET", "POST"])
@admin_required
def flights():
    form = FlightForm()
    if form.validate_on_submit():
        existing = Flight.query.filter_by(
            flight_number=form.flight_number.data.strip().upper()
        ).first()
        if existing:
            flash("That flight number already exists.", "error")
        else:
            arrival = None
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
                try:
                    arrival = datetime.strptime(form.scheduled_arrival.data.strip(), fmt)
                    break
                except ValueError:
                    continue
            if arrival is None:
                flash("Use an arrival format like 2026-06-26 14:30.", "error")
            else:
                db.session.add(
                    Flight(
                        flight_number=form.flight_number.data.strip().upper(),
                        airline=form.airline.data.strip(),
                        origin=form.origin.data.strip(),
                        origin_code=(form.origin_code.data or "").strip().upper() or None,
                        scheduled_arrival=arrival,
                    )
                )
                db.session.commit()
                flash("Flight added to the roster.", "success")
                return redirect(url_for("admin.flights"))

    roster = Flight.query.order_by(Flight.scheduled_arrival.desc()).all()
    return render_template("admin/flights.html", form=form, flights=roster)


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    form = UserAdminForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        elif not form.password.data:
            flash("Set an initial password for the new account.", "error")
        elif form.role.data not in ROLES:
            flash("Unknown role.", "error")
        else:
            user = User(
                full_name=form.full_name.data.strip(),
                email=email,
                role=form.role.data,
                is_active=form.is_active.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f"{user.full_name} added as {user.role}.", "success")
            return redirect(url_for("admin.users"))

    people = User.query.order_by(User.role, User.full_name).all()
    return render_template("admin/users.html", form=form, people=people)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user().id:
        flash("You cannot deactivate your own account.", "error")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(
            f"{user.full_name} is now {'active' if user.is_active else 'inactive'}.",
            "success",
        )
    return redirect(url_for("admin.users"))
