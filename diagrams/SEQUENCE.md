# Sequence diagrams and state diagram

## 1. Submit complaint – normal flow
```mermaid
sequenceDiagram
    actor C as Complainant
    participant W as Web app (complaints.new)
    participant S as Services
    participant DB as Database
    participant N as Notifications

    C->>W: POST /complaints/new (form, files, CSRF token)
    W->>W: check session, role and CSRF token
    W->>W: validate fields, consent, file type, size and signature
    W->>S: create_complaint()
    S->>DB: INSERT complaint, then set code CGMS-YYYY-NNNNN
    S->>S: due date = created + category SLA (halved if High or Critical)
    S->>DB: find least-loaded officer (or committee if sensitive)
    S->>DB: INSERT assignment
    S->>DB: INSERT audit log entry
    S->>N: notify assignee and complainant
    N->>DB: INSERT notifications
    N-->>N: write simulated e-mail to logs/emails.log
    W->>DB: save attachment records and files
    W-->>C: redirect to complaint page showing the ID
```
*Figure 5 – Submit complaint (normal flow).*

## 2. Submit complaint – alternate and error flows
```mermaid
sequenceDiagram
    actor C as Complainant
    participant W as Web app
    participant S as Services
    participant DB as Database

    C->>W: POST /complaints/new
    alt not logged in
        W-->>C: redirect to login page
    else CSRF token missing or invalid
        W-->>C: 400 error page
    else invalid input (short title, no consent, bad category)
        W-->>C: form shown again with error messages, nothing saved
    else file rejected (wrong type, over 5 MB, fake signature, too many)
        W-->>C: form shown again with file error, nothing saved
    else valid
        W->>S: create_complaint()
        alt no active officer in the department
            S->>DB: assign to the head of department
        else no head of department either
            S->>DB: assign to an administrator
        else category is sensitive
            S->>DB: assign directly to the grievance committee (level 3)
        else normal
            S->>DB: assign to the least-loaded officer (level 1)
        end
        W-->>C: redirect to complaint page
    end
```
*Figure 6 – Submit complaint (alternate flows).*

## 3. Escalation of an overdue complaint
```mermaid
sequenceDiagram
    participant T as Scheduler (daily) or Admin button
    participant E as Escalation engine
    participant DB as Database
    participant N as Notifications
    actor A as New assignee
    actor C as Complainant

    T->>E: escalate_overdue()
    E->>DB: SELECT complaints past due, SLA running, level below 3
    loop each overdue complaint
        E->>DB: pick assignee for next level (HOD, then committee)
        E->>DB: UPDATE level and new due date
        E->>DB: end old assignment, INSERT new assignment
        E->>DB: INSERT escalation record and audit entry
        E->>N: notify new assignee and complainant
        N-->>A: in-app notification and e-mail
        N-->>C: in-app notification and e-mail
    end
    E-->>T: number of complaints escalated
```
*Figure 7 – Escalation flow.*

## 4. Complaint status state diagram
```mermaid
stateDiagram-v2
    state "Under Review" as UR
    state "In Progress" as IP
    state "Awaiting Info" as AI
    [*] --> Submitted
    Submitted --> UR: officer starts review
    Submitted --> Rejected: officer rejects with reason
    UR --> IP: work begins
    UR --> AI: more information needed
    UR --> Rejected: officer rejects with reason
    IP --> Resolved: officer marks resolved
    IP --> AI: more information needed
    IP --> Rejected: officer rejects with reason
    AI --> IP: complainant replies
    Resolved --> Closed: complainant rates and confirms
    Resolved --> Reopened: complainant reopens within 7 days
    Closed --> Reopened: complainant reopens within 7 days
    Reopened --> UR: officer reviews again
    Rejected --> [*]
    Closed --> [*]
```
*Figure 8 – Status workflow.*

| Transition | Who may trigger it | Rule |
|---|---|---|
| Submitted → Under Review | Assigned officer, HOD, committee, admin | – |
| Any open state → Rejected | Staff roles | A reason is mandatory and is shown to the complainant |
| Under Review / In Progress → Awaiting Info | Staff roles | A message is mandatory; the SLA clock pauses |
| Awaiting Info → In Progress | Complainant (by replying) or staff | Automatic on the complainant's reply |
| In Progress → Resolved | Staff roles | Records `resolved_at` |
| Resolved → Closed | Complainant only | Done by giving a rating, only once |
| Resolved / Closed → Reopened | Complainant only | Reason mandatory; within 7 days of resolution; new deadline |
| Reopened → Under Review | Staff roles | – |
| Any other change | Admin only | Recorded as `status_override` in the audit log |
