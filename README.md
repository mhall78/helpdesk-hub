# HelpDesk Hub

A campus IT support ticket system. Students submit and track tickets, help-desk staff work a shared queue, everyone can search a knowledge base of common fixes, and admins see how support is going.

- **Live app:** _add your Render URL here_
- **Stack:** Python 3.12, Flask, SQLite, vanilla HTML/CSS/JS, pytest, Docker, Render

## Features

| # | Feature | Who | Where |
|---|---|---|---|
| 1 | Accounts and roles (student, staff, admin) | Everyone | `/login`, `/register` |
| 2 | Submit a ticket (category, priority, description) | Students | `/tickets` |
| 3 | Track my tickets + reply thread | Students | `/tickets`, `/tickets/<id>` |
| 4 | Staff queue: filter, search, claim, change status, resolve with a note | Staff | `/queue`, `/tickets/<id>` |
| 5 | Knowledge base: search; staff write and edit articles | Everyone | `/kb` |
| 6 | Admin dashboard: counts by status/category, avg. time to resolve | Admin | `/admin` |

### Demo accounts

When `SEED_DEMO=1` (the default), an empty database is filled with three accounts and three help articles. Password for all: `password123`.

| Email | Role |
|---|---|
| student@demo.edu | student |
| staff@demo.edu | staff |
| admin@demo.edu | admin |

New sign-ups are always students. Create staff or admins from the command line:

```bash
flask --app app create-user "Ann Lee" ann@wssu.edu secret123 --role staff
```

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
flask --app app run --debug        # http://127.0.0.1:5000
```

The SQLite database is created automatically at `instance/helpdesk.db`. Delete that file to start fresh.

## Run the tests

```bash
pytest -v
```

There are 30 tests covering auth, permissions, the ticket workflow, comments, the knowledge base, and the dashboard. GitHub Actions runs them, and builds the Docker image, on every push (`.github/workflows/tests.yml`).

## Run with Docker

```bash
docker build -t helpdesk-hub .
docker run -p 8000:8000 helpdesk-hub      # http://localhost:8000
```

## Deploy to Render

1. Push this repo to GitHub.
2. In Render, choose **New > Blueprint** and pick the repo. `render.yaml` sets up a Docker web service with a generated `SECRET_KEY`.
3. When the deploy finishes, open the `.onrender.com` URL and log in with a demo account.

**Note on data:** Render's free plan has no persistent disk, so the SQLite file resets when the service restarts or redeploys (demo data is re-seeded automatically). That's fine for a class demo. For real use, add a Render disk mounted at `/data`, or switch to PostgreSQL.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `dev-only-change-me` | Signs session cookies. **Set this in production.** |
| `DATABASE_PATH` | `instance/helpdesk.db` (`/data/helpdesk.db` in Docker) | SQLite file location |
| `SEED_DEMO` | `1` | Create demo accounts and articles in an empty database |
| `DEMO_PASSWORD` | `password123` | Password for the demo accounts |
| `SESSION_COOKIE_SECURE` | `0` | Set to `1` behind HTTPS (Render) |

## Architecture

Browser pages are thin HTML shells; their JavaScript calls a JSON REST API with `fetch()`. Flask serves both, organized as blueprints:

```
app/
  __init__.py     app factory, error handlers, /health
  db.py           SQLite connection, schema setup, demo data, CLI commands
  schema.sql      tables: users, tickets, comments, articles
  auth.py         /api/auth/*  register, login, logout, me; role checks
  tickets.py      /api/tickets/*  tickets and comments
  articles.py     /api/articles/*  knowledge base
  admin.py        /api/admin/stats
  pages.py        HTML page routes
  templates/      Jinja pages
  static/         app.js (API helper, escaping), style.css
tests/            pytest suite
```

### API

| Method | Endpoint | Who | Does |
|---|---|---|---|
| POST | `/api/auth/register` | Anyone | Create a student account and log in |
| POST | `/api/auth/login` | Anyone | Log in |
| POST | `/api/auth/logout` | Anyone | Log out |
| GET | `/api/auth/me` | Logged in | Current user |
| GET | `/api/tickets` | Logged in | Students: own tickets. Staff: all, with `status`, `category`, `priority`, `assigned=me\|none`, `q` filters |
| POST | `/api/tickets` | Logged in | Submit a ticket |
| GET | `/api/tickets/<id>` | Owner, staff | Ticket with comments |
| PATCH | `/api/tickets/<id>` | Staff | Change `status`, `priority`, `assigned_to` (`"me"`, staff id, or `null`); optional `note` adds a comment |
| POST | `/api/tickets/<id>/comments` | Owner, staff | Add a reply |
| GET | `/api/articles?q=` | Anyone | Search articles |
| GET | `/api/articles/<id>` | Anyone | One article |
| POST | `/api/articles` | Staff | Create an article |
| PUT | `/api/articles/<id>` | Staff | Edit an article |
| GET | `/api/admin/stats` | Admin | Dashboard numbers |

### Security notes

- Passwords are hashed with Werkzeug (`generate_password_hash`).
- All SQL uses parameterized queries.
- User text is HTML-escaped before display (`esc()` in `app.js`).
- Session cookies are `HttpOnly` and `SameSite=Lax`.
- Students get a 404 (not 403) for other students' tickets, so ticket IDs can't be probed.

## Ideas for next steps

- Screenshot attachments on tickets (user story 4)
- Email or in-app notifications when a ticket changes
- PostgreSQL for persistent production data
