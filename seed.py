"""Seed the database with realistic mock data.

    python seed.py          # drops and recreates all tables, then loads demo data

Creates the three system roles, a roster of arriving flights, and a spread of
customs declarations across every status and risk band so the dashboards and
audit filters have something meaningful to show.
"""
import random
from datetime import datetime, timedelta

from app import create_app, db
from app.models import (
    AuditLog,
    Declaration,
    DeclarationItem,
    Flight,
    User,
    ROLE_ADMIN,
    ROLE_INSPECTOR,
    ROLE_TRAVELER,
    STATUS_CLEARED,
    STATUS_FLAGGED,
    STATUS_INSPECTED,
    STATUS_PENDING,
)
from app.services import generate_reference, score_risk

# Deterministic data so screenshots and reports stay reproducible.
random.seed(81213)

FLIGHTS = [
    ("KQ412", "Kenya Airways", "Nairobi", "NBO"),
    ("ET336", "Ethiopian Airlines", "Addis Ababa", "ADD"),
    ("WB482", "RwandAir", "Kigali", "KGL"),
    ("EK729", "Emirates", "Dubai", "DXB"),
    ("QR1373", "Qatar Airways", "Doha", "DOH"),
    ("SA204", "Brussels Airlines", "Brussels", "BRU"),
    ("TK612", "Turkish Airlines", "Istanbul", "IST"),
    ("KL565", "KLM", "Amsterdam", "AMS"),
]

TRAVELERS = [
    ("Aisha Nakimera", "aisha@example.com", "B0451123", "Ugandan"),
    ("David Okello", "david@example.com", "B0918842", "Ugandan"),
    ("Grace Atim", "grace@example.com", "C2231908", "Ugandan"),
    ("Samuel Mugisha", "samuel@example.com", "B1120934", "Ugandan"),
    ("Lydia Namatovu", "lydia@example.com", "D5512098", "Ugandan"),
    ("John Carter", "john.carter@example.com", "X8841220", "British"),
    ("Mei Lin", "mei.lin@example.com", "G4410982", "Chinese"),
    ("Fatima Hassan", "fatima@example.com", "K2298120", "Kenyan"),
]

ITEM_POOL = {
    "electronics": [("Laptop computer", 1200), ("Mobile phone", 800), ("Camera kit", 2200)],
    "apparel": [("Designer clothing", 600), ("Leather shoes", 180), ("Wrist watch", 3500)],
    "food": [("Packaged coffee", 40), ("Dried spices", 25), ("Honey jars", 30)],
    "medical": [("Prescription medicine", 450), ("Medical device", 5200)],
    "commercial": [("Phone accessories carton", 3200), ("Spare parts crate", 8800)],
    "currency": [("Foreign currency", 12000), ("Gold jewellery", 9000)],
    "general": [("Personal gifts", 120), ("Books", 60), ("Household items", 200)],
}

CURRENCIES = ["USD", "USD", "USD", "EUR", "GBP", "UGX"]


def populate():
    """Load demo data into empty tables using the active app context and session.

    Assumes the tables already exist and are empty, and deliberately does not drop
    anything. That makes it safe to call from a process (such as the gunicorn web
    worker) that already holds an open transaction on the database: issuing DROP
    there would deadlock against that transaction's table locks.
    """
    # --- Users ---------------------------------------------------------
    admin = User(full_name="Brenda Komugisha", email="supervisor@entebbe.go.ug",
                 role=ROLE_ADMIN, nationality="Ugandan")
    admin.set_password("Supervisor#2026")

    inspectors = []
    for name, email in [
        ("Patrick Wamala", "patrick@entebbe.go.ug"),
        ("Sandra Achieng", "sandra@entebbe.go.ug"),
    ]:
        ins = User(full_name=name, email=email, role=ROLE_INSPECTOR, nationality="Ugandan")
        ins.set_password("Inspector#2026")
        inspectors.append(ins)

    travelers = []
    for name, email, passport, nat in TRAVELERS:
        t = User(full_name=name, email=email, role=ROLE_TRAVELER,
                 passport_no=passport, nationality=nat)
        t.set_password("Traveler#2026")
        travelers.append(t)

    db.session.add_all([admin, *inspectors, *travelers])
    db.session.flush()

    # --- Flights -------------------------------------------------------
    base = datetime(2026, 6, 25, 6, 0)
    flights = []
    for i, (num, airline, origin, code) in enumerate(FLIGHTS):
        f = Flight(
            flight_number=num, airline=airline, origin=origin, origin_code=code,
            scheduled_arrival=base + timedelta(hours=i * 3),
            status="arrived",
        )
        flights.append(f)
    db.session.add_all(flights)
    db.session.flush()

    # --- Declarations --------------------------------------------------
    statuses = (
        [STATUS_PENDING] * 8
        + [STATUS_CLEARED] * 14
        + [STATUS_FLAGGED] * 5
        + [STATUS_INSPECTED] * 5
    )
    random.shuffle(statuses)

    for n, status in enumerate(statuses):
        traveler = random.choice(travelers)
        flight = random.choice(flights)
        currency = random.choice(CURRENCIES)
        created = datetime(2026, 6, 12) + timedelta(
            days=random.randint(0, 13), hours=random.randint(0, 20)
        )

        n_items = random.randint(1, 4)
        categories = random.sample(list(ITEM_POOL.keys()), k=n_items)
        items, total = [], 0
        for cat in categories:
            desc, base_val = random.choice(ITEM_POOL[cat])
            qty = random.randint(1, 3)
            unit = base_val * (1 if currency != "UGX" else 3600)
            items.append(DeclarationItem(description=desc, category=cat,
                                         quantity=qty, unit_value=unit))
            total += unit * qty

        decl = Declaration(
            reference=generate_reference(),
            traveler_id=traveler.id,
            flight_id=flight.id,
            currency=currency,
            total_value=total,
            has_goods_to_declare=True,
            traveler_note=None,
            status=status,
            created_at=created,
            items=items,
        )
        decl.risk_level = score_risk(total, currency, items)

        if status != STATUS_PENDING:
            reviewer = random.choice(inspectors)
            decl.reviewed_by_id = reviewer.id
            decl.reviewed_at = created + timedelta(hours=random.randint(1, 12))
            if status == STATUS_FLAGGED:
                decl.inspector_note = "Declared value inconsistent with documentation."
            elif status == STATUS_INSPECTED:
                decl.inspector_note = "Baggage physically inspected, contents match."

        db.session.add(decl)
        db.session.flush()

        db.session.add(AuditLog(declaration_id=decl.id, actor_id=traveler.id,
                                action="submitted", detail=f"{len(items)} item(s)",
                                created_at=created))
        if status != STATUS_PENDING:
            db.session.add(AuditLog(declaration_id=decl.id, actor_id=decl.reviewed_by_id,
                                    action=status, detail=f"risk={decl.risk_level}",
                                    created_at=decl.reviewed_at))

    db.session.commit()

    print("Seed complete.")
    print(f"  Users:        {User.query.count()}")
    print(f"  Flights:      {Flight.query.count()}")
    print(f"  Declarations: {Declaration.query.count()}")
    print()
    print("Demo logins (password in parentheses):")
    print("  Supervisor:  supervisor@entebbe.go.ug  (Supervisor#2026)")
    print("  Inspector:   patrick@entebbe.go.ug     (Inspector#2026)")
    print("  Traveler:    aisha@example.com         (Traveler#2026)")


def build():
    """Drop, recreate, and repopulate everything. For a deliberate full reset."""
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        populate()


if __name__ == "__main__":
    build()
