# Presentation outline (15 slides) and demo script

Assign each speaker below to a real member so that every member speaks.

| # | Slide | Content | Speaker | Speaker notes |
|---|---|---|---|---|
| 1 | Title | Project name, team, course, date | [Member 1] | Introduce the team and what each person did |
| 2 | Problem | Paper/e-mail complaints get lost, no deadlines, no visibility | [Member 1] | Give one realistic example from your college |
| 3 | Objectives and scope | 5 objectives; what is in and out of scope | [Member 2] | Mention future work is out of scope on purpose |
| 4 | Users and requirements | 5 roles, 17 FR, 8 NFR | [Member 2] | Show two requirements and the tests that prove them |
| 5 | Process model | Waterfall diagram and why | [Member 1] | Explain why not Agile, and the mitigation for late change |
| 6 | Plan | WBS, Gantt, milestones | [Member 3] | Show the Trello board |
| 7 | Risks | Top 5 of 10 risks | [Member 3] | Say which risk actually happened and what you did |
| 8 | DFD Level 0 and 1 | Context and main processes | [Member 4] | Explain the data stores |
| 9 | DFD Level 2 + data dictionary | Process 4.0 breakdown, balancing | [Member 4] | Explain balancing with one flow |
| 10 | Sequence and state diagrams | Submit flow, status workflow | [Member 2] | Walk one error flow |
| 11 | Architecture and scalability | Three tiers, bottlenecks, how to scale | [Member 1] | Be honest that SQLite is a limit |
| 12 | Key features | Routing, anonymity, escalation, analytics (screenshots) | [Member 3] | One screenshot per feature |
| 13 | Testing and security | 17 tests, OWASP table | [Member 4] | Mention one bug found by a test |
| 14 | Ethics | Privacy, anonymity, fairness, licences | [Member 2] | Explain the logged identity view |
| 15 | Conclusion and Q&A | Achievements, limits, future work | [Member 1] | Invite questions |

## 5-minute live demo script
Run `python seed.py` and `python run.py` first, and log in to each account in a separate private window beforehand. Keep screenshots as a backup.

1. **Register** (30 s): open Create account, point out the consent checkbox and password rules. Then log in as `student1@college.example`.
2. **Submit** (60 s): New complaint → Hostel Facilities → fill in → tick *Submit anonymously* → attach a PDF → submit. Show the complaint ID, deadline and timeline.
3. **Officer view** (60 s): in another window log in as the officer for that department (the Hostel officer: `officer1.hostel@college.example`). Open the complaint: the complainant shows as **Anonymous**. Change status Submitted → Under Review → In Progress, add a reply and an internal note.
4. **State rules** (20 s): try choosing Closed directly: it is not offered. Try Rejected without a reason: refused.
5. **Escalation** (60 s): log in as `admin@college.example`, open the dashboard, point out the overdue count, click *Run escalation check now*, then open an overdue complaint and show the escalation history and the new assignee.
6. **Resolve and rate** (40 s): officer sets Resolved; student confirms with a rating (complaint closes) and show Reopen in a different complaint.
7. **Admin** (30 s): charts, audit log (show the *view_identity* entry), CSV export.
8. **Tools** (20 s): show GitHub commits and the Trello board.

## Likely viva questions and short answers
1. **Why Waterfall?** Stable requirements, document-driven assessment, small team. Late change is handled by configurable data.
2. **Why Flask and SQLite?** Simple, easy to explain, no server to install; SQL can move to PostgreSQL.
3. **How are passwords stored?** As salted PBKDF2-SHA256 hashes; never in plain text.
4. **How do you stop one student reading another's complaint?** Every complaint query uses `visibility_clause()`; other users get a 404.
5. **How does anonymity work?** `complainant_label()` returns "Anonymous" for everyone except the owner, committee and admin; committee/admin views are logged.
6. **What is escalation?** Overdue complaints move officer → HOD → committee, restart the deadline, and notify people. It runs daily and by an admin button.
7. **What is the SLA?** Days allowed per category; High and Critical halve it; it pauses in "Awaiting Info".
8. **How do you prevent SQL injection?** All SQL is parameterised; no string formatting of user input.
9. **What is CSRF and how is it handled?** Forged form posts from other sites; every POST needs a secret token (Flask-WTF).
10. **How are uploads secured?** Extension, size and file-signature checks, random file names, served only through an authorised route.
11. **What does the DFD balancing check mean?** The inputs and outputs of a process at Level 1 must equal those of its Level 2 breakdown.
12. **What are the system's limits?** SQLite single writer, in-process scheduler, in-memory lockout, simulated e-mail.
13. **How would you scale it?** PostgreSQL, Gunicorn workers, separate scheduler, object storage, queued e-mail.
14. **How did you test?** 17 automated pytest tests plus manual role walk-throughs and user acceptance.
15. **What ethical issues did you consider?** Privacy, consent, retaliation, sensitive cases, accessibility, false complaints, licences.
