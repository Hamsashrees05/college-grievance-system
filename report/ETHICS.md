# Ethical, legal and professional considerations

## 1. Issues and mitigations
| Area | Issue | Mitigation in CGMS | Where in the code |
|---|---|---|---|
| Privacy and consent | The system holds personal data and sensitive complaints | Only name, e-mail, department, role and optional phone are collected. Registration and each complaint require explicit consent. A privacy policy explains use, access and retention. | `register()` consent check, `complaint_new.html`, `privacy.html`, `users.consent_given_at` |
| Confidentiality of reporters | Retaliation against people who complain | Anonymous option hides identity from officers and HODs in lists, detail pages, notifications and CSV. Only the committee and admin can see it and every view is logged. | `complainant_label()`, `view_identity` audit action, `export_csv()` |
| Sensitive cases | Harassment and ragging must not reach people who may know the accused | Sensitive categories go directly to the grievance committee and are invisible to officers and HODs. | `is_sensitive`, `visibility_clause()` |
| Security | Unauthorised access, injection, session theft | Hashed passwords, lockout, CSRF tokens, parameterised SQL, role and ownership checks, secure session cookie, security headers. See the OWASP table below. | `auth.py`, `utils.py`, `__init__.py` |
| Fairness and accessibility | Some users could be excluded | Keyboard-friendly, labelled forms, text status (not colour only), responsive layout, reduced-motion support, plain language. Same queue and deadline rules for everyone. | templates, `app.css`, `accessibility.html` |
| Accuracy and safety of data | Wrong status or lost history harms trust | Server-side workflow rules, mandatory reasons for rejection and reopening, immutable audit log, 17 automated tests. | `change_status()`, `audit()`, `tests/` |
| Transparency and accountability | Decisions must be explainable | Complainants see a timeline of status changes and escalations. Every action has an audit entry. Officers cannot hide their own actions. | `detail()` timeline, `audit_logs` |
| Fairness of deadlines | Pressure on officers could cause hasty closure | The clock pauses in "Awaiting Info". Resolution needs the complainant's confirmation, and reopening is possible for 7 days. | `SLA_RUNNING`, `add_feedback()` |
| Misuse and false complaints | Malicious or abusive complaints | Terms in the privacy policy, confirmation checkbox, audit trail allows investigation, officers can reject with a reason. | `privacy.html`, `STAFF_NEXT` |
| Anonymity limits | Content may reveal the reporter | The privacy page states that anonymity cannot be guaranteed when the text identifies the person. | `privacy.html` |
| Data retention | Complaints should not be kept forever | Policy states retention follows college rules. Admin can export and remove data on request. Future work: scheduled anonymisation. | `privacy.html` |
| Intellectual property | Use of third-party code | Only open-source libraries with permissive licences, listed below. No copied code or images. | `requirements.txt` |
| Environmental / social | Digital-only access may exclude some people | The system supplements, not replaces, the physical grievance cell; help page explains how it works. | `help.html` |

## 2. Third-party components and licences
Verify these on each project's official page before submission.
| Component | Use | Licence |
|---|---|---|
| Python | Language | PSF License |
| Flask, Werkzeug, Jinja2 | Web framework | BSD-3-Clause |
| Flask-WTF / WTForms | CSRF protection | BSD-3-Clause |
| APScheduler | Daily escalation job | MIT |
| python-dotenv | Reads `.env` | BSD-3-Clause |
| pytest | Testing | MIT |
| SQLite | Database | Public domain |
| Bootstrap 5 | Styling | MIT |
| Chart.js | Dashboard charts | MIT |

## 3. OWASP Top 10 (2021) checklist
| Risk | Status | How it is handled |
|---|---|---|
| A01 Broken access control | Mitigated | Role decorators, `visibility_clause()` on every complaint query, 404 for unauthorised objects, tests for cross-user access |
| A02 Cryptographic failures | Mitigated | PBKDF2-SHA256 hashes, secret key from environment; HTTPS and `COOKIE_SECURE=1` required in production |
| A03 Injection | Mitigated | Parameterised SQL only, Jinja autoescape, CSV formula-injection guard, strict upload validation |
| A04 Insecure design | Mitigated | Server-side workflow, least-privilege roles, anonymity designed in, threat thinking documented here |
| A05 Security misconfiguration | Mitigated | Debug off by default, app refuses to start without a secret key, security headers and CSP, custom error pages |
| A06 Vulnerable components | Partly | Few, maintained dependencies. Run `pip list --outdated` before release. No automatic scanning yet |
| A07 Identification and authentication failures | Mitigated | Password policy, lockout after 5 failures, session reset on login, deactivation. No multi-factor or e-mail reset yet |
| A08 Software and data integrity failures | Partly | Version-pinned CDN files; no subresource-integrity hashes yet; no deserialisation of user data |
| A09 Logging and monitoring failures | Mitigated | `audit_logs` for logins, status changes, identity views, exports and admin actions. No alerting yet |
| A10 Server-side request forgery | Not applicable | The server never fetches user-supplied URLs |

## 4. Professional responsibility
The team follows the ACM/IEEE Software Engineering Code of Ethics principles: act in the public interest (protect vulnerable reporters), be honest about limits (this report lists known weaknesses), keep personal data confidential, test before release, credit sources and licences, and keep the audit trail honest. Demo data uses fictional people and `example` e-mail domains. No real passwords are stored in the repository; `seed.py` takes the demo password from the environment or prints a random one.
