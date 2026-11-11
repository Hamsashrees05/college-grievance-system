"""Work queue and case actions for officers, HODs, the grievance committee and admins."""
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from . import services as svc
from .db import get_db
from .escalation import escalate
from .utils import STAFF_ROLES, clean, page_arg, roles_required

bp = Blueprint("officer", __name__)


@bp.route("/queue")
@roles_required(*STAFF_ROLES)
def queue():
    db = get_db()
    data = svc.list_complaints(db, g.user, request.args, page_arg())
    categories = db.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
    return render_template("queue.html", data=data, categories=categories, statuses=svc.ALL_STATUSES,
                           priorities=svc.PRIORITIES)


def _load(cid):
    c = svc.get_complaint(get_db(), g.user, cid)
    if c is None:
        abort(404)
    return c


@bp.route("/complaints/<int:cid>/status", methods=["POST"])
@roles_required(*STAFF_ROLES)
def set_status(cid):
    _load(cid)
    try:
        svc.change_status(get_db(), cid, clean(request.form.get("new_status")), g.user,
                          request.form.get("message"), current_app.config["REOPEN_WINDOW_DAYS"])
        flash("Status updated.", "success")
    except svc.WorkflowError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("complaints.detail", cid=cid))


@bp.route("/complaints/<int:cid>/escalate", methods=["POST"])
@roles_required(*STAFF_ROLES)
def manual_escalate(cid):
    c = _load(cid)
    reason = clean(request.form.get("reason"), 500)
    if len(reason) < 5:
        flash("Please give a reason for escalating (at least 5 characters).", "danger")
    elif c["status"] not in svc.OPEN_STATUSES:
        flash("Only open complaints can be escalated.", "danger")
    else:
        try:
            escalate(get_db(), c, f"Manual escalation: {reason}", g.user["id"])
            flash("Complaint escalated to the next level.", "success")
            if svc.get_complaint(get_db(), g.user, cid) is None:  # it now belongs to a higher level
                return redirect(url_for("officer.queue"))
        except svc.WorkflowError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("complaints.detail", cid=cid))
