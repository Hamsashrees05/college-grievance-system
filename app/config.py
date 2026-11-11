"""Application configuration. Secrets come from environment variables, never from code."""
import os
import secrets
from datetime import timedelta
from pathlib import Path


class ConfigError(RuntimeError):
    pass


def build_config(app, overrides=None):
    overrides = overrides or {}
    debug = os.environ.get("FLASK_DEBUG") == "1"
    instance = Path(app.instance_path)
    instance.mkdir(parents=True, exist_ok=True)

    cfg = dict(
        DATABASE=str(instance / "cgms.db"),
        UPLOAD_FOLDER=str(instance / "uploads"),
        LOG_FOLDER=str(Path(app.root_path).parent / "logs"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,      # whole request
        MAX_FILE_SIZE=5 * 1024 * 1024,             # one attachment
        MAX_FILES_PER_UPLOAD=3,
        MAX_FILES_PER_COMPLAINT=5,
        ALLOWED_EXTENSIONS={"pdf", "png", "jpg", "jpeg"},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        WTF_CSRF_TIME_LIMIT=None,
        SCHEDULER_ENABLED=True,
        ESCALATION_HOUR=2,
        REOPEN_WINDOW_DAYS=7,
        LOGIN_MAX_ATTEMPTS=5,
        LOGIN_LOCK_MINUTES=10,
        SMTP_HOST=os.environ.get("SMTP_HOST") or None,
        SMTP_PORT=int(os.environ.get("SMTP_PORT") or 587),
        SMTP_USER=os.environ.get("SMTP_USER") or None,
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD") or None,
        SMTP_FROM=os.environ.get("SMTP_FROM") or "no-reply@cgms.local",
    )
    cfg.update(overrides)

    secret = overrides.get("SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not secret:
        if debug:
            key_file = instance / "dev_secret.key"
            if key_file.exists():
                secret = key_file.read_text().strip()
            else:
                secret = secrets.token_hex(32)
                key_file.write_text(secret)
        else:
            raise ConfigError(
                "SECRET_KEY is not set. Copy .env.example to .env (it sets FLASK_DEBUG=1 for local use) "
                "or set SECRET_KEY to a long random value."
            )
    cfg["SECRET_KEY"] = secret
    app.config.update(cfg)
