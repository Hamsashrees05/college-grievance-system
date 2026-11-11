# College Complaint & Grievance Management System (CGMS)
**Course:** Software Engineering  **Date:** [date]
**Team:** [Member 1 – role], [Member 2 – role], [Member 3 – role], [Member 4 – role]
**GitHub repository:** [GitHub URL]  **Trello board:** [Trello URL]

> To produce the PDF: export each Mermaid diagram as PNG (see README), paste the images where the figure numbers appear, then export this file to PDF from VS Code (Markdown PDF extension), Typora, or by pasting into Word.

## 1. Introduction
Colleges receive complaints about teaching, hostels, libraries, transport, fees and safety, but many are raised on paper or verbally and are lost, delayed or ignored. CGMS is a web application where students and staff submit complaints, officers resolve them within deadlines, overdue complaints escalate automatically, and management sees reports. It supports anonymous and sensitive complaints. The project follows the Waterfall model and is built with Python (Flask) and SQLite.

## 2. Requirements
Full text: `requirements/REQUIREMENTS.md`.
- **Users:** complainant (student or staff), department officer, head of department, grievance committee, administrator.
- **17 functional requirements** cover registration and login, submission with attachments, routing, workflow, replies and notes, escalation, notifications, feedback and reopening, anonymity, search, dashboard, administration, audit log and CSV export.
- **8 non-functional requirements** cover security, privacy, accessibility, reliability, performance, maintainability, portability and auditability.
- A traceability table maps each requirement to code and to an automated test.

## 3. Selected process model
Waterfall (Figure 1, `planning/PROCESS_MODEL.md`). It was chosen because the requirements were stable, each phase produces a reviewed document, the team is small, and changes were expected to be rare. Agile, Spiral, Prototyping and Incremental were compared and rejected with reasons. The main weakness, late change, is reduced by early review with sample users, feedback loops for defects, and keeping business rules (SLA days, categories) as data.

## 4. Project plan
Full text: `planning/PROJECT_PLAN.md`. It contains the work breakdown structure, a 16-task table with owners and dependencies, six milestones, a 12-week Gantt chart, a 65 person-day effort estimate and a risk register with ten risks (for example team member loss, time overrun, security flaws, data loss) and mitigations.

## 5. Software design
- **DFD Level 0, 1 and 2** (Figures 2–4) with a balancing table and a full data dictionary: `diagrams/DFD.md`.
- **Sequence diagrams** for submission (normal and alternate flows) and escalation, and the status **state diagram** (Figures 5–8): `diagrams/SEQUENCE.md`.
- **Architecture, deployment, ER and use case diagrams** (Figures 9–12), technology justification and scalability analysis: `diagrams/ARCHITECTURE.md`.

**Key design decisions**
1. A single `visibility_clause()` decides which complaints each role may see, so list pages, detail pages and downloads cannot disagree.
2. One `change_status()` function enforces the workflow, who may use each transition, mandatory reasons, and notifications.
3. Anonymity is enforced in one function, `complainant_label()`, so identity cannot leak by forgetting a check in a template.
4. Escalation is a plain function used by both the daily job and the admin button, so it can be tested directly.
5. Deadlines pause while information is requested from the complainant, to avoid penalising officers for waiting on the user.

## 6. Tools and collaboration
| Tool | Use |
|---|---|
| Trello | Board with columns Backlog, To Do, In Progress, Review, Done; cards in `planning/TRELLO_TASKS.md`. Screenshot: [add] |
| GitHub | Repository with feature branches, small commits and pull-request review. Screenshot of commit history and contribution graph: [add] |
| VS Code / Antigravity / Cursor | Editing; AI assistants were used to speed up coding and every generated file was reviewed and tested by the team |
| pytest | 17 automated tests (all passing) |
| Mermaid / draw.io | Diagrams |

**Branching:** `main` is always demo-ready; each task uses a branch named `feature/<task>`; merges happen by pull request with at least one reviewer.

**Contribution table** (fill in with real work)
| Member | Main contributions | Commits / PRs |
|---|---|---|
| [Member 1] | | |
| [Member 2] | | |
| [Member 3] | | |
| [Member 4] | | |

## 7. Ethical and professional considerations
Full text and OWASP checklist: `report/ETHICS.md`. Highlights: consent and a privacy policy; anonymous complaints with logged committee access; sensitive categories isolated from ordinary officers; hashed passwords, CSRF protection, parameterised SQL and role checks; accessibility features; honest limitations; permissive open-source licences only; fictional demo data.

## 8. Testing summary
| Type | Evidence |
|---|---|
| Automated (17 tests) | Login failure and lockout, password policy, cross-user access, routing, anonymity, workflow rules, file validation, escalation to level 3 with logging, reopening, CSRF, admin-only pages, feedback once, sensitive-case isolation, CSV masking and formula-injection guard, every page for every role |
| Manual | Walk-through of the demo script with each role (see `presentation/SLIDES_OUTLINE.md`) |
| UAT | [Add notes from 3–5 real users: what they liked, what confused them, what you changed] |

## 9. Conclusion and references
**Achievements:** a complete, tested system with routing, workflow, escalation, anonymity, notifications, analytics and an audit trail.
**Limitations:** SQLite and in-process scheduler suit one college, not thousands of simultaneous users; e-mail is simulated unless SMTP is configured; the login lockout is in memory; no password reset by e-mail; no multi-factor authentication; uploads are type-checked but not virus scanned; the scheduler runs only while the server is running; times use server local time.
**Future work:** mobile app, SMS or WhatsApp alerts, college single sign-on, PostgreSQL deployment, AI-assisted categorisation, scheduled data anonymisation, multi-language support.

**References (add the ones you actually used)**
1. Pressman, R. and Maxim, B., *Software Engineering: A Practitioner's Approach*, McGraw-Hill.
2. Sommerville, I., *Software Engineering*, Pearson.
3. OWASP Top 10 (2021), https://owasp.org/Top10/
4. Flask documentation, https://flask.palletsprojects.com/
5. Bootstrap documentation, https://getbootstrap.com/docs/5.3/
6. Chart.js documentation, https://www.chartjs.org/docs/
7. ACM/IEEE-CS Software Engineering Code of Ethics, https://www.acm.org/code-of-ethics/software-engineering-code
