"""Application configuration.

Settings are read from environment variables where available so the same code
runs on localhost and on a cloud host (Render, Vercel) without edits. Sensible
local defaults are provided for development.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Used to sign session cookies and CSRF tokens. Override in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-entebbe-customs-key-change-me")

    # SQLite for local development. Point DATABASE_URL at Postgres/MySQL in cloud.
    _db_url = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'instance' / 'customs.db'}"
    # Render and some hosts hand out the legacy "postgres://" scheme, which
    # SQLAlchemy 2.x no longer accepts. Normalise it to "postgresql://".
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session hardening.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to True behind HTTPS in production.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    WTF_CSRF_TIME_LIMIT = None
