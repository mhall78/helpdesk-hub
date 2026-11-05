"""Tickets and comments: submit, track, and (for staff) work the queue."""
from flask import Blueprint, jsonify, request

from .auth import current_user, is_staff, json_body, login_required
from .db import get_db, now

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

CATEGORIES = ("account", "wifi", "software", "hardware", "other")
PRIORITIES = ("low", "medium", "high")
STATUSES = ("open", "in_progress", "resolved", "closed")

TICKET_SELECT = """
    SELECT t.*, u.name AS requester_name, u.email AS requester_email, a.name AS assignee_name
    FROM tickets t
    JOIN users u ON u.id = t.user_id
    LEFT JOIN users a ON a.id = t.assigned_to
"""
# High priority first, then oldest first, so the most urgent, longest-waiting ticket is on top.
PRIORITY_ORDER = "CASE t.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END"


def load_ticket(ticket_id):
    row = get_db().execute(TICKET_SELECT + " WHERE t.id = ?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def can_view(user, ticket):
    return is_staff(user) or ticket["user_id"] == user["id"]


@bp.get("")
@login_required()
def list_tickets():
    """Students get their own tickets. Staff get every ticket, with optional filters."""
    user = current_user()
    where, params = [], []

    if not is_staff(user):
        where.append("t.user_id = ?")
        params.append(user["id"])

    for field, allowed in (("status", STATUSES), ("category", CATEGORIES), ("priority", PRIORITIES)):
        value = request.args.get(field)
        if value:
            if value not in allowed:
                return jsonify(error=f"Unknown {field}: {value}"), 400
            where.append(f"t.{field} = ?")
            params.append(value)

    assigned = request.args.get("assigned")
    if assigned == "me":
        where.append("t.assigned_to = ?")
        params.append(user["id"])
    elif assigned == "none":
        where.append("t.assigned_to IS NULL")

    q = (request.args.get("q") or "").strip()
    if q:
        where.append("(t.title LIKE ? OR t.description LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]

    sql = TICKET_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {PRIORITY_ORDER}, t.created_at"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify(tickets=[dict(r) for r in rows])


@bp.post("")
@login_required()
def create_ticket():
    data = json_body()
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = data.get("category") or "other"
    priority = data.get("priority") or "medium"

    errors = {}
    if not title:
        errors["title"] = "Give the ticket a short title."
    elif len(title) > 120:
        errors["title"] = "Keep the title under 120 characters."
    if not description:
        errors["description"] = "Describe the problem."
    if category not in CATEGORIES:
        errors["category"] = "Pick a category."
    if priority not in PRIORITIES:
        errors["priority"] = "Pick a priority."
    if errors:
        return jsonify(error="Please fix the highlighted fields.", fields=errors), 400

    ts = now()
    db = get_db()
    cur = db.execute(
        """INSERT INTO tickets (user_id, title, description, category, priority, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'open', ?, ?)""",
        (current_user()["id"], title, description, category, priority, ts, ts),
    )
    db.commit()
    return jsonify(ticket=load_ticket(cur.lastrowid)), 201


@bp.get("/<int:ticket_id>")
@login_required()
def get_ticket(ticket_id):
    ticket = load_ticket(ticket_id)
    if ticket is None or not can_view(current_user(), ticket):
        return jsonify(error="Ticket not found."), 404  # 404 (not 403) so students can't probe other IDs
    comments = get_db().execute(
        """SELECT c.id, c.body, c.created_at, u.name AS author_name, u.role AS author_role
           FROM comments c JOIN users u ON u.id = c.user_id
           WHERE c.ticket_id = ? ORDER BY c.created_at, c.id""",
        (ticket_id,),
    ).fetchall()
    ticket["comments"] = [dict(c) for c in comments]
    return jsonify(ticket=ticket)


@bp.patch("/<int:ticket_id>")
@login_required("staff", "admin")
def update_ticket(ticket_id):
    """Staff change status, priority or assignee. An optional 'note' is posted as a comment."""
    ticket = load_ticket(ticket_id)
    if ticket is None:
        return jsonify(error="Ticket not found."), 404

    data = json_body()
    user = current_user()
    updates = {}

    if "status" in data:
        if data["status"] not in STATUSES:
            return jsonify(error="Unknown status."), 400
        updates["status"] = data["status"]
        if data["status"] in ("resolved", "closed"):
            updates["resolved_at"] = ticket["resolved_at"] or now()
        else:
            updates["resolved_at"] = None
    if "priority" in data:
        if data["priority"] not in PRIORITIES:
            return jsonify(error="Unknown priority."), 400
        updates["priority"] = data["priority"]
    if "assigned_to" in data:
        target = data["assigned_to"]
        if target == "me":
            updates["assigned_to"] = user["id"]
            if ticket["status"] == "open" and "status" not in data:
                updates["status"] = "in_progress"  # claiming a ticket starts work on it
        elif target is None:
            updates["assigned_to"] = None
        else:
            row = get_db().execute("SELECT role FROM users WHERE id = ?", (target,)).fetchone()
            if row is None or row["role"] not in ("staff", "admin"):
                return jsonify(error="Tickets can only be assigned to staff."), 400
            updates["assigned_to"] = target

    note = (data.get("note") or "").strip()
    if not updates and not note:
        return jsonify(error="Nothing to update."), 400

    db = get_db()
    if updates:
        updates["updated_at"] = now()
        cols = ", ".join(f"{k} = ?" for k in updates)  # keys come from the fixed set above, never from input
        db.execute(f"UPDATE tickets SET {cols} WHERE id = ?", (*updates.values(), ticket_id))
    if note:
        db.execute(
            "INSERT INTO comments (ticket_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, user["id"], note, now()),
        )
    db.commit()
    return jsonify(ticket=load_ticket(ticket_id))


@bp.post("/<int:ticket_id>/comments")
@login_required()
def add_comment(ticket_id):
    ticket = load_ticket(ticket_id)
    user = current_user()
    if ticket is None or not can_view(user, ticket):
        return jsonify(error="Ticket not found."), 404
    body = (json_body().get("body") or "").strip()
    if not body:
        return jsonify(error="Write a reply first.", fields={"body": "Required."}), 400

    db = get_db()
    ts = now()
    cur = db.execute(
        "INSERT INTO comments (ticket_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
        (ticket_id, user["id"], body, ts),
    )
    db.execute("UPDATE tickets SET updated_at = ? WHERE id = ?", (ts, ticket_id))
    db.commit()
    return jsonify(comment={
        "id": cur.lastrowid, "body": body, "created_at": ts,
        "author_name": user["name"], "author_role": user["role"],
    }), 201
