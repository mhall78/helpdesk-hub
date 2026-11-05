-- HelpDesk Hub database schema (SQLite).
-- "IF NOT EXISTS" makes it safe to run on every startup.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'student'
                  CHECK (role IN ('student', 'staff', 'admin')),
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users (id),
    assigned_to INTEGER REFERENCES users (id),
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    category    TEXT    NOT NULL
                CHECK (category IN ('account', 'wifi', 'software', 'hardware', 'other')),
    priority    TEXT    NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high')),
    status      TEXT    NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER NOT NULL REFERENCES tickets (id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users (id),
    body       TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS articles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER NOT NULL REFERENCES users (id),
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    category   TEXT    NOT NULL DEFAULT 'other',
    updated_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_user   ON tickets (user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status);
CREATE INDEX IF NOT EXISTS idx_comments_ticket ON comments (ticket_id);
