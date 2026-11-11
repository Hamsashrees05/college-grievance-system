"""Shared helpers: time, validation, decorators, pagination and audit logging."""
import re
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, g, has_request_context, redirect, request, url_for

FMT = "%Y-%m-%d %H:%M:%S"
COMPLAINANT_ROLES = ("student", "staff")
STAFF_ROLES = ("officer", "hod", "committee", "admin")
ALL_ROLES = COMPLAINANT_ROLES + STAFF_ROLES
ROLE_LABELS = {"student": "Student", "staff": "Staff member", "officer": "Department officer",
               "hod": "Head of department", "committee": "Grievance committee", "admin": "Administrator"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{7,15}$")


def now():
    return datetime.now()


def now_str():
    return now().strftime(FMT)


def parse_dt(value):
    return datetime.strptime(value, FMT)


def validate_password(pw):
    errors = []
    if len(pw or "") < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", pw or ""):
        errors.append("an uppercase letter")
    if not re.search(r"[a-z]", pw or ""):
        errors.append("a lowercase letter")
    if not re.search(r"\d", pw or ""):
        errors.append("a digit")
    return errors


def clean(value, max_len=None):
    value = (value or "").strip()
    return value[:max_len] if max_len else value


def safe_next(target):
    """Only allow same-site relative redirects (prevents open redirect)."""
    if not target:
        return None
    p = urlparse(target)
    if p.scheme or p.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def audit(db, user_id, action, entity=None, entity_id=None, details=None):
    ip = request.remote_addr if has_request_context() else None
    db.execute(
        "INSERT INTO audit_logs (user_id, action, entity, entity_id, details, ip_address, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (user_id, action, entity, entity_id, details, ip, now_str()),
    )


def paginate(db, count_sql, rows_sql, params, page, per_page=10):
    total = db.execute(count_sql, params).fetchone()[0]
    pages = max(1, -(-total // per_page))
    page = min(max(page, 1), pages)
    rows = db.execute(rows_sql + " LIMIT ? OFFSET ?", list(params) + [per_page, (page - 1) * per_page]).fetchall()
    return {"rows": rows, "total": total, "page": page, "pages": pages}


def like_escape(text):
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def page_arg():
    try:
        return max(1, int(request.args.get("page", 1)))
    except ValueError:
        return 1


def fmt_dt_filter(value, with_time=True):
    """Jinja filter: '2026-11-10 14:30:00' -> '10 Nov 2026, 14:30'."""
    if not value:
        return "\u2014"
    try:
        d = parse_dt(value)
    except (ValueError, TypeError):
        return value
    return d.strftime("%d %b %Y, %H:%M" if with_time else "%d %b %Y")
