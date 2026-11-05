"""HelpDesk Hub: a campus IT support ticket system built with Flask."""
import os

from flask import Flask, jsonify, render_template, request

from . import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "helpdesk.db")),
        SEED_DEMO=os.environ.get("SEED_DEMO", "1") == "1",
        DEMO_PASSWORD=os.environ.get("DEMO_PASSWORD", "password123"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.init_db()
        if app.config["SEED_DEMO"]:
            db.seed_demo_data()

    from .auth import bp as auth_bp
    from .tickets import bp as tickets_bp
    from .articles import bp as articles_bp
    from .admin import bp as admin_bp
    from .pages import bp as pages_bp

    for bp in (auth_bp, tickets_bp, articles_bp, admin_bp, pages_bp):
        app.register_blueprint(bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(403)
    @app.errorhandler(404)
    def http_error(e):
        # API callers get JSON; people in a browser get a simple page.
        if request.path.startswith("/api/"):
            return jsonify(error=e.description), e.code
        return render_template("error.html", error=e), e.code

    return app
