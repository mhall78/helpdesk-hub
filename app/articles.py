"""Knowledge base: anyone can search help articles; staff write and edit them."""
from flask import Blueprint, jsonify, request

from .auth import current_user, json_body, login_required
from .db import get_db, now
from .tickets import CATEGORIES

bp = Blueprint("articles", __name__, url_prefix="/api/articles")

ARTICLE_SELECT = """
    SELECT a.*, u.name AS author_name FROM articles a JOIN users u ON u.id = a.author_id
"""


def validate(data):
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    category = data.get("category") or "other"
    errors = {}
    if not title:
        errors["title"] = "Title is required."
    if not body:
        errors["body"] = "Article text is required."
    if category not in CATEGORIES:
        errors["category"] = "Pick a category."
    return title, body, category, errors


@bp.get("")
def search_articles():
    q = (request.args.get("q") or "").strip()
    category = request.args.get("category")
    where, params = [], []
    if q:
        where.append("(a.title LIKE ? OR a.body LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if category:
        where.append("a.category = ?")
        params.append(category)
    sql = ARTICLE_SELECT + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY a.title"
    return jsonify(articles=[dict(r) for r in get_db().execute(sql, params).fetchall()])


@bp.get("/<int:article_id>")
def get_article(article_id):
    row = get_db().execute(ARTICLE_SELECT + " WHERE a.id = ?", (article_id,)).fetchone()
    if row is None:
        return jsonify(error="Article not found."), 404
    return jsonify(article=dict(row))


@bp.post("")
@login_required("staff", "admin")
def create_article():
    title, body, category, errors = validate(json_body())
    if errors:
        return jsonify(error="Please fix the highlighted fields.", fields=errors), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO articles (author_id, title, body, category, updated_at) VALUES (?, ?, ?, ?, ?)",
        (current_user()["id"], title, body, category, now()),
    )
    db.commit()
    row = db.execute(ARTICLE_SELECT + " WHERE a.id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(article=dict(row)), 201


@bp.put("/<int:article_id>")
@login_required("staff", "admin")
def update_article(article_id):
    db = get_db()
    if db.execute("SELECT 1 FROM articles WHERE id = ?", (article_id,)).fetchone() is None:
        return jsonify(error="Article not found."), 404
    title, body, category, errors = validate(json_body())
    if errors:
        return jsonify(error="Please fix the highlighted fields.", fields=errors), 400
    db.execute(
        "UPDATE articles SET title = ?, body = ?, category = ?, updated_at = ? WHERE id = ?",
        (title, body, category, now(), article_id),
    )
    db.commit()
    return get_article(article_id)
