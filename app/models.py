"""Database models for the Entebbe Flight Tracker customs system.

Relational design notes
-----------------------
* Every foreign key column is indexed, and high-traffic filter columns
  (declaration status, risk level, created_at, flight_number) carry explicit
  indexes so the inspector audit filters and the analytics aggregations stay
  fast as the table grows.
* Relationships are declared on both sides so list views can eager-load related
  rows with a single join and avoid the N+1 query trap (see queries.py).
"""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from . import db


def _utcnow():
    return datetime.now(timezone.utc)


# Roles used across the role-based access control layer.
ROLE_TRAVELER = "traveler"
ROLE_INSPECTOR = "inspector"
ROLE_ADMIN = "admin"
ROLES = (ROLE_TRAVELER, ROLE_INSPECTOR, ROLE_ADMIN)

# Declaration lifecycle states.
STATUS_PENDING = "pending"
STATUS_CLEARED = "cleared"
STATUS_FLAGGED = "flagged"
STATUS_INSPECTED = "inspected"
STATUSES = (STATUS_PENDING, STATUS_CLEARED, STATUS_FLAGGED, STATUS_INSPECTED)

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_LEVELS = (RISK_LOW, RISK_MEDIUM, RISK_HIGH)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_TRAVELER, index=True)
    passport_no = db.Column(db.String(40))
    nationality = db.Column(db.String(60))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    declarations = db.relationship(
        "Declaration",
        back_populates="traveler",
        foreign_keys="Declaration.traveler_id",
    )

    def set_password(self, raw_password):
        # pbkdf2-sha256 with a per-user salt, handled by werkzeug.
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def initials(self):
        parts = [p for p in self.full_name.split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or "?"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Flight(db.Model):
    __tablename__ = "flights"

    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(12), unique=True, nullable=False, index=True)
    airline = db.Column(db.String(80), nullable=False)
    origin = db.Column(db.String(80), nullable=False)
    origin_code = db.Column(db.String(6))
    scheduled_arrival = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="scheduled")

    declarations = db.relationship("Declaration", back_populates="flight")

    def __repr__(self):
        return f"<Flight {self.flight_number} from {self.origin}>"


class Declaration(db.Model):
    __tablename__ = "declarations"
    # Composite index for the most common inspector filter: status within a flight.
    __table_args__ = (
        db.Index("ix_decl_flight_status", "flight_id", "status"),
        db.Index("ix_decl_status_created", "status", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False, index=True)

    traveler_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    flight_id = db.Column(
        db.Integer, db.ForeignKey("flights.id"), nullable=False, index=True
    )
    reviewed_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )

    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING, index=True)
    risk_level = db.Column(db.String(10), nullable=False, default=RISK_LOW, index=True)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    total_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    has_goods_to_declare = db.Column(db.Boolean, nullable=False, default=True)
    traveler_note = db.Column(db.Text)
    inspector_note = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)
    reviewed_at = db.Column(db.DateTime)

    traveler = db.relationship(
        "User", back_populates="declarations", foreign_keys=[traveler_id]
    )
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_id])
    flight = db.relationship("Flight", back_populates="declarations")
    items = db.relationship(
        "DeclarationItem",
        back_populates="declaration",
        cascade="all, delete-orphan",
    )
    audit_entries = db.relationship(
        "AuditLog",
        back_populates="declaration",
        cascade="all, delete-orphan",
        order_by="AuditLog.created_at.desc()",
    )

    def __repr__(self):
        return f"<Declaration {self.reference} {self.status}>"


class DeclarationItem(db.Model):
    __tablename__ = "declaration_items"

    id = db.Column(db.Integer, primary_key=True)
    declaration_id = db.Column(
        db.Integer, db.ForeignKey("declarations.id"), nullable=False, index=True
    )
    description = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(40), nullable=False, default="general", index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    declaration = db.relationship("Declaration", back_populates="items")

    @property
    def line_total(self):
        return (self.quantity or 0) * float(self.unit_value or 0)


class AuditLog(db.Model):
    """Immutable record of every inspector action, powering the audit filters."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    declaration_id = db.Column(
        db.Integer, db.ForeignKey("declarations.id"), nullable=False, index=True
    )
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(40), nullable=False)
    detail = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)

    declaration = db.relationship("Declaration", back_populates="audit_entries")
    actor = db.relationship("User")
