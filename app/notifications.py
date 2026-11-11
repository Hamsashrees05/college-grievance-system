"""In-app notifications + simulated (or real, if SMTP is configured) e-mail."""
import smtplib
from email.message import EmailMessage
from pathlib import Path

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from .db import get_db
from .utils import login_required, now_str, page_arg, paginate

bp = Blueprint("notifications", __name__)


def _send_email(to_addr, subject, body):
    """Write to logs/emails.log; also send via SMTP when configured. Never raises."""
    try:
        cfg = current_app.config
        log_dir = Path(cfg["LOG_FOLDER"])
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "emails.log", "a", encoding="utf-8") as fh:
            fh.write(f"[{now_str()}] TO: {to_addr} | SUBJECT: {subject}\n{body}\n---\n")
        if cfg.get("SMTP_HOST"):
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = cfg["SMTP_FROM"], to_addr, subject
            msg.set_content(body)
            with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=10) as smtp:
                smtp.starttls()
                if cfg.get("SMTP_USER"):
                    smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"] or "")
                smtp.send_message(msg)
    except Exception as exc:  # e-mail problems must never break a request
        current_app.logger.warning("E-mail delivery failed: %s", exc)


def notify(db, user_id, message, complaint_id=None):
    """Create an in-app notification. Messages must never contain an anonymous complainant's identity."""
    db.execute(
        "INSERT INTO notifications (user_id, complaint_id, message, is_read, created_at) VALUES (?,?,?,0,?)",
        (user_id, complaint_id, message, now_str()),
    )
    row = db.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row:
        _send_email(row["email"], "CGMS notification", message)


@bp.route("/notifications")
@login_required
def list_notifications():
    db = get_db()
    data = paginate(
        db, "SELECT COUNT(*) FROM notifications WHERE user_id = ?",
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC",
        [g.user["id"]], page_arg(), 15)
    return render_template("notifications.html", data=data)


@bp.route("/notifications/<int:nid>/read", methods=["POST"])
@login_required
def mark_read(nid):
    db = get_db()
    row = db.execute("SELECT * FROM notifications WHERE id = ? AND user_id = ?", (nid, g.user["id"])).fetchone()
    if row is None:
        return redirect(url_for("notifications.list_notifications"))
    db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (nid,))
    db.commit()
    if row["complaint_id"]:
        return redirect(url_for("complaints.detail", cid=row["complaint_id"]))
    return redirect(url_for("notifications.list_notifications"))


@bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user["id"],))
    db.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications.list_notifications"))
