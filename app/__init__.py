"""Application factory for the College Complaint & Grievance Management System."""
from flask import Flask, g, render_template, session
from flask_wtf.csrf import CSRFError, CSRFProtect

from . import services as svc
from .config import build_config
from .db import close_db, get_db
from .utils import ROLE_LABELS, STAFF_ROLES, fmt_dt_filter

csrf = CSRFProtect()


def create_app(overrides=None):
    app = Flask(__name__, instance_relative_config=True)
    build_config(app, overrides)
    app.extensions["login_attempts"] = {}
    csrf.init_app(app)
    app.teardown_appcontext(close_db)

    from . import admin, auth, complaints, notifications, officer, pages
    for module in (pages, auth, complaints, officer, admin, notifications):
        app.register_blueprint(module.bp)

    @app.before_request
    def load_user():
        from flask import request
        g.user = None
        if request.endpoint == "static":
            return
        uid = session.get("user_id")
        if uid:
            user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
            if user and user["is_active"]:
                g.user = user
            else:
                session.clear()

    @app.context_processor
    def inject():
        unread = 0
        if g.get("user"):
            unread = get_db().execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
                                      (g.user["id"],)).fetchone()[0]
        return {"current_user": g.get("user"), "unread_count": unread, "ROLE_LABELS": ROLE_LABELS,
                "STAFF_ROLES": STAFF_ROLES, "LEVEL_NAMES": svc.LEVEL_NAMES,
                "complainant_label": svc.complainant_label, "is_overdue": svc.is_overdue}

    app.jinja_env.filters["dt"] = fmt_dt_filter

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:; font-src 'self' https://cdn.jsdelivr.net; "
            "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        if g.get("user"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def error_page(code, title, text):
        return render_template("error.html", code=code, title=title, text=text), code

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return error_page(400, "Request could not be verified",
                          "Your form expired or was not sent from this site. Go back, reload the page and try again.")

    @app.errorhandler(403)
    def forbidden(_e):
        return error_page(403, "You do not have access", "Your account is not allowed to open this page.")

    @app.errorhandler(404)
    def not_found(_e):
        return error_page(404, "Page not found", "The page or complaint you asked for does not exist, or you cannot view it.")

    @app.errorhandler(413)
    def too_large(_e):
        return error_page(413, "Upload too large", "The files you sent are too large. Each file can be at most 5 MB.")

    @app.errorhandler(500)
    def server_error(_e):
        return error_page(500, "Something went wrong", "An unexpected error occurred. Please try again later.")

    return app
