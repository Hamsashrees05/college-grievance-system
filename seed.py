"""Create (or reset) the database and fill it with demo data.

WARNING: this deletes all existing data.   Usage:  python seed.py
Set SEED_PASSWORD in .env to choose the shared demo password; otherwise a random one is printed once.
"""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

from app import create_app          # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.db import get_db, init_db  # noqa: E402
from app.seed_data import seed      # noqa: E402
from app.utils import validate_password  # noqa: E402

if __name__ == "__main__":
    password = os.environ.get("SEED_PASSWORD") or ""
    generated = False
    if not password:
        password, generated = "Cg" + secrets.token_urlsafe(9) + "7x", True
    elif validate_password(password):
        raise SystemExit("SEED_PASSWORD must have 8+ characters, an uppercase letter, a lowercase letter and a digit.")

    app = create_app({"SCHEDULER_ENABLED": False})
    with app.app_context():
        init_db(drop=True)
        logins = seed(get_db(), hash_password(password))

    print("\nDatabase created with demo data.\n")
    print("Demo logins (same password for all):")
    for role, email in logins:
        print(f"  {role:<10} {email}")
    print(f"\nPassword: {password}" + ("   <-- generated, shown only once. Write it down." if generated else ""))
    print("\nNow start the site with:  python run.py   and open http://127.0.0.1:5000\n")
