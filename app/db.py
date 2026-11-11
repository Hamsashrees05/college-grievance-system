"""SQLite helpers. Only parameterized SQL is used anywhere in the project."""
import sqlite3
from flask import current_app, g

TABLES = ["audit_logs", "notifications", "feedback", "escalations", "responses",
          "assignments", "attachments", "complaints", "categories", "users", "departments"]


def connect(path):
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(drop=False):
    db = get_db()
    if drop:
        db.execute("PRAGMA foreign_keys = OFF")
        for t in TABLES:
            db.execute(f"DROP TABLE IF EXISTS {t}")  # table names are constants, not user input
        db.execute("PRAGMA foreign_keys = ON")
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    db.commit()
