"""Accounts and roles: register, login, logout, and access-control helpers."""
from functools import wraps

from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import check_password_hash

from .db import create_user, get_db

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

STAFF_ROLES = ("staff", "admin")


def current_user():
    """The logged-in user as a dict, or None. Cached for the request."""
    if "user" not in g:
        g.user = None
        uid = session.get("user_id")
        if uid is not None:
            row = get_db().execute(
                "SELECT id, name, email, role FROM users WHERE id = ?", (uid,)
            ).fetchone()
            g.user = dict(row) if row else None
    return g.user


def is_staff(user):
    return user is not None and user["role"] in STAFF_ROLES


def login_required(*roles):
    """Decorator for API routes. login_required() = any user; login_required('admin') = admins only."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify(error="Please log in."), 401
            if roles and user["role"] not in roles:
                return jsonify(error="You don't have permission to do that."), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator


def json_body():
    return request.get_json(silent=True) or {}


@bp.post("/register")
def register():
    data = json_body()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    errors = {}
    if not name:
        errors["name"] = "Name is required."
    if "@" not in email or "." not in email.split("@")[-1]:
        errors["email"] = "Enter a valid email address."
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."
    if not errors and get_db().execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        errors["email"] = "An account with that email already exists."
    if errors:
        return jsonify(error="Please fix the highlighted fields.", fields=errors), 400

    # Self-registration always creates a student. Staff and admins are created with the CLI.
    uid = create_user(name, email, password, "student")
    session.clear()
    session["user_id"] = uid
    return jsonify(user={"id": uid, "name": name, "email": email, "role": "student"}), 201


@bp.post("/login")
def login():
    data = json_body()
    email = (data.get("email") or "").strip().lower()
    row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], data.get("password") or ""):
        return jsonify(error="Wrong email or password."), 401
    session.clear()
    session["user_id"] = row["id"]
    return jsonify(user={"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]})


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.get("/me")
@login_required()
def me():
    return jsonify(user=current_user())
