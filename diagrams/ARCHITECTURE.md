# Architecture, deployment, ER and use cases

## 1. Architecture diagram (three-tier)
```mermaid
flowchart TB
    subgraph Client["Presentation tier – browser"]
        U["Student / staff / officer / HOD / committee / admin<br/>HTML + Bootstrap 5 + Chart.js"]
    end
    subgraph App["Application tier – Flask (Python)"]
        direction TB
        R["Route blueprints<br/>auth, complaints, officer, admin, notifications, pages"]
        S["Business logic<br/>services.py workflow, routing, visibility<br/>escalation.py"]
        M["Cross-cutting<br/>CSRF, role checks, security headers, audit log"]
        SCH["APScheduler<br/>daily escalation job"]
        R --> S
        M -.-> R
        SCH --> S
    end
    subgraph Data["Data tier"]
        DB[("SQLite database<br/>11 tables")]
        FS["File storage<br/>instance/uploads"]
        LOG["logs/emails.log"]
    end
    EXT["SMTP server (optional)"]
    U <-->|"HTTP(S)"| R
    S --> DB
    S --> FS
    S --> LOG
    S -.-> EXT
```
*Figure 9 – System architecture.*

### Technology choices
| Choice | Reason |
|---|---|
| Python + Flask | Small, readable, well documented; easy for every team member to explain |
| SQLite | Zero setup, one file, enough for a single college's complaint volume; same SQL moves to PostgreSQL |
| Jinja2 templates + Bootstrap 5 | Server-rendered pages are simple, accessible and work without a JavaScript framework |
| Flask-WTF (CSRF) | Standard protection against cross-site request forgery |
| Werkzeug hashing (PBKDF2-SHA256) | Safe password storage using a maintained library |
| APScheduler | Daily job without installing Celery or Redis |
| Chart.js | Lightweight charts for the dashboard |
| pytest | Simple automated tests with a temporary database |

## 2. Deployment diagram
```mermaid
flowchart LR
    subgraph Local["Option A – demo on a laptop"]
        L1["Browser"] --> L2["python run.py<br/>Flask dev server 127.0.0.1:5000"]
        L2 --> L3[("instance/cgms.db")]
    end
    subgraph Prod["Option B – college server or cloud VM"]
        P1["Users' browsers"] -->|"HTTPS 443"| P2["Nginx reverse proxy<br/>TLS certificate"]
        P2 --> P3["Gunicorn (2-4 workers)<br/>Flask app"]
        P3 --> P4[("PostgreSQL<br/>after migration")]
        P3 --> P5["Uploads volume or object storage"]
        P6["Separate scheduler process<br/>daily escalation"] --> P4
        P7["Nightly backup job"] --> P4
        P7 --> P5
    end
```
*Figure 10 – Deployment options.*

Production notes: set `SECRET_KEY` and `COOKIE_SECURE=1`, leave `FLASK_DEBUG` unset, serve only over HTTPS, run the scheduler as one process only, and back up the database and uploads nightly.

## 3. Scalability
| Bottleneck | Why it matters | How to scale |
|---|---|---|
| SQLite allows one writer at a time | Many users submitting together would queue | Move to PostgreSQL (change the connection layer; SQL is standard) |
| Single Flask process | Limited concurrency | Gunicorn with several workers behind Nginx |
| Scheduler inside the app process | With several workers the job could run more than once | Run it as its own process, or use Celery beat / cron calling an endpoint |
| Uploads on local disk | Not shared between servers | Object storage (for example S3 compatible) |
| In-memory login lockout | Lost on restart and not shared between workers | Store attempts in Redis or the database |
| E-mail sent inside the request | Slow SMTP delays the user | Queue e-mails with Celery or RQ |

For about 5,000 users, indexes on status, user, due date and assignments keep queries fast, and pagination limits the rows returned.

## 4. Entity–relationship diagram
```mermaid
erDiagram
    DEPARTMENTS ||--o{ CATEGORIES : has
    DEPARTMENTS ||--o{ USERS : employs
    USERS ||--o{ COMPLAINTS : files
    CATEGORIES ||--o{ COMPLAINTS : classifies
    COMPLAINTS ||--o{ ATTACHMENTS : has
    COMPLAINTS ||--o{ ASSIGNMENTS : "is assigned through"
    USERS ||--o{ ASSIGNMENTS : handles
    COMPLAINTS ||--o{ RESPONSES : has
    USERS ||--o{ RESPONSES : writes
    COMPLAINTS ||--o{ ESCALATIONS : "moves up through"
    COMPLAINTS ||--o| FEEDBACK : receives
    USERS ||--o{ NOTIFICATIONS : receives
    COMPLAINTS ||--o{ NOTIFICATIONS : triggers
    USERS ||--o{ AUDIT_LOGS : performs

    USERS {
        int id PK
        text name
        text email UK
        text password_hash
        text role
        int department_id FK
        text phone
        int is_active
        text consent_given_at
    }
    DEPARTMENTS {
        int id PK
        text name UK
        int head_user_id FK
    }
    CATEGORIES {
        int id PK
        text name UK
        int department_id FK
        int sla_days
        int is_sensitive
    }
    COMPLAINTS {
        int id PK
        text complaint_code UK
        int user_id FK
        int category_id FK
        text title
        text description
        text priority
        int is_anonymous
        text status
        int escalation_level
        text due_date
        text resolved_at
    }
    ASSIGNMENTS {
        int id PK
        int complaint_id FK
        int officer_id FK
        int level
        int is_current
    }
    RESPONSES {
        int id PK
        int complaint_id FK
        int responder_id FK
        text message
        int is_internal
    }
    FEEDBACK {
        int id PK
        int complaint_id FK
        int rating
    }
```
*Figure 11 – ER diagram (main attributes).*

## 5. Use case diagram
```mermaid
flowchart LR
    CMP(["Complainant<br/>student / staff"])
    OFC(["Officer"])
    HOD(["Head of department"])
    GCM(["Grievance committee"])
    ADM(["Administrator"])

    subgraph CGMS["CGMS"]
        U1(["Register and log in"])
        U2(["Submit complaint<br/>(optionally anonymous)"])
        U3(["Track status and reply"])
        U4(["Confirm and rate, or reopen"])
        U5(["Work the assigned queue"])
        U6(["Change status, reply, add internal note"])
        U7(["Escalate a complaint"])
        U8(["Handle escalated and sensitive cases"])
        U9(["View anonymous identity (logged)"])
        U10(["Manage users, departments, categories"])
        U11(["View dashboard, audit log, export CSV"])
        U12(["Run escalation check"])
    end

    CMP --- U1
    CMP --- U2
    CMP --- U3
    CMP --- U4
    OFC --- U5
    OFC --- U6
    OFC --- U7
    HOD --- U5
    HOD --- U6
    HOD --- U7
    GCM --- U8
    GCM --- U9
    GCM --- U6
    ADM --- U9
    ADM --- U10
    ADM --- U11
    ADM --- U12
```
*Figure 12 – Use case diagram.*
