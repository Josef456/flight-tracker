"""Authentication helpers and the role-based access control (RBAC) layer.

Access is enforced server side on every protected route through decorators.
The session only ever stores the user id; the user record is reloaded from the
database on each request so a deactivated account loses access immediately.
"""
from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from .models import User, ROLE_ADMIN, ROLE_INSPECTOR, ROLE_TRAVELER

_ROLE_LABELS = {
    ROLE_TRAVELER: "Traveler",
    ROLE_INSPECTOR: "Customs Inspector",
    ROLE_ADMIN: "Supervisor",
}


def role_label(role):
    return _ROLE_LABELS.get(role, role.title() if role else "")


def login_user(user):
    session.clear()
    session["user_id"] = user.id


def logout_user():
    session.clear()


def current_user():
    """Return the logged-in User for this request, cached on flask.g."""
    if "user" in g:
        return g.user
    user_id = session.get("user_id")
    user = None
    if user_id is not None:
        user = User.query.get(user_id)
        if user is not None and not user.is_active:
            user = None
    g.user = user
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    """Allow the view only for the listed roles. 403 otherwise."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return redirect(url_for("auth.login", next=request.path))
            if user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


# Convenience shortcuts.
def admin_required(view):
    return role_required(ROLE_ADMIN)(view)


def inspector_required(view):
    return role_required(ROLE_INSPECTOR, ROLE_ADMIN)(view)
