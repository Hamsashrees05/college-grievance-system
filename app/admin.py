"""Administrator area: dashboard, users, departments & categories, audit log, CSV export, escalation."""
import csv
import io

from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for

from . import services as svc
from .auth import hash_password
from .db import get_db
from .escalation import escalate_overdue
from .utils import (ALL_ROLES, EMAIL_RE, ROLE_LABELS, audit, clean, like_escape, now_str, page_arg, paginate,
                    roles_required, validate_password)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("")
@roles_required("admin")
def dashboard():
    db = get_db()
    one = lambda sql, p=(): db.execute(sql, p).fetchone()[0]
    marks = ",".join("?" * len(svc.SLA_RUNNING))
    stats = {
        "total": one("SELECT COUNT(*) FROM complaints"),
        "open": one(f"SELECT COUNT(*) FROM complaints WHERE status IN ({','.join('?' * len(svc.OPEN_STATUSES))})",
                    svc.OPEN_STATUSES),
        "overdue": one(f"SELECT COUNT(*) FROM complaints WHERE status IN ({marks}) AND due_date < ?",
                       list(svc.SLA_RUNNING) + [now_str()]),
        "avg_days": one("SELECT AVG(julianday(resolved_at) - julianday(created_at)) FROM complaints "
                        "WHERE resolved_at IS NOT NULL"),
        "avg_rating": one("SELECT AVG(rating) FROM feedback"),
        "users": one("SELECT COUNT(*) FROM users WHERE is_active = 1"),
    }
    by_status = db.execute("SELECT status, COUNT(*) n FROM complaints GROUP BY status").fetchall()
    by_cat = db.execute("SELECT cat.name, COUNT(*) n FROM complaints c JOIN categories cat ON cat.id = c.category_id "
                        "GROUP BY cat.id ORDER BY n DESC").fetchall()
    by_dept = db.execute(
        "SELECT d.name, COUNT(*) n, AVG(CASE WHEN c.resolved_at IS NOT NULL THEN "
        "julianday(c.resolved_at) - julianday(c.created_at) END) AS avg_days "
        "FROM complaints c JOIN categories cat ON cat.id = c.category_id JOIN departments d ON d.id = cat.department_id "
        "GROUP BY d.id ORDER BY n DESC").fetchall()
    monthly = db.execute("SELECT strftime('%Y-%m', created_at) m, COUNT(*) n FROM complaints GROUP BY m ORDER BY m").fetchall()
    chart = {"status": {"labels": [r["status"] for r in by_status], "values": [r["n"] for r in by_status]},
             "category": {"labels": [r["name"] for r in by_cat], "values": [r["n"] for r in by_cat]},
             "monthly": {"labels": [r["m"] for r in monthly], "values": [r["n"] for r in monthly]}}
    return render_template("admin_dashboard.html", stats=stats, chart=chart, by_dept=by_dept)


@bp.route("/escalate-now", methods=["POST"])
@roles_required("admin")
def escalate_now():
    db = get_db()
    n = escalate_overdue(db)
    audit(db, g.user["id"], "escalation_run", "system", None, f"Manual escalation check: {n} escalated")
    db.commit()
    flash(f"Escalation check finished: {n} complaint(s) escalated." if n else
          "Escalation check finished: no overdue complaints needed escalation.", "success" if n else "info")
    return redirect(url_for("admin.dashboard"))


# ---------------------------------------------------------------------- users
@bp.route("/users")
@roles_required("admin")
def users():
    db = get_db()
    q = clean(request.args.get("q"), 80)
    where, params = "", []
    if q:
        where, params = " WHERE (u.name LIKE ? ESCAPE '\\' OR u.email LIKE ? ESCAPE '\\')", [like_escape(q)] * 2
    data = paginate(db, f"SELECT COUNT(*) FROM users u{where}",
                    f"SELECT u.*, d.name AS department_name FROM users u LEFT JOIN departments d "
                    f"ON d.id = u.department_id{where} ORDER BY u.id", params, page_arg(), 15)
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()
    return render_template("admin_users.html", data=data, departments=departments, roles=ALL_ROLES,
                           role_labels=ROLE_LABELS)


def _dept_or_none(db, raw):
    return int(raw) if raw and raw.isdigit() and db.execute(
        "SELECT 1 FROM departments WHERE id = ?", (int(raw),)).fetchone() else None


@bp.route("/users/create", methods=["POST"])
@roles_required("admin")
def create_user():
    db, f = get_db(), request.form
    name, email, role = clean(f.get("name"), 120), clean(f.get("email"), 120).lower(), clean(f.get("role"))
    dept, pw = _dept_or_none(db, f.get("department_id")), f.get("password", "")
    errors = []
    if len(name) < 2:
        errors.append("Please enter the user's name.")
    if not EMAIL_RE.match(email):
        errors.append("Please enter a valid e-mail address.")
    elif db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        errors.append("A user with this e-mail already exists.")
    if role not in ALL_ROLES:
        errors.append("Please choose a role.")
    if role in ("officer", "hod") and dept is None:
        errors.append("Officers and heads of department must belong to a department.")
    missing = validate_password(pw)
    if missing:
        errors.append("Password must contain " + ", ".join(missing) + ".")
    if errors:
        for e in errors:
            flash(e, "danger")
    else:
        cur = db.execute("INSERT INTO users (name, email, password_hash, role, department_id, is_active, created_at) "
                         "VALUES (?,?,?,?,?,1,?)", (name, email, hash_password(pw), role, dept, now_str()))
        if role == "hod":
            db.execute("UPDATE departments SET head_user_id = ? WHERE id = ? AND head_user_id IS NULL", (cur.lastrowid, dept))
        audit(db, g.user["id"], "user_created", "user", cur.lastrowid, f"Role: {role}")
        db.commit()
        flash(f"User {email} created.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:uid>/update", methods=["POST"])
@roles_required("admin")
def update_user(uid):
    db, f = get_db(), request.form
    u = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if u is None:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    role = clean(f.get("role")) if clean(f.get("role")) in ALL_ROLES else u["role"]
    dept = _dept_or_none(db, f.get("department_id"))
    active = 1 if f.get("is_active") == "1" else 0
    if uid == g.user["id"] and (not active or role != "admin"):
        flash("You cannot deactivate or demote your own account.", "danger")
    elif role in ("officer", "hod") and dept is None:
        flash("Officers and heads of department must belong to a department.", "danger")
    else:
        db.execute("UPDATE users SET role = ?, department_id = ?, is_active = ? WHERE id = ?", (role, dept, active, uid))
        if role == "hod":
            db.execute("UPDATE departments SET head_user_id = ? WHERE id = ? AND head_user_id IS NULL", (uid, dept))
        audit(db, g.user["id"], "user_updated", "user", uid, f"Role: {role}, active: {active}")
        db.commit()
        flash("User updated.", "success")
    return redirect(url_for("admin.users"))


# ------------------------------------------------------ departments & categories
@bp.route("/catalog")
@roles_required("admin")
def catalog():
    db = get_db()
    departments = db.execute("SELECT d.*, u.name AS head_name FROM departments d LEFT JOIN users u "
                             "ON u.id = d.head_user_id ORDER BY d.name").fetchall()
    categories = db.execute("SELECT c.*, d.name AS department_name FROM categories c JOIN departments d "
                            "ON d.id = c.department_id ORDER BY c.name").fetchall()
    heads = db.execute("SELECT id, name, department_id FROM users WHERE role = 'hod' AND is_active = 1 ORDER BY name").fetchall()
    return render_template("admin_catalog.html", departments=departments, categories=categories, heads=heads)


@bp.route("/departments/save", methods=["POST"])
@roles_required("admin")
def save_department():
    db, f = get_db(), request.form
    name, did = clean(f.get("name"), 80), f.get("id", "")
    head = f.get("head_user_id", "")
    head = int(head) if head.isdigit() and db.execute("SELECT 1 FROM users WHERE id = ?", (int(head),)).fetchone() else None
    if len(name) < 2:
        flash("Please enter a department name.", "danger")
    elif db.execute("SELECT 1 FROM departments WHERE name = ? AND id != ?", (name, int(did) if did.isdigit() else 0)).fetchone():
        flash("A department with this name already exists.", "danger")
    elif did.isdigit():
        db.execute("UPDATE departments SET name = ?, head_user_id = ? WHERE id = ?", (name, head, int(did)))
        audit(db, g.user["id"], "department_updated", "department", int(did), name); db.commit()
        flash("Department updated.", "success")
    else:
        cur = db.execute("INSERT INTO departments (name, head_user_id) VALUES (?,?)", (name, head))
        audit(db, g.user["id"], "department_created", "department", cur.lastrowid, name); db.commit()
        flash("Department added.", "success")
    return redirect(url_for("admin.catalog"))


@bp.route("/categories/save", methods=["POST"])
@roles_required("admin")
def save_category():
    db, f = get_db(), request.form
    name, cid = clean(f.get("name"), 80), f.get("id", "")
    dept = _dept_or_none(db, f.get("department_id"))
    sla = int(f["sla_days"]) if (f.get("sla_days") or "").isdigit() else 0
    sensitive = 1 if f.get("is_sensitive") else 0
    if len(name) < 2 or dept is None or not 1 <= sla <= 90:
        flash("Please give a name, a department and an SLA between 1 and 90 days.", "danger")
    elif db.execute("SELECT 1 FROM categories WHERE name = ? AND id != ?", (name, int(cid) if cid.isdigit() else 0)).fetchone():
        flash("A category with this name already exists.", "danger")
    elif cid.isdigit():
        db.execute("UPDATE categories SET name = ?, department_id = ?, sla_days = ?, is_sensitive = ? WHERE id = ?",
                   (name, dept, sla, sensitive, int(cid)))
        audit(db, g.user["id"], "category_updated", "category", int(cid), name); db.commit()
        flash("Category updated. New SLA values apply to future complaints.", "success")
    else:
        cur = db.execute("INSERT INTO categories (name, department_id, sla_days, is_sensitive) VALUES (?,?,?,?)",
                         (name, dept, sla, sensitive))
        audit(db, g.user["id"], "category_created", "category", cur.lastrowid, name); db.commit()
        flash("Category added.", "success")
    return redirect(url_for("admin.catalog"))


# -------------------------------------------------------------- audit & export
@bp.route("/audit")
@roles_required("admin")
def audit_log():
    db = get_db()
    action, q = clean(request.args.get("action"), 40), clean(request.args.get("q"), 80)
    where, params = [], []
    if action:
        where.append("a.action = ?"); params.append(action)
    if q:
        where.append("(u.email LIKE ? ESCAPE '\\' OR a.details LIKE ? ESCAPE '\\')"); params += [like_escape(q)] * 2
    w = (" WHERE " + " AND ".join(where)) if where else ""
    frm = f"FROM audit_logs a LEFT JOIN users u ON u.id = a.user_id{w}"
    data = paginate(db, f"SELECT COUNT(*) {frm}",
                    f"SELECT a.*, u.email AS user_email {frm} ORDER BY a.id DESC", params, page_arg(), 25)
    actions = [r[0] for r in db.execute("SELECT DISTINCT action FROM audit_logs ORDER BY action")]
    return render_template("admin_audit.html", data=data, actions=actions)


def _safe_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text  # blocks spreadsheet formula injection


@bp.route("/export.csv")
@roles_required("admin")
def export_csv():
    rows = get_db().execute(
        "SELECT c.complaint_code, c.title, cat.name AS category, d.name AS department, c.status, c.priority, "
        "c.escalation_level, c.is_anonymous, u.name AS owner, c.created_at, c.due_date, c.resolved_at "
        "FROM complaints c JOIN categories cat ON cat.id = c.category_id JOIN departments d ON d.id = cat.department_id "
        "JOIN users u ON u.id = c.user_id ORDER BY c.id").fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Complaint ID", "Title", "Category", "Department", "Status", "Priority", "Level",
                "Complainant", "Created", "Due", "Resolved"])
    for r in rows:
        w.writerow([_safe_cell(x) for x in (
            r["complaint_code"], r["title"], r["category"], r["department"], r["status"], r["priority"],
            r["escalation_level"], "Anonymous" if r["is_anonymous"] else r["owner"],
            r["created_at"], r["due_date"], r["resolved_at"])])
    audit(get_db(), g.user["id"], "csv_export", "system", None, f"{len(rows)} complaints"); get_db().commit()
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=complaints.csv"})
