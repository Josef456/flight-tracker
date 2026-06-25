"""Gunicorn entry point for cloud deploys.

Gunicorn's master process binds the listening socket *before* it imports this
module in a worker, so preparing the database here does not delay the port from
opening (which is what Render's port scan checks). The previous approach ran the
seed as a separate `bootstrap.py && gunicorn` step, which blocked the port from
ever opening while it waited on the database.

Seeding is idempotent: tables are created if missing and demo data is loaded only
when the database is empty, so ordinary restarts keep existing data.
"""
from app import create_app, db
from app.models import User
import seed

app = create_app()

with app.app_context():
    db.create_all()
    if User.query.count() == 0:
        print("Empty database detected, loading demo data...", flush=True)
        seed.build()
        print("Seed complete.", flush=True)
    else:
        print("Database already populated, skipping seed.", flush=True)
