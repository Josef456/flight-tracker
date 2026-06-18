"""JSON endpoints that feed Chart.js on the supervisor dashboard.

These are read-only aggregations and are restricted to inspector and supervisor
roles. Returning JSON keeps the visualization pipeline clean: the server does
the grouping in SQL, the browser only draws.
"""
from flask import Blueprint, jsonify

from ..models import STATUSES, RISK_LEVELS
from ..queries import (
    declarations_per_day,
    origin_volumes,
    risk_breakdown,
    status_breakdown,
    top_flights,
    value_by_category,
)
from ..security import inspector_required

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Destination airport and the origin cities served by the seeded roster.
ENTEBBE = {"city": "Entebbe", "code": "EBB", "lat": 0.0464, "lng": 32.4435}
CITY_COORDS = {
    "Nairobi": (-1.2921, 36.8219),
    "Addis Ababa": (9.0300, 38.7400),
    "Kigali": (-1.9706, 30.1044),
    "Dubai": (25.2048, 55.2708),
    "Doha": (25.2854, 51.5310),
    "Brussels": (50.8503, 4.3517),
    "Istanbul": (41.0082, 28.9784),
    "Amsterdam": (52.3676, 4.9041),
}


@api_bp.route("/analytics/status")
@inspector_required
def status_data():
    data = status_breakdown()
    return jsonify({"labels": list(STATUSES), "values": [data.get(s, 0) for s in STATUSES]})


@api_bp.route("/analytics/risk")
@inspector_required
def risk_data():
    data = risk_breakdown()
    return jsonify(
        {"labels": [r.title() for r in RISK_LEVELS], "values": [data.get(r, 0) for r in RISK_LEVELS]}
    )


@api_bp.route("/analytics/trend")
@inspector_required
def trend_data():
    series = declarations_per_day(14)
    return jsonify(
        {"labels": [p["date"][5:] for p in series], "values": [p["count"] for p in series]}
    )


@api_bp.route("/analytics/flights")
@inspector_required
def flights_data():
    rows = top_flights()
    return jsonify({"labels": [r[0] for r in rows], "values": [r[1] for r in rows]})


@api_bp.route("/analytics/categories")
@inspector_required
def categories_data():
    rows = value_by_category()
    return jsonify(
        {"labels": [r[0].title() for r in rows], "values": [round(r[1], 2) for r in rows]}
    )


@api_bp.route("/geo/origins")
@inspector_required
def geo_origins():
    """Flight origins with their declaration volume, for the arrivals map."""
    origins = []
    for row in origin_volumes():
        coords = CITY_COORDS.get(row["city"])
        if not coords:
            continue
        origins.append({
            "city": row["city"],
            "code": row["code"],
            "lat": coords[0],
            "lng": coords[1],
            "count": row["count"],
            "flagged": row["flagged"],
        })
    return jsonify({"destination": ENTEBBE, "origins": origins})
