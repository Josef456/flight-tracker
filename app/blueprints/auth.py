"""Authentication: registration, login, logout.

New self-service registrations are always travelers. Inspector and supervisor
accounts are created by a supervisor from the admin area, so a privileged role
can never be granted from the public form.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db
from ..forms import LoginForm, RegisterForm
from ..models import ROLE_TRAVELER, User
from ..security import current_user, login_user, logout_user

auth_bp = Blueprint("auth", __name__)


def _home_for(user):
    return {
        "admin": "admin.dashboard",
        "inspector": "inspector.queue",
        "traveler": "traveler.dashboard",
    }.get(user.role, "traveler.dashboard")


@auth_bp.route("/")
def index():
    user = current_user()
    if user:
        return redirect(url_for(_home_for(user)))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for(_home_for(current_user())))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        # Constant work whether or not the email exists; generic error message.
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.full_name.split()[0]}.", "success")
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/"):
                return redirect(nxt)
            return redirect(url_for(_home_for(user)))
        flash("Those credentials did not match our records.", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for(_home_for(current_user())))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(
                full_name=form.full_name.data.strip(),
                email=email,
                role=ROLE_TRAVELER,
                passport_no=(form.passport_no.data or "").strip() or None,
                nationality=(form.nationality.data or "").strip() or None,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Your traveler account is ready.", "success")
            return redirect(url_for("traveler.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
