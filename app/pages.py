"""HTML pages. Each page is a thin shell; its data comes from the JSON API via fetch()."""
from functools import wraps

from flask import Blueprint, abort, redirect, render_template, url_for

from .auth import current_user, is_staff

bp = Blueprint("pages", __name__)


def page(*roles):
    """Like login_required, but redirects to the login page instead of returning JSON."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return redirect(url_for("pages.login"))
            if roles and user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@bp.app_context_processor
def inject_user():
    return {"user": current_user(), "is_staff": is_staff(current_user())}


@bp.get("/")
def home():
    user = current_user()
    if user is None:
        return redirect(url_for("pages.login"))
    return redirect(url_for("pages.queue" if is_staff(user) else "pages.my_tickets"))


@bp.get("/login")
def login():
    return render_template("login.html")


@bp.get("/register")
def register():
    return render_template("register.html")


@bp.get("/tickets")
@page()
def my_tickets():
    return render_template("my_tickets.html")


@bp.get("/tickets/<int:ticket_id>")
@page()
def ticket_detail(ticket_id):
    return render_template("ticket.html", ticket_id=ticket_id)


@bp.get("/queue")
@page("staff", "admin")
def queue():
    return render_template("queue.html")


@bp.get("/kb")
def knowledge_base():
    return render_template("kb.html")


@bp.get("/admin")
@page("admin")
def admin_dashboard():
    return render_template("admin.html")
