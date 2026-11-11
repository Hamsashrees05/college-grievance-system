# Data Flow Diagrams (Gane & Sarson style notation expressed in Mermaid)

Notation: rectangles = external entities, circles = processes, cylinders = data stores, arrows = data flows.

## Level 0 – Context diagram
```mermaid
flowchart LR
    CM["Complainant<br/>student or staff"]
    OF["Officer / HOD"]
    GC["Grievance committee"]
    AD["Administrator"]
    EM["E-mail service"]
    P0(("0<br/>CGMS"))

    CM -->|"registration details, login credentials, complaint details, reply or additional information, feedback and rating, reopen request"| P0
    P0 -->|"complaint ID and confirmation, status updates and replies, notifications"| CM
    OF -->|"login credentials, status update, reply or internal note, escalation request"| P0
    P0 -->|"assigned complaints, notifications"| OF
    GC -->|"login credentials, status update, reply or internal note"| P0
    P0 -->|"escalated and sensitive complaints, anonymous complainant identity, notifications"| GC
    AD -->|"login credentials, user data, department data, category data, report and export request, escalation run request"| P0
    P0 -->|"dashboard and reports, audit log, CSV export, anonymous complainant identity"| AD
    P0 -->|"e-mail message"| EM
```
*Figure 2 – DFD Level 0.*

## Level 1 – Major processes
```mermaid
flowchart TB
    CM["Complainant"]
    OF["Officer / HOD / Committee"]
    AD["Administrator"]
    EM["E-mail service"]

    P1(("1.0<br/>Manage accounts<br/>and access"))
    P2(("2.0<br/>Register<br/>complaint"))
    P3(("3.0<br/>Route and<br/>assign"))
    P4(("4.0<br/>Manage complaint<br/>resolution"))
    P5(("5.0<br/>Escalate overdue<br/>complaints"))
    P6(("6.0<br/>Notify users"))
    P7(("7.0<br/>Report and<br/>audit"))
    P8(("8.0<br/>Maintain departments<br/>and categories"))

    D1[("D1 Users")]
    D2[("D2 Complaints")]
    D3[("D3 Attachments")]
    D4[("D4 Assignments")]
    D5[("D5 Departments<br/>and categories")]
    D6[("D6 Responses")]
    D7[("D7 Feedback")]
    D8[("D8 Escalations")]
    D9[("D9 Notifications")]
    D10[("D10 Audit log")]

    CM -->|"registration details, login credentials"| P1
    OF -->|"login credentials"| P1
    AD -->|"login credentials, user data"| P1
    P1 <-->|"user record"| D1

    CM -->|"complaint details"| P2
    P2 -->|"complaint ID and confirmation"| CM
    P2 -->|"complaint record"| D2
    P2 -->|"attachment record"| D3
    D5 -->|"category and SLA"| P2
    P2 -->|"new complaint"| P3

    D1 -->|"officer, HOD and committee list"| P3
    D4 -->|"current workload"| P3
    P3 -->|"assignment record"| D4
    P3 -->|"notification request"| P6
    P3 -->|"assigned complaints"| OF

    OF -->|"status update, reply or internal note"| P4
    CM -->|"reply or additional information, feedback and rating, reopen request"| P4
    P4 -->|"status updates and replies"| CM
    D2 <-->|"complaint record"| P4
    P4 -->|"response record"| D6
    P4 -->|"feedback record"| D7
    P4 -->|"notification request"| P6

    OF -->|"escalation request"| P5
    AD -->|"escalation run request"| P5
    D2 -->|"overdue complaints"| P5
    D5 -->|"SLA days"| P5
    D1 -->|"HOD and committee list"| P5
    P5 -->|"new assignment"| D4
    P5 -->|"escalation record"| D8
    P5 -->|"deadline update"| D2
    P5 -->|"notification request"| P6

    P6 -->|"notification record"| D9
    P6 -->|"notifications"| CM
    P6 -->|"notifications"| OF
    P6 -->|"e-mail message"| EM

    AD -->|"report and export request"| P7
    D2 -->|"complaint data"| P7
    D7 -->|"ratings"| P7
    D8 -->|"escalation history"| P7
    P7 -->|"dashboard and reports, CSV export"| AD
    P1 -->|"audit entry"| D10
    P2 -->|"audit entry"| D10
    P4 -->|"audit entry"| D10
    P5 -->|"audit entry"| D10
    D10 -->|"audit entries"| P7
    P7 -->|"audit log"| AD

    AD -->|"department data, category data"| P8
    P8 -->|"department and category records"| D5
```
*Figure 3 – DFD Level 1.*

## Level 2 – Process 4.0 Manage complaint resolution
```mermaid
flowchart TB
    OF["Officer / HOD / Committee"]
    CM["Complainant"]
    P6(("6.0<br/>Notify users"))

    P41(("4.1<br/>Check permission<br/>and workflow rule"))
    P42(("4.2<br/>Update status"))
    P43(("4.3<br/>Record reply<br/>or note"))
    P44(("4.4<br/>Record feedback<br/>and close"))
    P45(("4.5<br/>Reopen<br/>complaint"))

    D2[("D2 Complaints")]
    D6[("D6 Responses")]
    D7[("D7 Feedback")]

    OF -->|"status update"| P41
    OF -->|"reply or internal note"| P43
    CM -->|"reply or additional information"| P43
    CM -->|"feedback and rating"| P41
    CM -->|"reopen request"| P41

    D2 -->|"complaint record"| P41
    P41 -->|"valid status update"| P42
    P41 -->|"valid feedback"| P44
    P41 -->|"valid reopen request"| P45
    P41 -->|"rejection message"| OF

    P42 -->|"updated complaint"| D2
    P44 -->|"feedback record"| D7
    P44 -->|"closed status"| D2
    P45 -->|"reopened status, new deadline"| D2
    P43 -->|"response record"| D6
    P42 -->|"reply for reason"| P43

    P42 -->|"status updates and replies"| CM
    P43 -->|"status updates and replies"| CM
    P44 -->|"status updates and replies"| CM
    P45 -->|"status updates and replies"| CM
    P42 -->|"notification request"| P6
    P43 -->|"notification request"| P6
    P44 -->|"notification request"| P6
    P45 -->|"notification request"| P6
```
*Figure 4 – DFD Level 2 for process 4.0.*

### Balancing check (Level 1 ⇄ Level 2 for process 4.0)
| Flow at the boundary of 4.0 in Level 1 | Appears in Level 2 as |
|---|---|
| IN: status update (Officer) | into 4.1 |
| IN: reply or internal note (Officer) | into 4.3 |
| IN: reply or additional information (Complainant) | into 4.3 |
| IN: feedback and rating (Complainant) | into 4.1 |
| IN: reopen request (Complainant) | into 4.1 |
| IN: complaint record (from D2) | into 4.1 |
| OUT: status updates and replies (to Complainant) | out of 4.2, 4.3, 4.4, 4.5 |
| OUT: notification request (to 6.0) | out of 4.2, 4.3, 4.4, 4.5 |
| OUT: complaint record (to D2) | out of 4.2, 4.4, 4.5 |
| OUT: response record (to D6) | out of 4.3 |
| OUT: feedback record (to D7) | out of 4.4 |
| OUT: audit entry (to D10) | recorded by every sub-process |

Level 0 ⇄ Level 1 balancing: every Level 0 flow appears at Level 1 – registration/login/user data into 1.0; complaint details into 2.0; replies, feedback and reopen into 4.0; status update and internal note into 4.0; escalation request and run request into 5.0; report and export request into 7.0; department and category data into 8.0; notifications and e-mail out of 6.0; reports and audit log out of 7.0. No flow was added or dropped.

---

# Data dictionary

## Data flows
| Data flow | Composition | Source → Destination |
|---|---|---|
| Registration details | name + email + role + department + [phone] + password + consent | Complainant → 1.0 |
| Login credentials | email + password | Any user → 1.0 |
| User data | name + email + role + [department] + temporary password + active flag | Administrator → 1.0 |
| Complaint details | category + title + description + priority + [anonymous flag] + [attachment]* | Complainant → 2.0 |
| Complaint ID and confirmation | complaint code + status + due date | 2.0 → Complainant |
| Status update | new status + [message] | Officer/Committee → 4.0 |
| Reply or internal note | message + internal flag | Officer → 4.0 |
| Reply or additional information | message | Complainant → 4.0 |
| Feedback and rating | rating (1–5) + [comments] | Complainant → 4.0 |
| Reopen request | reason message | Complainant → 4.0 |
| Status updates and replies | status + message + timestamp | 4.0 → Complainant |
| Escalation request | reason | Officer → 5.0 |
| Escalation run request | (button press) | Administrator → 5.0 |
| Notification request | recipient + message + complaint reference | 3.0, 4.0, 5.0 → 6.0 |
| Notifications | message + time + read flag | 6.0 → users |
| E-mail message | recipient address + subject + body | 6.0 → E-mail service |
| Department data / Category data | name + [head] / name + department + SLA days + sensitivity | Administrator → 8.0 |
| Report and export request | filters | Administrator → 7.0 |
| Dashboard and reports, CSV export | counts + averages + chart data / rows | 7.0 → Administrator |
| Audit entry / Audit log | user + action + item + details + IP + time | processes → D10 → 7.0 |
| Anonymous complainant identity | name + e-mail + phone | 7.0/4.0 → Committee, Administrator (logged) |

`[ ]` optional, `*` repeated (maximum 3 per upload, 5 per complaint).

## Data stores
| Store | Database table | Contents |
|---|---|---|
| D1 Users | `users` | Accounts, roles, hashed passwords, consent time |
| D2 Complaints | `complaints` | Complaint record, status, level, deadlines |
| D3 Attachments | `attachments` + files in `instance/uploads` | Evidence files |
| D4 Assignments | `assignments` | Who handles a complaint at each level |
| D5 Departments and categories | `departments`, `categories` | Reference data and SLA days |
| D6 Responses | `responses` | Public replies and internal notes |
| D7 Feedback | `feedback` | One rating per complaint |
| D8 Escalations | `escalations` | History of level changes |
| D9 Notifications | `notifications` | In-app messages |
| D10 Audit log | `audit_logs` | Record of important actions |

## Key data elements
| Element | Type / length | Format or domain | Description |
|---|---|---|---|
| user.id, complaint.id | integer | auto-increment | Internal keys |
| complaint_code | text, 15 | `CGMS-YYYY-NNNNN` | Public complaint ID |
| email | text, ≤120 | valid address, unique | Login name |
| password_hash | text | PBKDF2-SHA256 | Never the plain password |
| role | text | student, staff, officer, hod, committee, admin | Access level |
| title | text, 5–150 | | Short summary |
| description | text, 20–5000 | | Full complaint |
| priority | text | Low, Medium, High, Critical | Urgency |
| is_anonymous | integer | 0 or 1 | Hide identity from officers |
| status | text | Submitted, Under Review, In Progress, Awaiting Info, Resolved, Closed, Rejected, Reopened | Workflow state |
| escalation_level | integer | 1, 2, 3 | Officer, HOD, Committee |
| due_date, created_at, resolved_at | text | `YYYY-MM-DD HH:MM:SS` local time | Timestamps |
| sla_days | integer | 1–90 | Days allowed to resolve |
| is_sensitive | integer | 0 or 1 | Route straight to the committee |
| stored_name | text | UUID + extension | Name of a file on disk |
| rating | integer | 1–5 | Satisfaction score |
| is_internal | integer | 0 or 1 | Note hidden from the complainant |
