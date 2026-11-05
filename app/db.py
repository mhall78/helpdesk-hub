"""Database helpers: one SQLite connection per request, schema setup, demo data."""
import sqlite3
from datetime import datetime, timezone

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


def now():
    """Current UTC time as an ISO string, e.g. 2026-11-05T18:30:00+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    db.commit()


def create_user(name, email, password, role="student"):
    db = get_db()
    cur = db.execute(
        "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, email.lower().strip(), generate_password_hash(password, method="pbkdf2:sha256"), role, now()),
    )
    db.commit()
    return cur.lastrowid


DEMO_ARTICLES = [
    ("How to reset your campus password",
     "1. Go to the campus password portal.\n2. Choose 'Forgot password'.\n"
     "3. Verify with your backup email or phone.\n4. Pick a new password of at least 12 characters.\n"
     "Still locked out? Submit a ticket under Account.", "account"),
    ("Connecting to campus Wi-Fi",
     "1. Pick the secure campus network (not the guest network).\n"
     "2. Sign in with your full student email and password.\n"
     "3. If asked about a certificate, accept the campus certificate.\n"
     "4. Forget the network and reconnect if it keeps dropping.", "wifi"),
    ("Installing licensed software",
     "Most licensed software is in the campus software portal. Sign in with your student account, "
     "download the installer, and restart after installing. If it crashes on launch, include the "
     "exact error message and the version number in your ticket.", "software"),
]


def seed_demo_data():
    """Create demo accounts and help articles, only if the database has no users yet."""
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return False
    pw = current_app.config["DEMO_PASSWORD"]
    create_user("Demo Student", "student@demo.edu", pw, "student")
    staff_id = create_user("Demo Staff", "staff@demo.edu", pw, "staff")
    create_user("Demo Admin", "admin@demo.edu", pw, "admin")
    for title, body, category in DEMO_ARTICLES:
        db.execute(
            "INSERT INTO articles (author_id, title, body, category, updated_at) VALUES (?, ?, ?, ?, ?)",
            (staff_id, title, body, category, now()),
        )
    db.commit()
    return True


@click.command("init-db")
def init_db_command():
    """Create the tables (safe to run more than once)."""
    init_db()
    click.echo("Database ready.")


@click.command("create-user")
@click.argument("name")
@click.argument("email")
@click.argument("password")
@click.option("--role", type=click.Choice(["student", "staff", "admin"]), default="student")
def create_user_command(name, email, password, role):
    """Create an account, e.g. flask --app app create-user "Ann Lee" ann@wssu.edu secret123 --role staff"""
    init_db()
    create_user(name, email, password, role)
    click.echo(f"Created {role} account for {email}.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_user_command)
