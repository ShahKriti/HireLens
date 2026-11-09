import sqlite3
from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('recruiter','client','delivery')),
 client_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS requisitions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, client_name TEXT NOT NULL,
 location TEXT NOT NULL, min_experience REAL NOT NULL, max_experience REAL NOT NULL,
 must_have TEXT NOT NULL, max_notice INTEGER NOT NULL, min_ctc REAL, max_ctc REAL,
 status TEXT DEFAULT 'open', created_by INTEGER REFERENCES users(id),
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS candidates (
 id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_code TEXT UNIQUE, name TEXT NOT NULL,
 current_role TEXT, experience REAL DEFAULT 0, skills TEXT DEFAULT '', notice_days INTEGER,
 email TEXT, phone TEXT, location TEXT, cv_text TEXT DEFAULT '', cv_text_hash TEXT, file_name TEXT,
 consent INTEGER DEFAULT 0, deleted INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS applications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, requisition_id INTEGER REFERENCES requisitions(id),
 candidate_id INTEGER REFERENCES candidates(id), score REAL DEFAULT 0, score_details TEXT DEFAULT '{}',
 status TEXT DEFAULT 'sourced', submitted INTEGER DEFAULT 0, client_id INTEGER,
 rejection_reason TEXT, interview_slot TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(requisition_id,candidate_id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, candidate_id INTEGER,
 action TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def close_db(_=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.executescript(SCHEMA)
        db.commit()
        db.close()
    app.teardown_appcontext(close_db)
