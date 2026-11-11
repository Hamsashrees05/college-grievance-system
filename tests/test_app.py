import io
import re

import pytest

from app.escalation import escalate_overdue
from app.services import allowed_next, get_complaint
from conftest import PASSWORD, make_app

STUDENT1, STUDENT2 = "student1@college.example", "student2@college.example"
ADMIN, COMMITTEE = "admin@college.example", "committee@college.example"
PDF = b"%PDF-1.4\n%test file\n"


def category_id(db, name):
    return db.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()["id"]


def submit(client, db, category="Hostel Facilities", anonymous=False, files=None, title="Broken fan in room 210"):
    data = {"category_id": category_id(db, category), "title": title,
            "description": "The ceiling fan in my room has stopped working completely for a week.",
            "priority": "Medium", "consent": "1"}
    if anonymous:
        data["anonymous"] = "1"
    if files:
        data["files"] = files
    return client.post("/complaints/new", data=data, content_type="multipart/form-data")


def latest(db):
    return db.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 1").fetchone()


def officer_email(db, cid):
    return db.execute("SELECT u.email FROM assignments a JOIN users u ON u.id = a.officer_id "
                      "WHERE a.complaint_id = ? AND a.is_current = 1", (cid,)).fetchone()["email"]


# 1
def test_wrong_password_rejected(app):
    c = app.test_client()
    r = c.post("/login", data={"email": STUDENT1, "password": "Wrong@12345"})
    assert r.status_code == 401 and b"Invalid email or password" in r.data
    assert c.get("/dashboard").status_code == 302  # still logged out


# 2
def test_weak_password_rejected_at_registration(app, db):
    c = app.test_client()
    dept = db.execute("SELECT id FROM departments LIMIT 1").fetchone()["id"]
    r = c.post("/register", data={"name": "New Person", "email": "new@college.example", "role": "student",
                                  "department_id": dept, "password": "abc", "password2": "abc", "consent": "1"})
    assert r.status_code == 200 and b"Password must contain" in r.data
    assert db.execute("SELECT 1 FROM users WHERE email = 'new@college.example'").fetchone() is None


# 3
def test_student_cannot_view_another_students_complaint(app, db, login):
    s1 = login(STUDENT1)
    submit(s1, db)
    cid = latest(db)["id"]
    assert s1.get(f"/complaints/{cid}").status_code == 200
    assert login(STUDENT2).get(f"/complaints/{cid}").status_code == 404


# 4
def test_submission_creates_code_and_routes_to_correct_department(app, db, login):
    r = submit(login(STUDENT1), db, "Library Services")
    assert r.status_code == 302
    c = latest(db)
    assert re.fullmatch(r"CGMS-\d{4}-\d{5}", c["complaint_code"])
    dept = db.execute("SELECT u.department_id, u.role FROM assignments a JOIN users u ON u.id = a.officer_id "
                      "WHERE a.complaint_id = ? AND a.is_current = 1", (c["id"],)).fetchone()
    lib = db.execute("SELECT id FROM departments WHERE name = 'Library'").fetchone()["id"]
    assert dept["department_id"] == lib and dept["role"] == "officer"
    assert c["status"] == "Submitted" and c["escalation_level"] == 1


# 5
def test_anonymous_identity_hidden_from_officer_but_not_admin(app, db, login):
    submit(login(STUDENT1), db, anonymous=True)
    cid = latest(db)["id"]
    officer = login(officer_email(db, cid)).get(f"/complaints/{cid}")
    assert officer.status_code == 200 and b"Aarav Nair" not in officer.data and b"student1@college.example" not in officer.data
    assert b"Anonymous" in officer.data
    admin = login(ADMIN).get(f"/complaints/{cid}")
    assert b"Aarav Nair" in admin.data
    logged = db.execute("SELECT 1 FROM audit_logs WHERE action = 'view_identity' AND entity_id = ?", (cid,)).fetchone()
    assert logged is not None
    queue = login(officer_email(db, cid)).get("/queue").data.decode()
    row = re.search(re.escape(latest(db)["complaint_code"]) + r".*?</tr>", queue, re.S).group(0)
    assert "Anonymous" in row and "Aarav" not in row


# 6
def test_invalid_status_transition_rejected(app, db, login):
    submit(login(STUDENT1), db)
    cid = latest(db)["id"]
    officer = login(officer_email(db, cid))
    r = officer.post(f"/complaints/{cid}/status", data={"new_status": "Closed"}, follow_redirects=True)
    assert b"cannot be moved" in r.data
    assert latest(db)["status"] == "Submitted"
    officer.post(f"/complaints/{cid}/status", data={"new_status": "Under Review"})
    assert latest(db)["status"] == "Under Review"
    r = officer.post(f"/complaints/{cid}/status", data={"new_status": "Rejected"}, follow_redirects=True)
    assert b"reason" in r.data and latest(db)["status"] == "Under Review"  # rejection needs a reason


# 7
def test_disallowed_and_oversized_files_rejected(app, db, login):
    s1 = login(STUDENT1)
    before = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    r = submit(s1, db, files=(io.BytesIO(b"MZ\x90\x00 evil"), "virus.exe"))
    assert r.status_code == 200 and b"only PDF, PNG and JPG" in r.data
    big = io.BytesIO(PDF + b"0" * (5 * 1024 * 1024 + 10))
    r = submit(s1, db, files=(big, "huge.pdf"))
    assert r.status_code == 200 and b"larger than 5 MB" in r.data
    fake = io.BytesIO(b"this is not really a pdf")
    r = submit(s1, db, files=(fake, "fake.pdf"))
    assert b"does not look like a real PDF" in r.data
    assert db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0] == before
    ok = submit(s1, db, files=(io.BytesIO(PDF), "evidence.pdf"))
    assert ok.status_code == 302
    assert db.execute("SELECT COUNT(*) FROM attachments WHERE complaint_id = ?", (latest(db)["id"],)).fetchone()[0] == 1


# 8
def test_overdue_complaint_escalates_through_levels_and_is_logged(app, db, login):
    submit(login(STUDENT1), db)
    cid = latest(db)["id"]
    for expected_level in (2, 3):
        db.execute("UPDATE complaints SET due_date = '2000-01-01 00:00:00' WHERE id = ?", (cid,))
        db.commit()
        with app.app_context():
            assert escalate_overdue(db) >= 1
        assert latest(db)["escalation_level"] == expected_level
    assert db.execute("SELECT COUNT(*) FROM escalations WHERE complaint_id = ?", (cid,)).fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'escalated' AND entity_id = ?", (cid,)).fetchone()[0] == 2
    assert officer_email(db, cid) == COMMITTEE
    assert db.execute("SELECT COUNT(*) FROM notifications WHERE complaint_id = ? AND message LIKE '%escalated%'", (cid,)).fetchone()[0] >= 4
    db.execute("UPDATE complaints SET due_date = '2000-01-01 00:00:00' WHERE id = ?", (cid,))
    db.commit()
    with app.app_context():
        escalate_overdue(db)
    assert latest(db)["escalation_level"] == 3  # never beyond level 3


# 9
def test_closed_complaint_can_be_reopened_with_reason(app, db, login):
    s1 = login(STUDENT1)
    submit(s1, db)
    cid = latest(db)["id"]
    officer = login(officer_email(db, cid))
    for st in ("Under Review", "In Progress", "Resolved"):
        officer.post(f"/complaints/{cid}/status", data={"new_status": st})
    assert latest(db)["status"] == "Resolved"
    s1.post(f"/complaints/{cid}/feedback", data={"rating": "4", "comments": "ok"})
    assert latest(db)["status"] == "Closed"
    r = s1.post(f"/complaints/{cid}/reopen", data={"message": ""}, follow_redirects=True)
    assert b"reason" in r.data and latest(db)["status"] == "Closed"
    s1.post(f"/complaints/{cid}/reopen", data={"message": "The fan stopped working again after two days."})
    assert latest(db)["status"] == "Reopened"
    assert latest(db)["resolved_at"] is None


# 10
def test_missing_csrf_token_returns_400(tmp_path):
    app = make_app(tmp_path, csrf=True)
    r = app.test_client().post("/login", data={"email": STUDENT1, "password": PASSWORD})
    assert r.status_code == 400


# 11
def test_non_admin_cannot_open_admin_pages(app, login):
    for email in (STUDENT1, "officer1.hostel@college.example", "hod.hostel@college.example", COMMITTEE):
        c = login(email)
        for path in ("/admin", "/admin/users", "/admin/catalog", "/admin/audit", "/admin/export.csv"):
            assert c.get(path).status_code == 403, (email, path)
    assert login(ADMIN).get("/admin").status_code == 200
    assert app.test_client().get("/admin").status_code == 302  # anonymous visitors are sent to log in


# 12
def test_feedback_only_allowed_once_after_resolution(app, db, login):
    s1 = login(STUDENT1)
    submit(s1, db)
    cid = latest(db)["id"]
    r = s1.post(f"/complaints/{cid}/feedback", data={"rating": "5"}, follow_redirects=True)
    assert b"after the complaint has been resolved" in r.data
    officer = login(officer_email(db, cid))
    for st in ("Under Review", "In Progress", "Resolved"):
        officer.post(f"/complaints/{cid}/status", data={"new_status": st})
    s1.post(f"/complaints/{cid}/feedback", data={"rating": "5"})
    s1.post(f"/complaints/{cid}/feedback", data={"rating": "1"})
    rows = db.execute("SELECT rating FROM feedback WHERE complaint_id = ?", (cid,)).fetchall()
    assert len(rows) == 1 and rows[0]["rating"] == 5


# 13
def test_sensitive_complaint_hidden_from_ordinary_officers_and_hods(app, db, login):
    submit(login(STUDENT1), db, category="Harassment", title="Confidential matter in the corridor")
    cid = latest(db)["id"]
    assert latest(db)["escalation_level"] == 3 and officer_email(db, cid) == COMMITTEE
    for email in ("officer1.academics@college.example", "officer2.academics@college.example", "hod.academics@college.example"):
        assert login(email).get(f"/complaints/{cid}").status_code == 404
    assert login(COMMITTEE).get(f"/complaints/{cid}").status_code == 200


# 14
def test_login_lockout_after_repeated_failures(app):
    c = app.test_client()
    for _ in range(5):
        c.post("/login", data={"email": STUDENT1, "password": "Bad@12345"})
    r = c.post("/login", data={"email": STUDENT1, "password": PASSWORD})
    assert r.status_code == 429 and b"Too many failed attempts" in r.data


# 15
def test_csv_export_masks_anonymous_and_resists_formula_injection(app, db, login):
    submit(login(STUDENT1), db, anonymous=True, title="=HYPERLINK(\"http://evil\") fake title")
    csv_text = login(ADMIN).get("/admin/export.csv").data.decode()
    assert "Aarav Nair" in csv_text  # his non-anonymous seed complaints are named
    row = [ln for ln in csv_text.splitlines() if "HYPERLINK" in ln][0]
    assert "Anonymous" in row and "Aarav" not in row
    assert "'=HYPERLINK" in row  # leading '=' neutralised


# 16
def test_every_page_loads_for_every_role(app, login):
    pages = ["/", "/privacy", "/accessibility", "/help", "/dashboard", "/queue", "/notifications", "/complaints/new",
             "/admin", "/admin/users", "/admin/catalog", "/admin/audit", "/complaints/1", "/complaints/8"]
    for email in (STUDENT1, "staff1@college.example", "officer1.hostel@college.example", "hod.hostel@college.example",
                  COMMITTEE, ADMIN):
        c = login(email)
        for p in pages:
            assert c.get(p, follow_redirects=True).status_code in (200, 403, 404), (email, p)


# 17
def test_admin_run_escalation_and_dashboard(app, db, login):
    admin = login(ADMIN)
    r = admin.post("/admin/escalate-now", follow_redirects=True)
    assert b"complaint(s) escalated" in r.data  # the two seeded overdue complaints are escalated
    assert db.execute("SELECT COUNT(*) FROM escalations").fetchone()[0] >= 2
    dash = admin.get("/admin")
    assert b"chart-data" in dash.data and b"Avg. days to resolve" in dash.data
