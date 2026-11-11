# College Complaint & Grievance Management System (CGMS)

A web application where students and staff submit complaints, officers resolve them within deadlines, overdue complaints escalate automatically (officer → head of department → grievance committee), and the administrator sees reports. It supports anonymous and sensitive complaints, attachments, notifications, feedback, an audit log and CSV export.

**Process model:** Waterfall. **Stack:** Python 3.10+, Flask, SQLite, Jinja2, Bootstrap 5, Chart.js, APScheduler, pytest.

## Features
- Role-based access: student, staff, officer, HOD, grievance committee, admin
- Unique complaint IDs, automatic routing to the least-loaded officer, SLA deadlines
- Status workflow with server-side rules (Submitted → Under Review → In Progress → Resolved → Closed, plus Awaiting Info, Rejected, Reopened)
- Anonymous complaints and sensitive categories (harassment, ragging) kept away from ordinary officers
- Escalation engine (daily job and admin button), notifications (in-app and simulated e-mail)
- Feedback, rating and reopening, search and filters, pagination
- Admin dashboard with charts, user/department/category management, audit log, CSV export
- CSRF protection, hashed passwords, login lockout, upload checks, security headers, accessible UI

## Set-up (about 5 minutes)
### macOS / Linux
```
cd cgms
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py        # creates demo data and prints the demo logins + password (shown once)
python run.py
```
### Windows (PowerShell)
```
cd cgms
py -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python seed.py
python run.py
```
Open **http://127.0.0.1:5000**. Stop the server with **Ctrl + C**.

- `python seed.py` **deletes all existing data** and recreates the demo data. Do not run it after you start using real data.
- To choose the demo password yourself, put `SEED_PASSWORD=YourPass123` in `.env` before running `seed.py`.
- `python run.py` creates missing tables but never deletes data.
- If you see "SECRET_KEY is not set", you forgot `cp .env.example .env`.

## Demo accounts (created by seed.py, all use the same printed password)
| Role | E-mail |
|---|---|
| Administrator | admin@college.example |
| Grievance committee | committee@college.example |
| Head of department | hod.hostel@college.example (also `.academics`, `.library`, `.transport`, `.finance`, `.infrastructure`) |
| Officer | officer1.hostel@college.example, officer2.hostel@college.example (and the other departments) |
| Student | student1@college.example, student2@college.example, student3@college.example |
| Staff | staff1@college.example |

## Run the tests
```
python -m pytest -q
```
Expected: `17 passed`.

## Project structure
```
app/            application code (auth, complaints, officer, admin, notifications, services, escalation)
app/templates/  HTML pages     app/static/  CSS and JavaScript
tests/          automated tests
requirements/   REQUIREMENTS.md
planning/       PROCESS_MODEL.md, PROJECT_PLAN.md, TRELLO_TASKS.md
diagrams/       DFD.md, SEQUENCE.md, ARCHITECTURE.md
report/         REPORT.md, ETHICS.md
presentation/   SLIDES_OUTLINE.md (slides, demo script, viva questions)
run.py seed.py  start the site / create demo data
```

## Documentation index
| Document | Purpose |
|---|---|
| [requirements/REQUIREMENTS.md](requirements/REQUIREMENTS.md) | Problem, scope, FR/NFR, traceability |
| [planning/PROCESS_MODEL.md](planning/PROCESS_MODEL.md) | Waterfall and justification |
| [planning/PROJECT_PLAN.md](planning/PROJECT_PLAN.md) | WBS, tasks, Gantt, risks |
| [planning/TRELLO_TASKS.md](planning/TRELLO_TASKS.md) | Cards to paste into Trello |
| [diagrams/DFD.md](diagrams/DFD.md) | DFD 0/1/2 and data dictionary |
| [diagrams/SEQUENCE.md](diagrams/SEQUENCE.md) | Sequence and state diagrams |
| [diagrams/ARCHITECTURE.md](diagrams/ARCHITECTURE.md) | Architecture, deployment, ER, use cases, scalability |
| [report/ETHICS.md](report/ETHICS.md) | Ethics, licences, OWASP checklist |
| [report/REPORT.md](report/REPORT.md) | Full team report |
| [presentation/SLIDES_OUTLINE.md](presentation/SLIDES_OUTLINE.md) | Slides, demo script, viva questions |

## Exporting diagrams to images for the PDF report
The diagrams are written in Mermaid. GitHub shows them automatically. To get PNG files, open https://mermaid.live, paste the text between the ```mermaid lines, and use **Actions → PNG**. You can also redraw them in https://app.diagrams.net (draw.io).

## Known limitations
SQLite and the in-process scheduler suit one college, not thousands of simultaneous users. E-mail is simulated unless SMTP settings are provided. Login lockout is stored in memory and resets on restart. There is no password reset by e-mail or multi-factor sign-in. Uploads are checked by type and size but not virus scanned. The daily escalation runs only while the server is running (use the admin button otherwise). See `report/ETHICS.md` and `diagrams/ARCHITECTURE.md`.

## Team
| Member | Role | GitHub |
|---|---|---|
| | | |
| | | |
| | | |
| | | |
