"""Registration, login (with lockout), logout and password change."""
from datetime import timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for, g
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .utils import (COMPLAINANT_ROLES, EMAIL_RE, PHONE_RE, audit, clean, login_required, now, now_str,
                    safe_next, validate_password)

bp = Blueprint("auth", __name__)
HASH_METHOD = "pbkdf2:sha256"
_DUMMY = {}


def hash_password(pw):
    return generate_password_hash(pw, method=HASH_METHOD)


def _dummy_hash():
    if "h" not in _DUMMY:
        _DUMMY["h"] = hash_password("not-a-real-password")
    return _DUMMY["h"]


def _lock_minutes(email):
    entry = current_app.extensions["login_attempts"].get(email)
    if entry and entry.get("locked_until") and entry["locked_until"] > now():
        return max(1, int((entry["locked_until"] - now()).total_seconds() // 60) + 1)
    return 0


def _record_failure(email):
    store = current_app.extensions["login_attempts"]
    entry = store.setdefault(email, {"count": 0, "locked_until": None})
    if entry["locked_until"] and entry["locked_until"] <= now():
        entry.update(count=0, locked_until=None)
    entry["count"] += 1
    if entry["count"] >= current_app.config["LOGIN_MAX_ATTEMPTS"]:
        entry["locked_until"] = now() + timedelta(minutes=current_app.config["LOGIN_LOCK_MINUTES"])


@bp.route("/register", methods=["GET", "POST"])
def register():
    db = get_db()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()
    form = {}
    if request.method == "POST":
        f = request.form
        form = {k: clean(f.get(k), 120) for k in ("name", "email", "role", "department_id", "phone")}
        form["email"] = form["email"].lower()
        pw, pw2 = f.get("password", ""), f.get("password2", "")
        errors = []
        if len(form["name"]) < 2:
            errors.append("Please enter your full name.")
        if not EMAIL_RE.match(form["email"]):
            errors.append("Please enter a valid e-mail address.")
        elif db.execute("SELECT 1 FROM users WHERE email = ?", (form["email"],)).fetchone():
            errors.append("An account with this e-mail already exists.")
        if form["role"] not in COMPLAINANT_ROLES:
            errors.append("Please choose whether you are a student or a staff member.")
        dept = None
        if form["department_id"].isdigit():
            dept = db.execute("SELECT id FROM departments WHERE id = ?", (int(form["department_id"]),)).fetchone()
        if dept is None:
            errors.append("Please choose your department.")
        if form["phone"] and not PHONE_RE.match(form["phone"]):
            errors.append("The phone number may only contain digits, spaces, + and - (7 to 15 characters).")
        missing = validate_password(pw)
        if missing:
            errors.append("Password must contain " + ", ".join(missing) + ".")
        if pw != pw2:
            errors.append("The two passwords do not match.")
        if not f.get("consent"):
            errors.append("You must agree to the privacy policy to create an account.")
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash, role, department_id, phone, is_active, "
                "consent_given_at, created_at) VALUES (?,?,?,?,?,?,1,?,?)",
                (form["name"], form["email"], hash_password(pw), form["role"], dept["id"],
                 form["phone"] or None, now_str(), now_str()))
            audit(db, cur.lastrowid, "register", "user", cur.lastrowid)
            db.commit()
            flash("Account created. You can log in now.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html", departments=departments, form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("complaints.dashboard"))
    if request.method == "POST":
        db = get_db()
        email = clean(request.form.get("email"), 120).lower()
        password = request.form.get("password", "")
        wait = _lock_minutes(email)
        if wait:
            flash(f"Too many failed attempts. Please try again in about {wait} minute(s).", "danger")
            return render_template("login.html", email=email), 429
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        ok = check_password_hash(user["password_hash"] if user else _dummy_hash(), password)
        if user and ok and user["is_active"]:
            current_app.extensions["login_attempts"].pop(email, None)
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            audit(db, user["id"], "login", "user", user["id"])
            db.commit()
            return redirect(safe_next(request.args.get("next")) or url_for("complaints.dashboard"))
        _record_failure(email)
        audit(db, user["id"] if user else None, "login_failed", "user", user["id"] if user else None)
        db.commit()
        flash("Invalid email or password." if not (user and ok) else "This account has been deactivated.", "danger")
        return render_template("login.html", email=email), 401
    return render_template("login.html", email="")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    db = get_db()
    audit(db, g.user["id"], "logout", "user", g.user["id"])
    db.commit()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        db = get_db()
        current, new, new2 = (request.form.get(k, "") for k in ("current", "new", "new2"))
        errors = []
        if not check_password_hash(g.user["password_hash"], current):
            errors.append("Your current password is incorrect.")
        missing = validate_password(new)
        if missing:
            errors.append("New password must contain " + ", ".join(missing) + ".")
        if new != new2:
            errors.append("The two new passwords do not match.")
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), g.user["id"]))
            audit(db, g.user["id"], "password_changed", "user", g.user["id"])
            db.commit()
            flash("Password changed.", "success")
            return redirect(url_for("complaints.dashboard"))
    return render_template("change_password.html")
