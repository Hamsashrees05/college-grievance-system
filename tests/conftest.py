import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app          # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.db import connect, init_db  # noqa: E402
from app.seed_data import seed      # noqa: E402

PASSWORD = "Test@12345"
_HASH = hash_password(PASSWORD)  # hashed once: every demo user shares it, which keeps tests fast


def make_app(tmp_path, csrf=False):
    app = create_app({
        "TESTING": True, "SECRET_KEY": "test-secret-key", "WTF_CSRF_ENABLED": csrf, "SCHEDULER_ENABLED": False,
        "DATABASE": str(tmp_path / "test.db"), "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "LOG_FOLDER": str(tmp_path / "logs"),
    })
    with app.app_context():
        init_db(drop=True)
        from app.db import get_db
        seed(get_db(), _HASH)
    return app


@pytest.fixture()
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture()
def db(app):
    conn = connect(app.config["DATABASE"])
    yield conn
    conn.close()


@pytest.fixture()
def login(app):
    def _login(email):
        client = app.test_client()
        r = client.post("/login", data={"email": email, "password": PASSWORD})
        assert r.status_code == 302, "login failed for " + email
        return client
    return _login
