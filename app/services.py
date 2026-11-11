"""Business logic: routing, visibility, workflow (status transitions), replies and feedback."""
import uuid
from datetime import timedelta

from .notifications import notify
from .utils import STAFF_ROLES, audit, like_escape, now, now_str, parse_dt

ALL_STATUSES = ["Submitted", "Under Review", "In Progress", "Awaiting Info",
                "Resolved", "Closed", "Rejected", "Reopened"]
OPEN_STATUSES = ("Submitted", "Under Review", "In Progress", "Awaiting Info", "Reopened")
SLA_RUNNING = ("Submitted", "Under Review", "In Progress", "Reopened")  # SLA clock paused while "Awaiting Info"
PRIORITIES = ["Low", "Medium", "High", "Critical"]
LEVEL_NAMES = {1: "Officer", 2: "Head of department", 3: "Grievance committee"}

# Allowed transitions. Everything else is rejected on the server.
STAFF_NEXT = {
    "Submitted": ["Under Review", "Rejected"],
    "Under Review": ["In Progress", "Awaiting Info", "Rejected"],
    "In Progress": ["Resolved", "Awaiting Info", "Rejected"],
    "Awaiting Info": ["In Progress"],
    "Reopened": ["Under Review"],
    "Resolved": [], "Closed": [], "Rejected": [],
}
OWNER_NEXT = {"Resolved": ["Closed", "Reopened"], "Closed": ["Reopened"]}
NEEDS_MESSAGE = ("Rejected", "Reopened", "Awaiting Info")


class WorkflowError(Exception):
    """A rule of the grievance workflow was violated (shown to the user as a message)."""


# ---------------------------------------------------------------- visibility
BASE_SELECT = """
SELECT c.*, cat.name AS category_name, cat.department_id AS department_id, cat.is_sensitive AS is_sensitive,
       cat.sla_days AS sla_days, d.name AS department_name, u.name AS owner_name, u.email AS owner_email,
       u.phone AS owner_phone
FROM complaints c
JOIN categories cat ON cat.id = c.category_id
JOIN departments d ON d.id = cat.department_id
JOIN users u ON u.id = c.user_id
"""


def visibility_clause(user):
    """SQL fragment (aliases c, cat) limiting which complaints this user may see."""
    role = user["role"]
    if role == "admin":
        return "1 = 1", []
    if role == "committee":
        return "(c.escalation_level = 3 OR cat.is_sensitive = 1)", []
    if role == "hod":
        return "(cat.department_id = ? AND c.escalation_level <= 2 AND cat.is_sensitive = 0)", [user["department_id"]]
    if role == "officer":
        return ("EXISTS (SELECT 1 FROM assignments a WHERE a.complaint_id = c.id "
                "AND a.officer_id = ? AND a.is_current = 1)"), [user["id"]]
    return "c.user_id = ?", [user["id"]]


def get_complaint(db, user, cid):
    clause, params = visibility_clause(user)
    return db.execute(f"{BASE_SELECT} WHERE c.id = ? AND {clause}", [cid] + params).fetchone()


def complainant_label(c, viewer):
    """Anonymity rule: only the owner, committee and admin ever see an anonymous complainant's identity."""
    if c["is_anonymous"] and viewer["id"] != c["user_id"] and viewer["role"] not in ("committee", "admin"):
        return "Anonymous"
    return c["owner_name"]


def can_see_identity(c, viewer):
    return complainant_label(c, viewer) != "Anonymous"


def is_overdue(c):
    return c["status"] in SLA_RUNNING and c["due_date"] < now_str()


def list_complaints(db, user, args, page, per_page=10):
    from .utils import paginate
    clause, params = visibility_clause(user)
    where, params = [clause], list(params)
    if args.get("status") in ALL_STATUSES:
        where.append("c.status = ?"); params.append(args["status"])
    if args.get("priority") in PRIORITIES:
        where.append("c.priority = ?"); params.append(args["priority"])
    if (args.get("category") or "").isdigit():
        where.append("c.category_id = ?"); params.append(int(args["category"]))
    if args.get("overdue") == "1":
        where.append("c.status IN ('Submitted','Under Review','In Progress','Reopened') AND c.due_date < ?")
        params.append(now_str())
    q = (args.get("q") or "").strip()[:80]
    if q:
        where.append("(c.complaint_code LIKE ? ESCAPE '\\' OR c.title LIKE ? ESCAPE '\\')")
        params += [like_escape(q), like_escape(q)]
    sql_where = " WHERE " + " AND ".join(where)
    frm = ("FROM complaints c JOIN categories cat ON cat.id = c.category_id "
           "JOIN departments d ON d.id = cat.department_id JOIN users u ON u.id = c.user_id")
    return paginate(
        db, f"SELECT COUNT(*) {frm}{sql_where}",
        f"SELECT c.*, cat.name AS category_name, d.name AS department_name, u.name AS owner_name, "
        f"cat.is_sensitive AS is_sensitive {frm}{sql_where} ORDER BY c.updated_at DESC, c.id DESC",
        params, page, per_page)


# ------------------------------------------------------------------- routing
def _least_loaded(db, role, dept_id=None):
    sql = ("SELECT u.id, (SELECT COUNT(*) FROM assignments a JOIN complaints c ON c.id = a.complaint_id "
           "WHERE a.officer_id = u.id AND a.is_current = 1 AND c.status IN "
           "('Submitted','Under Review','In Progress','Awaiting Info','Reopened')) AS load "
           "FROM users u WHERE u.role = ? AND u.is_active = 1")
    params = [role]
    if dept_id is not None:
        sql += " AND u.department_id = ?"
        params.append(dept_id)
    row = db.execute(sql + " ORDER BY load, u.id LIMIT 1", params).fetchone()
    return row["id"] if row else None


def pick_assignee(db, dept_id, level):
    """Level 1 -> least-loaded officer (fallback HOD); level 2 -> HOD; level 3 -> committee. Admin is last resort."""
    chosen = None
    if level == 1:
        chosen = _least_loaded(db, "officer", dept_id) or _least_loaded(db, "hod", dept_id)
    elif level == 2:
        head = db.execute("SELECT u.id FROM departments d JOIN users u ON u.id = d.head_user_id "
                          "WHERE d.id = ? AND u.is_active = 1", (dept_id,)).fetchone()
        chosen = head["id"] if head else _least_loaded(db, "hod", dept_id)
    else:
        chosen = _least_loaded(db, "committee")
    return chosen or _least_loaded(db, "admin")


def assign(db, cid, user_id, level):
    db.execute("UPDATE assignments SET is_current = 0 WHERE complaint_id = ?", (cid,))
    db.execute("INSERT INTO assignments (complaint_id, officer_id, level, assigned_at, is_current) VALUES (?,?,?,?,1)",
               (cid, user_id, level, now_str()))


def current_assignee(db, cid):
    return db.execute("SELECT u.* FROM assignments a JOIN users u ON u.id = a.officer_id "
                      "WHERE a.complaint_id = ? AND a.is_current = 1", (cid,)).fetchone()


def compute_due(created, sla_days, priority):
    days = max(1, sla_days // 2) if priority in ("High", "Critical") else sla_days
    return created + timedelta(days=days)


# ----------------------------------------------------------------- complaints
def create_complaint(db, user, category_id, title, description, priority, anonymous, created_at=None):
    cat = db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    created = created_at or now()
    due = compute_due(created, cat["sla_days"], priority)
    level = 3 if cat["is_sensitive"] else 1
    stamp = created.strftime("%Y-%m-%d %H:%M:%S")
    cur = db.execute(
        "INSERT INTO complaints (complaint_code, user_id, category_id, title, description, priority, is_anonymous, "
        "status, escalation_level, created_at, updated_at, due_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("TMP-" + uuid.uuid4().hex, user["id"], category_id, title, description, priority,
         1 if anonymous else 0, "Submitted", level, stamp, stamp, due.strftime("%Y-%m-%d %H:%M:%S")))
    cid = cur.lastrowid
    code = f"CGMS-{created.year}-{cid:05d}"
    db.execute("UPDATE complaints SET complaint_code = ? WHERE id = ?", (code, cid))
    assignee = pick_assignee(db, cat["department_id"], level)
    assign(db, cid, assignee, level)
    audit(db, user["id"], "complaint_created", "complaint", cid,
          f"Complaint {code} submitted in category {cat['name']}" + (" (anonymous)" if anonymous else ""))
    notify(db, assignee, f"New complaint {code} ({priority} priority): {title}", cid)
    notify(db, user["id"], f"Your complaint {code} was received. Track it from your dashboard.", cid)
    db.commit()
    return cid


def allowed_next(c, user, reopen_window_days=7):
    """Statuses this user may move the complaint to right now."""
    if user["role"] == "admin":
        return [s for s in ALL_STATUSES if s != c["status"]]
    if user["id"] == c["user_id"]:
        opts = list(OWNER_NEXT.get(c["status"], []))
        if "Reopened" in opts:
            ref = c["resolved_at"]
            if not ref or (now() - parse_dt(ref)).days >= reopen_window_days:
                opts.remove("Reopened")
        return opts
    if user["role"] in STAFF_ROLES:
        return list(STAFF_NEXT.get(c["status"], []))
    return []


def add_response(db, cid, user, message, internal=False, notify_people=True):
    c = db.execute("SELECT * FROM complaints WHERE id = ?", (cid,)).fetchone()
    db.execute("INSERT INTO responses (complaint_id, responder_id, message, is_internal, created_at) VALUES (?,?,?,?,?)",
               (cid, user["id"], message, 1 if internal else 0, now_str()))
    db.execute("UPDATE complaints SET updated_at = ? WHERE id = ?", (now_str(), cid))
    audit(db, user["id"], "internal_note" if internal else "reply_added", "complaint", cid)
    if notify_people and not internal:
        if user["id"] == c["user_id"]:
            a = current_assignee(db, cid)
            if a:
                notify(db, a["id"], f"New reply on complaint {c['complaint_code']}.", cid)
            if c["status"] == "Awaiting Info":  # information supplied -> work resumes
                _set_status(db, c, "In Progress", user["id"], "status_changed")
        else:
            notify(db, c["user_id"], f"There is a new reply on your complaint {c['complaint_code']}.", cid)
    db.commit()


def _set_status(db, c, new_status, actor_id, action="status_changed"):
    old = c["status"]
    resolved_at = c["resolved_at"]
    due = c["due_date"]
    if new_status == "Resolved":
        resolved_at = now_str()
    elif new_status == "Reopened":
        due = compute_due(now(), c["sla_days"] if "sla_days" in c.keys() else 7, c["priority"]).strftime("%Y-%m-%d %H:%M:%S")
        resolved_at = None
    db.execute("UPDATE complaints SET status = ?, updated_at = ?, resolved_at = ?, due_date = ? WHERE id = ?",
               (new_status, now_str(), resolved_at, due, c["id"]))
    audit(db, actor_id, action, "complaint", c["id"], f"Status changed: {old} \u2192 {new_status}")


def change_status(db, cid, new_status, actor, message=None, reopen_window_days=7):
    c = db.execute(
        "SELECT c.*, cat.sla_days AS sla_days FROM complaints c JOIN categories cat ON cat.id = c.category_id "
        "WHERE c.id = ?", (cid,)).fetchone()
    old = c["status"]
    if new_status not in ALL_STATUSES:
        raise WorkflowError("Unknown status.")
    if new_status not in allowed_next(c, actor, reopen_window_days):
        raise WorkflowError(f"A complaint cannot be moved from \u201c{old}\u201d to \u201c{new_status}\u201d.")
    message = (message or "").strip()
    if new_status in NEEDS_MESSAGE and len(message) < 5:
        raise WorkflowError(f"Please give a reason or message (at least 5 characters) when setting \u201c{new_status}\u201d.")
    is_override = actor["role"] == "admin" and new_status not in STAFF_NEXT.get(old, []) \
        and new_status not in OWNER_NEXT.get(old, [])
    _set_status(db, c, new_status, actor["id"], "status_override" if is_override else "status_changed")
    if message:
        db.execute("INSERT INTO responses (complaint_id, responder_id, message, is_internal, created_at) VALUES (?,?,?,0,?)",
                   (cid, actor["id"], message, now_str()))
    if actor["id"] == c["user_id"]:
        a = current_assignee(db, cid)
        if a:
            notify(db, a["id"], f"Complaint {c['complaint_code']} is now \u201c{new_status}\u201d (set by the complainant).", cid)
    else:
        notify(db, c["user_id"], f"Your complaint {c['complaint_code']} is now \u201c{new_status}\u201d.", cid)
    db.commit()


def add_feedback(db, c, user, rating, comments):
    if user["id"] != c["user_id"]:
        raise WorkflowError("Only the complainant can give feedback.")
    if c["status"] != "Resolved":
        raise WorkflowError("Feedback can only be given once, after the complaint has been resolved.")
    if db.execute("SELECT 1 FROM feedback WHERE complaint_id = ?", (c["id"],)).fetchone():
        raise WorkflowError("Feedback has already been submitted for this complaint.")
    if rating not in (1, 2, 3, 4, 5):
        raise WorkflowError("Please choose a rating from 1 to 5.")
    db.execute("INSERT INTO feedback (complaint_id, rating, comments, created_at) VALUES (?,?,?,?)",
               (c["id"], rating, comments or None, now_str()))
    _set_status(db, c, "Closed", user["id"])
    a = current_assignee(db, c["id"])
    if a:
        notify(db, a["id"], f"Complaint {c['complaint_code']} was confirmed and closed (rating {rating}/5).", c["id"])
    db.commit()
