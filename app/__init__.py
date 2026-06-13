"""Application factory for the Entebbe Flight Tracker.

A small MVC layout:
  * Models  -> app/models.py (SQLAlchemy ORM)
  * Views   -> app/templates/*.html (Jinja2)
  * Control -> app/blueprints/*.py (request handling, one blueprint per concern)
"""
from pathlib import Path

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure the SQLite folder exists before the engine connects.
    Path(app.root_path).parent.joinpath("instance").mkdir(exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    # Blueprints (controllers).
    from .blueprints.auth import auth_bp
    from .blueprints.traveler import traveler_bp
    from .blueprints.inspector import inspector_bp
    from .blueprints.admin import admin_bp
    from .blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(traveler_bp)
    app.register_blueprint(inspector_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    from .security import current_user, role_label

    @app.context_processor
    def inject_user():
        # Available in every template without passing it from each view.
        return {"current_user": current_user(), "role_label": role_label}

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403,
                               message="You do not have access to that page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404,
                               message="That page could not be found."), 404

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
