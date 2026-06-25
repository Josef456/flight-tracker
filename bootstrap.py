"""Idempotent startup bootstrap for cloud deploys (Render free tier).

Render ignores the Procfile when a render.yaml blueprint is present, and
pre-deploy commands are a paid feature, so the database is never prepared by
those paths. This script runs before gunicorn in the start command:

  * create any missing tables, and
  * load demo data only when the database is empty.

Because seeding is guarded on an empty database, ordinary restarts (free
instances sleep after inactivity and cold-start later) keep existing data
instead of wiping it. seed.py is still the tool for a deliberate full reset.
"""
from app import create_app, db
from app.models import User
import seed

app = create_app()
with app.app_context():
    db.create_all()
    if User.query.count() == 0:
        print("Empty database detected, loading demo data...")
        seed.build()
    else:
        print("Database already populated, skipping seed.")
