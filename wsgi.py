"""Production entry point (PythonAnywhere, gunicorn:  gunicorn wsgi:application)."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from app import create_app   # noqa: E402  (must come after load_dotenv)
from app.db import init_db   # noqa: E402

application = create_app()
with application.app_context():
    init_db()  # creates missing tables only; never deletes data
