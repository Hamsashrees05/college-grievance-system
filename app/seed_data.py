"""Demo data used by seed.py and by the automated tests."""
from datetime import timedelta

from . import services as svc
from .utils import now, now_str

DEPARTMENTS = [("Academics", "academics"), ("Hostel", "hostel"), ("Library", "library"),
               ("Transport", "transport"), ("Finance & Fees", "finance"), ("Infrastructure", "infrastructure")]

# name, department, SLA days, sensitive
CATEGORIES = [
    ("Exam & Results", "Academics", 7, 0), ("Timetable & Teaching", "Academics", 7, 0),
    ("Harassment", "Academics", 3, 1), ("Ragging", "Hostel", 3, 1),
    ("Hostel Facilities", "Hostel", 5, 0), ("Mess & Food", "Hostel", 3, 0),
    ("Library Services", "Library", 5, 0), ("Transport Delay", "Transport", 4, 0),
    ("Fee Payment & Refund", "Finance & Fees", 10, 0), ("Scholarship", "Finance & Fees", 14, 0),
    ("Classroom Infrastructure", "Infrastructure", 7, 0), ("Water & Electricity", "Infrastructure", 3, 0),
]

# (owner, category, title, description, priority, anonymous, days_ago, steps, message for the last step, rating)
COMPLAINTS = [
    ("student1", "Mess & Food", "Stale food served in the mess", "The dinner served on Monday and Tuesday smelled stale and several students felt unwell. Please inspect the kitchen and storage.", "Medium", False, 30, ["Under Review", "In Progress", "Resolved"], None, 4),
    ("student2", "Hostel Facilities", "Water heater not working in Block B", "The water heater on the second floor of Block B has not worked for three days and there is no hot water in the mornings.", "High", False, 1, ["Under Review", "In Progress"], None, None),
    ("student3", "Exam & Results", "Internal marks missing for Data Structures", "My internal assessment marks for Data Structures are not shown on the portal although I attended all tests.", "Medium", False, 3, ["Under Review"], None, None),
    ("student1", "Library Services", "Reference books not available before exams", "The prescribed reference books for the semester are always issued out and there are no copies available in the reading room.", "Low", False, 45, ["Under Review", "In Progress", "Resolved"], None, 5),
    ("student2", "Transport Delay", "Bus route 7 arrives 40 minutes late daily", "Route 7 has been arriving about 40 minutes late for two weeks and we miss the first lecture.", "Medium", False, 3, [], None, None),
    ("staff1", "Classroom Infrastructure", "Projector in Room 204 is broken", "The ceiling projector in Room 204 shows only a green screen. Lectures are being disturbed.", "Medium", False, 6, ["Under Review", "In Progress"], None, None),
    ("student3", "Fee Payment & Refund", "Fee refund not received after withdrawal", "I withdrew from the course in August and the refund promised in the notice has not reached my bank account.", "High", False, 20, ["Under Review", "Awaiting Info"], "Please upload your bank passbook page and the withdrawal approval letter.", None),
    ("student1", "Harassment", "Inappropriate behaviour by a senior student", "A senior student has repeatedly made inappropriate comments to me near the department corridor. I would like this handled confidentially.", "High", True, 0.1, ["Under Review"], None, None),
    ("student2", "Mess & Food", "Mess charges billed twice this month", "The mess account shows two charges for the same week in October. Please check and correct the bill.", "Medium", False, 20, [], None, None),
    ("student3", "Library Services", "Library closes before the posted time", "The library has been closing at 7 pm instead of 9 pm on weekdays, which affects students preparing for exams.", "Low", True, 22, ["Under Review"], None, None),
    ("staff1", "Water & Electricity", "Frequent power cuts in the lab block", "There are daily power cuts of up to an hour in the lab block and the backup supply does not start.", "High", False, 0.5, [], None, None),
    ("student1", "Scholarship", "Scholarship amount not credited", "My merit scholarship for this year has not been credited and the finance office says the file is pending.", "Medium", False, 9, ["Under Review", "In Progress"], None, None),
    ("student2", "Timetable & Teaching", "Classes clashing for elective subjects", "Two of my elective subjects are scheduled in the same slot on Thursdays so I cannot attend both.", "Medium", False, 40, ["Under Review", "In Progress", "Resolved"], None, None),
    ("student3", "Exam & Results", "Revaluation result delayed", "The revaluation result for last semester was due weeks ago and has still not been published.", "Medium", False, 28, ["Rejected"], "Revaluation results are issued by the university, not by the college. Please contact the university examination cell.", None),
    ("staff1", "Hostel Facilities", "Broken window latch in room 112", "The window latch in room 112 is broken and the window cannot be locked at night.", "Low", False, 55, ["Under Review", "In Progress", "Resolved"], None, 3),
]


def seed(db, password_hash):
    """Fill an empty database with departments, users, categories and sample complaints. Returns the demo logins."""
    dept_id = {}
    for name, _slug in DEPARTMENTS:
        dept_id[name] = db.execute("INSERT INTO departments (name) VALUES (?)", (name,)).lastrowid

    def add_user(name, email, role, dept=None, phone=None):
        return db.execute(
            "INSERT INTO users (name, email, password_hash, role, department_id, phone, is_active, consent_given_at, created_at) "
            "VALUES (?,?,?,?,?,?,1,?,?)", (name, email, password_hash, role, dept, phone, now_str(), now_str())).lastrowid

    logins = []
    def add(name, email, role, dept=None, phone=None):
        uid = add_user(name, email, role, dept, phone)
        logins.append((role, email))
        return uid

    add("Administrator", "admin@college.example", "admin")
    add("Dr. Meera Rao (Grievance Committee)", "committee@college.example", "committee")
    for dname, slug in DEPARTMENTS:
        d = dept_id[dname]
        head = add(f"Prof. {dname.split()[0]} Head", f"hod.{slug}@college.example", "hod", d)
        db.execute("UPDATE departments SET head_user_id = ? WHERE id = ?", (head, d))
        add(f"{dname.split()[0]} Officer One", f"officer1.{slug}@college.example", "officer", d)
        add(f"{dname.split()[0]} Officer Two", f"officer2.{slug}@college.example", "officer", d)
    people = {
        "student1": add("Aarav Nair", "student1@college.example", "student", dept_id["Academics"], "9876500001"),
        "student2": add("Diya Menon", "student2@college.example", "student", dept_id["Academics"], "9876500002"),
        "student3": add("Kabir Shah", "student3@college.example", "student", dept_id["Hostel"], "9876500003"),
        "staff1": add("Ms. Lakshmi Iyer", "staff1@college.example", "staff", dept_id["Infrastructure"], "9876500004"),
    }
    for name, dname, sla, sens in CATEGORIES:
        db.execute("INSERT INTO categories (name, department_id, sla_days, is_sensitive) VALUES (?,?,?,?)",
                   (name, dept_id[dname], sla, sens))
    db.commit()

    cats = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM categories")}
    for i, (owner, cat, title, desc, prio, anon, days_ago, steps, msg, rating) in enumerate(COMPLAINTS):
        user = db.execute("SELECT * FROM users WHERE id = ?", (people[owner],)).fetchone()
        created = now() - timedelta(days=days_ago)
        cid = svc.create_complaint(db, user, cats[cat], title, desc, prio, anon, created_at=created)
        for step in steps:
            actor = svc.current_assignee(db, cid)
            is_last = step == steps[-1]
            svc.change_status(db, cid, step, actor, msg if (is_last and msg) else None)
        if "Resolved" in steps:
            days = 1 + (i % 4)
            db.execute("UPDATE complaints SET resolved_at = ? WHERE id = ?",
                       ((created + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"), cid))
            if rating:
                c = svc.get_complaint(db, user, cid)
                svc.add_feedback(db, c, user, rating, "Thank you for the quick action." if rating >= 4 else None)
        if steps and steps[-1] == "In Progress":
            svc.add_response(db, cid, svc.current_assignee(db, cid), "We have started working on this and will update you soon.")
    db.commit()
    return logins
