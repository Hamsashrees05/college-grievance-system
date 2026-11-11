"""Escalation engine: Level 1 (officer) -> Level 2 (HOD) -> Level 3 (grievance committee)."""
import os

from .db import connect
from .notifications import notify
from .services import (LEVEL_NAMES, SLA_RUNNING, WorkflowError, assign, compute_due, pick_assignee)
from .utils import audit, now, now_str


def escalate(db, c, reason, actor_id=None):
    """Move one complaint up a level, reassign it, restart its SLA and notify everyone concerned."""
    level = c["escalation_level"]
    if level >= 3:
        raise WorkflowError("This complaint is already at the highest escalation level.")
    to_level = level + 1
    cat = db.execute("SELECT department_id, sla_days FROM categories WHERE id = ?", (c["category_id"],)).fetchone()
    assignee = pick_assignee(db, cat["department_id"], to_level)
    new_due = compute_due(now(), cat["sla_days"], c["priority"]).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE complaints SET escalation_level = ?, due_date = ?, updated_at = ? WHERE id = ?",
               (to_level, new_due, now_str(), c["id"]))
    assign(db, c["id"], assignee, to_level)
    db.execute("INSERT INTO escalations (complaint_id, from_level, to_level, reason, escalated_at) VALUES (?,?,?,?,?)",
               (c["id"], level, to_level, reason, now_str()))
    audit(db, actor_id, "escalated", "complaint", c["id"],
          f"Escalated from Level {level} ({LEVEL_NAMES[level]}) to Level {to_level} ({LEVEL_NAMES[to_level]})")
    notify(db, assignee, f"Complaint {c['complaint_code']} was escalated to you "
                         f"(Level {to_level}, {LEVEL_NAMES[to_level]}).", c["id"])
    notify(db, c["user_id"], f"Your complaint {c['complaint_code']} was escalated to Level {to_level} "
                             f"({LEVEL_NAMES[to_level]}) for faster attention.", c["id"])
    db.commit()


def escalate_overdue(db):
    """Escalate every complaint whose deadline has passed. Returns the number escalated."""
    marks = ",".join("?" * len(SLA_RUNNING))
    rows = db.execute(
        f"SELECT * FROM complaints WHERE status IN ({marks}) AND due_date < ? AND escalation_level < 3",
        list(SLA_RUNNING) + [now_str()]).fetchall()
    for c in rows:
        escalate(db, c, "SLA deadline passed without resolution (automatic escalation).", None)
    return len(rows)


def start_scheduler(app):
    """Start the daily job once. Called from run.py (never from create_app) so the reloader cannot start it twice."""
    if not app.config.get("SCHEDULER_ENABLED") or "scheduler" in app.extensions:
        return None
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return None
    from apscheduler.schedulers.background import BackgroundScheduler

    def job():
        with app.app_context():
            db = connect(app.config["DATABASE"])
            try:
                n = escalate_overdue(db)
                app.logger.info("Scheduled escalation check: %s complaint(s) escalated.", n)
            finally:
                db.close()

    sched = BackgroundScheduler(daemon=True)
    sched.add_job(job, "cron", hour=app.config["ESCALATION_HOUR"], minute=0, id="daily_escalation")
    sched.start()
    app.extensions["scheduler"] = sched
    return sched
