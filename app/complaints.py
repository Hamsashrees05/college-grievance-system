"""Complaint submission, tracking, replies, attachments, feedback and reopening."""
import uuid
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template, request,
                   send_from_directory, url_for)
from werkzeug.utils import secure_filename

from . import services as svc
from .db import get_db
from .utils import (COMPLAINANT_ROLES, STAFF_ROLES, audit, clean, login_required, now_str, page_arg, roles_required)

bp = Blueprint("complaints", __name__)
MAGIC = {"pdf": (b"%PDF",), "png": (b"\x89PNG\r\n\x1a\n",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",)}


def validate_uploads(files, existing=0):
    """Return (valid_files, errors). Checks extension, size, signature and counts BEFORE anything is saved."""
    cfg = current_app.config
    valid, errors = [], []
    files = [f for f in files if f and f.filename]
    if len(files) > cfg["MAX_FILES_PER_UPLOAD"]:
        errors.append(f"You can upload at most {cfg['MAX_FILES_PER_UPLOAD']} files at a time.")
        return [], errors
    if existing + len(files) > cfg["MAX_FILES_PER_COMPLAINT"]:
        errors.append(f"A complaint can have at most {cfg['MAX_FILES_PER_COMPLAINT']} attachments.")
        return [], errors
    for f in files:
        name = secure_filename(f.filename) or "file"
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in cfg["ALLOWED_EXTENSIONS"]:
            errors.append(f"\u201c{name}\u201d: only PDF, PNG and JPG files are allowed.")
            continue
        data = f.read(cfg["MAX_FILE_SIZE"] + 1)
        if len(data) > cfg["MAX_FILE_SIZE"]:
            errors.append(f"\u201c{name}\u201d is larger than {cfg['MAX_FILE_SIZE'] // (1024 * 1024)} MB.")
        elif not any(data.startswith(sig) for sig in MAGIC[ext]):
            errors.append(f"\u201c{name}\u201d does not look like a real {ext.upper()} file.")
        else:
            valid.append((name, ext, data))
    return valid, errors


def save_uploads(db, cid, valid):
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    for name, ext, data in valid:
        stored = f"{uuid.uuid4().hex}.{ext}"
        (folder / stored).write_bytes(data)
        db.execute("INSERT INTO attachments (complaint_id, original_name, stored_name, file_size, uploaded_at) "
                   "VALUES (?,?,?,?,?)", (cid, name, stored, len(data), now_str()))
    db.commit()


@bp.route("/dashboard")
@login_required
def dashboard():
    role = g.user["role"]
    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    if role in STAFF_ROLES:
        return redirect(url_for("officer.queue"))
    db = get_db()
    counts = {r["status"]: r["n"] for r in db.execute(
        "SELECT status, COUNT(*) AS n FROM complaints WHERE user_id = ? GROUP BY status", (g.user["id"],))}
    data = svc.list_complaints(db, g.user, request.args, page_arg())
    return render_template("dashboard.html", data=data, counts=counts, total=sum(counts.values()),
                           statuses=svc.ALL_STATUSES)


@bp.route("/complaints/new", methods=["GET", "POST"])
@roles_required(*COMPLAINANT_ROLES)
def new():
    db = get_db()
    categories = db.execute("SELECT c.*, d.name AS department_name FROM categories c "
                            "JOIN departments d ON d.id = c.department_id ORDER BY c.name").fetchall()
    form = {}
    if request.method == "POST":
        f = request.form
        form = {"category_id": clean(f.get("category_id")), "title": clean(f.get("title"), 150),
                "description": clean(f.get("description"), 5000), "priority": clean(f.get("priority")),
                "anonymous": bool(f.get("anonymous"))}
        errors = []
        cat = db.execute("SELECT id FROM categories WHERE id = ?", (int(form["category_id"]),)).fetchone() \
            if form["category_id"].isdigit() else None
        if cat is None:
            errors.append("Please choose a category.")
        if len(form["title"]) < 5:
            errors.append("The title must be at least 5 characters.")
        if len(form["description"]) < 20:
            errors.append("Please describe the problem in at least 20 characters so it can be handled properly.")
        if form["priority"] not in svc.PRIORITIES:
            errors.append("Please choose a priority.")
        if not f.get("consent"):
            errors.append("Please confirm that the information is true and that you agree to its processing.")
        valid, upload_errors = validate_uploads(request.files.getlist("files"))
        errors += upload_errors
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            cid = svc.create_complaint(db, g.user, cat["id"], form["title"], form["description"],
                                       form["priority"], form["anonymous"])
            save_uploads(db, cid, valid)
            flash("Your complaint has been submitted. Keep the complaint ID to track it.", "success")
            return redirect(url_for("complaints.detail", cid=cid))
    return render_template("complaint_new.html", categories=categories, form=form, priorities=svc.PRIORITIES)


@bp.route("/complaints/<int:cid>")
@login_required
def detail(cid):
    db = get_db()
    c = svc.get_complaint(db, g.user, cid)
    if c is None:
        abort(404)  # also used for "not yours" so existence is not revealed
    is_staff = g.user["role"] in STAFF_ROLES
    is_owner = g.user["id"] == c["user_id"]
    if c["is_anonymous"] and not is_owner and svc.can_see_identity(c, g.user):
        audit(db, g.user["id"], "view_identity", "complaint", cid, "Viewed identity of anonymous complainant")
        db.commit()
    responses = db.execute(
        "SELECT r.*, u.name AS responder_name, u.role AS responder_role FROM responses r "
        "JOIN users u ON u.id = r.responder_id WHERE r.complaint_id = ? ORDER BY r.id", (cid,)).fetchall()
    if not is_staff:
        responses = [r for r in responses if not r["is_internal"]]
    attachments = db.execute("SELECT * FROM attachments WHERE complaint_id = ? ORDER BY id", (cid,)).fetchall()
    timeline = db.execute(
        "SELECT action, details, created_at FROM audit_logs WHERE entity = 'complaint' AND entity_id = ? "
        "AND action IN ('complaint_created','status_changed','status_override','escalated') ORDER BY id", (cid,)).fetchall()
    escalations = db.execute("SELECT * FROM escalations WHERE complaint_id = ? ORDER BY id", (cid,)).fetchall() \
        if is_staff else []
    feedback = db.execute("SELECT * FROM feedback WHERE complaint_id = ?", (cid,)).fetchone()
    nxt = svc.allowed_next(c, g.user, current_app.config["REOPEN_WINDOW_DAYS"])
    assignee = svc.current_assignee(db, cid) if is_staff else None
    return render_template(
        "complaint_detail.html", c=c, responses=responses, attachments=attachments, timeline=timeline,
        escalations=escalations, feedback=feedback, assignee=assignee, is_staff=is_staff, is_owner=is_owner,
        next_statuses=nxt if is_staff else [],
        can_reply=c["status"] not in ("Closed", "Rejected") or is_staff,
        can_upload=is_owner and c["status"] in svc.OPEN_STATUSES and len(attachments) < current_app.config["MAX_FILES_PER_COMPLAINT"],
        can_feedback=is_owner and c["status"] == "Resolved" and feedback is None,
        can_reopen=is_owner and "Reopened" in nxt,
        can_escalate=is_staff and c["escalation_level"] < 3 and c["status"] in svc.OPEN_STATUSES,
        owner_label=svc.complainant_label(c, g.user), overdue=svc.is_overdue(c))


def _load(cid):
    c = svc.get_complaint(get_db(), g.user, cid)
    if c is None:
        abort(404)
    return c


@bp.route("/complaints/<int:cid>/reply", methods=["POST"])
@login_required
def reply(cid):
    c, db = _load(cid), get_db()
    is_staff = g.user["role"] in STAFF_ROLES
    message = clean(request.form.get("message"), 2000)
    internal = is_staff and request.form.get("internal") == "1"
    if len(message) < 2:
        flash("Please type a message.", "danger")
    elif c["status"] in ("Closed", "Rejected") and not is_staff:
        flash("This complaint is closed. Use \u201cReopen\u201d if the problem is not solved.", "warning")
    else:
        svc.add_response(db, cid, g.user, message, internal)
        flash("Internal note saved." if internal else "Your reply was sent.", "success")
    return redirect(url_for("complaints.detail", cid=cid))


@bp.route("/complaints/<int:cid>/upload", methods=["POST"])
@roles_required(*COMPLAINANT_ROLES)
def upload(cid):
    c, db = _load(cid), get_db()
    if c["status"] not in svc.OPEN_STATUSES:
        flash("Files can only be added while a complaint is open.", "warning")
        return redirect(url_for("complaints.detail", cid=cid))
    existing = db.execute("SELECT COUNT(*) FROM attachments WHERE complaint_id = ?", (cid,)).fetchone()[0]
    valid, errors = validate_uploads(request.files.getlist("files"), existing)
    if not valid and not errors:
        errors = ["Please choose a file to upload."]
    if errors:
        for e in errors:
            flash(e, "danger")
    else:
        save_uploads(db, cid, valid)
        audit(db, g.user["id"], "attachment_added", "complaint", cid, f"{len(valid)} file(s)")
        db.commit()
        flash("File(s) uploaded.", "success")
    return redirect(url_for("complaints.detail", cid=cid))


@bp.route("/complaints/<int:cid>/feedback", methods=["POST"])
@roles_required(*COMPLAINANT_ROLES)
def feedback(cid):
    c, db = _load(cid), get_db()
    rating = request.form.get("rating", "")
    try:
        svc.add_feedback(db, c, g.user, int(rating) if rating.isdigit() else 0, clean(request.form.get("comments"), 1000))
        flash("Thank you. The complaint is now closed.", "success")
    except svc.WorkflowError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("complaints.detail", cid=cid))


@bp.route("/complaints/<int:cid>/reopen", methods=["POST"])
@roles_required(*COMPLAINANT_ROLES)
def reopen(cid):
    _load(cid)
    try:
        svc.change_status(get_db(), cid, "Reopened", g.user, request.form.get("message"),
                          current_app.config["REOPEN_WINDOW_DAYS"])
        flash("The complaint has been reopened.", "success")
    except svc.WorkflowError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("complaints.detail", cid=cid))


@bp.route("/attachments/<int:aid>")
@login_required
def attachment(aid):
    db = get_db()
    a = db.execute("SELECT * FROM attachments WHERE id = ?", (aid,)).fetchone()
    if a is None or svc.get_complaint(db, g.user, a["complaint_id"]) is None:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], a["stored_name"],
                               as_attachment=True, download_name=a["original_name"])
