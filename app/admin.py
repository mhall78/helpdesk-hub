"""Admin dashboard data: ticket counts and how fast tickets get resolved."""
from datetime import datetime

from flask import Blueprint, jsonify

from .auth import login_required
from .db import get_db
from .tickets import CATEGORIES, STATUSES

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/stats")
@login_required("admin")
def stats():
    db = get_db()
    by_status = {s: 0 for s in STATUSES}
    for row in db.execute("SELECT status, COUNT(*) AS n FROM tickets GROUP BY status"):
        by_status[row["status"]] = row["n"]
    by_category = {c: 0 for c in CATEGORIES}
    for row in db.execute("SELECT category, COUNT(*) AS n FROM tickets GROUP BY category"):
        by_category[row["category"]] = row["n"]

    hours = []
    for row in db.execute("SELECT created_at, resolved_at FROM tickets WHERE resolved_at IS NOT NULL"):
        delta = datetime.fromisoformat(row["resolved_at"]) - datetime.fromisoformat(row["created_at"])
        hours.append(delta.total_seconds() / 3600)

    unassigned = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE assigned_to IS NULL AND status IN ('open', 'in_progress')"
    ).fetchone()[0]

    return jsonify(
        total=sum(by_status.values()),
        by_status=by_status,
        by_category=by_category,
        unassigned_open=unassigned,
        avg_resolution_hours=round(sum(hours) / len(hours), 1) if hours else None,
        resolved_count=len(hours),
    )
