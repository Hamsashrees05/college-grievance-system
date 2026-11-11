# Requirements – College Complaint & Grievance Management System (CGMS)

## 1. Problem statement
Students and staff currently raise complaints on paper, by e-mail or verbally. Complaints get lost, nobody is accountable, there is no deadline, and management cannot see patterns. CGMS is a web application that gives every complaint a number, an owner, a deadline and an audit trail, and escalates it automatically when it is not resolved in time.

## 2. Objectives
1. One online portal to submit and track complaints.
2. Automatic routing to the correct department.
3. Enforced resolution deadlines (SLA) with three-level escalation.
4. Protection for people who need confidentiality (anonymous and sensitive complaints).
5. Reports that let management see workload, delays and satisfaction.

## 3. Scope
**In scope:** registration and login, role-based access, complaint submission with attachments, routing, status workflow, replies and internal notes, escalation, in-app and e-mail notifications, feedback and reopening, admin dashboard and reports, audit log, CSV export.
**Out of scope (future work):** mobile app, SMS/WhatsApp alerts, password-reset by e-mail, single sign-on with the college directory, AI-based categorisation, multi-language interface.

## 4. Assumptions and constraints
- Users have a modern web browser and a college e-mail address.
- Written in Python (Flask) with SQLite so it runs on a laptop with no database server. For real deployment the database would move to PostgreSQL.
- E-mails are simulated (written to `logs/emails.log`) unless SMTP settings are supplied.
- Deadlines use the server's local time.

## 5. Stakeholders
| Stakeholder | Interest |
|---|---|
| Students and staff (complainants) | Be heard, track progress, stay safe from retaliation |
| Department officers | A clear queue and deadlines |
| Heads of department | Visibility of delays, handle escalations |
| Grievance committee | Serious and sensitive cases, identity access when required |
| Administrator | Users, categories, reports, system health |
| College management | Accountability and trends |

## 6. Functional requirements
| ID | Requirement |
|---|---|
| FR-1 | Users register with name, e-mail, role (student or staff), department, optional phone, a strong password and consent to the privacy policy. |
| FR-2 | Users log in and out; accounts lock for 10 minutes after 5 failed attempts. |
| FR-3 | Role-based access for student, staff, officer, HOD, committee and admin. Only the admin creates officer, HOD, committee and admin accounts. |
| FR-4 | A complainant submits a complaint with category, title, description, priority, optional attachments (PDF/PNG/JPG, max 3 per upload, 5 MB each) and an optional anonymous flag. |
| FR-5 | The system generates a unique complaint ID (`CGMS-YYYY-NNNNN`) and a deadline from the category SLA (High and Critical priority halve it). |
| FR-6 | The system routes the complaint to the least-loaded officer of the category's department. Sensitive categories go directly to the grievance committee. |
| FR-7 | Complaints follow the status workflow Submitted → Under Review → In Progress → Resolved → Closed, with Awaiting Info, Rejected and Reopened. Invalid transitions are refused. |
| FR-8 | Officers can reply publicly, add internal notes, request more information, reject with a reason, and escalate manually. |
| FR-9 | Overdue complaints are escalated automatically (daily job and an admin button): officer → HOD → grievance committee. The deadline restarts at each level. |
| FR-10 | The complainant and the new assignee are notified in the application (and by simulated e-mail) of new complaints, replies, status changes and escalations. |
| FR-11 | After resolution the complainant confirms and rates 1–5 (once), which closes the complaint, or reopens it with a reason within 7 days. |
| FR-12 | Anonymous complainants' identity is hidden from officers and HODs; only the committee and admin can see it and every such view is logged. |
| FR-13 | Users search and filter complaints by ID/title, status, priority, category and overdue. |
| FR-14 | The admin dashboard shows totals, counts by status, category, department and month, average resolution time, overdue count and average rating. |
| FR-15 | The admin manages users, departments, categories (including SLA days and sensitivity). |
| FR-16 | Every important action is written to an audit log that the admin can filter. |
| FR-17 | The admin can export all complaints to CSV (anonymous complainants shown as "Anonymous"). |

## 7. Non-functional requirements
| ID | Requirement | How it is met |
|---|---|---|
| NFR-1 Security | Passwords hashed; CSRF, SQL injection and XSS protection; object-level authorisation | PBKDF2 hashing, Flask-WTF CSRF, parameterised SQL, Jinja autoescape, `visibility_clause` |
| NFR-2 Privacy | Minimal data, consent, confidentiality of sensitive cases | Consent checkbox, anonymity rules, privacy page |
| NFR-3 Usability and accessibility | Responsive, labelled forms, keyboard use, text not colour alone | Bootstrap 5, labels, skip link, status text |
| NFR-4 Reliability | Data survives restarts; failures do not leak details | SQLite file, custom error pages |
| NFR-5 Performance | Pages load in under 2 seconds with a few thousand complaints | Indexed queries, pagination |
| NFR-6 Maintainability | Modular code with automated tests | Blueprints, services layer, 17 pytest tests |
| NFR-7 Portability | Runs on Windows, macOS and Linux | Pure Python, no external services |
| NFR-8 Auditability | Who did what and when | `audit_logs` table |

## 8. Traceability (requirement → implementation → test)
| Requirement | Implemented in | Tested by |
|---|---|---|
| FR-1, FR-2 | `app/auth.py` | `test_wrong_password_rejected`, `test_weak_password_rejected_at_registration`, `test_login_lockout_after_repeated_failures` |
| FR-3 | `app/utils.py` (`roles_required`), `app/admin.py` | `test_non_admin_cannot_open_admin_pages` |
| FR-4, FR-5 | `app/complaints.py`, `app/services.py` (`create_complaint`) | `test_submission_creates_code_and_routes_to_correct_department`, `test_disallowed_and_oversized_files_rejected` |
| FR-6 | `app/services.py` (`pick_assignee`) | `test_submission_creates_code_and_routes_to_correct_department`, `test_sensitive_complaint_hidden_from_ordinary_officers_and_hods` |
| FR-7, FR-8 | `app/services.py` (`change_status`), `app/officer.py` | `test_invalid_status_transition_rejected` |
| FR-9 | `app/escalation.py` | `test_overdue_complaint_escalates_through_levels_and_is_logged`, `test_admin_run_escalation_and_dashboard` |
| FR-10 | `app/notifications.py` | `test_overdue_complaint_escalates_through_levels_and_is_logged` |
| FR-11 | `app/services.py` (`add_feedback`) | `test_feedback_only_allowed_once_after_resolution`, `test_closed_complaint_can_be_reopened_with_reason` |
| FR-12 | `app/services.py` (`complainant_label`), `app/complaints.py` | `test_anonymous_identity_hidden_from_officer_but_not_admin` |
| FR-13 | `app/services.py` (`list_complaints`) | `test_every_page_loads_for_every_role` |
| FR-14, FR-15, FR-16 | `app/admin.py` | `test_admin_run_escalation_and_dashboard`, `test_every_page_loads_for_every_role` |
| FR-17 | `app/admin.py` (`export_csv`) | `test_csv_export_masks_anonymous_and_resists_formula_injection` |
