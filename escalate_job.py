"""Run the overdue-complaint escalation check once.

Use it from cron / a hosting provider's scheduled task, or by hand:  python escalate_job.py
(The website also has a "Run escalation check now" button on the admin dashboard.)
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from app import create_app               # noqa: E402
from app.db import get_db                # noqa: E402
from app.escalation import escalate_overdue  # noqa: E402

app = create_app({"SCHEDULER_ENABLED": False})
with app.app_context():
    db = get_db()
    print(f"{escalate_overdue(db)} complaint(s) escalated.")
