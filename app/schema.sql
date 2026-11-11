CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    head_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student','staff','officer','hod','committee','admin')),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    phone TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    consent_given_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    sla_days INTEGER NOT NULL DEFAULT 7 CHECK (sla_days BETWEEN 1 AND 90),
    is_sensitive INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_code TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low','Medium','High','Critical')),
    is_anonymous INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Submitted' CHECK (status IN
        ('Submitted','Under Review','In Progress','Awaiting Info','Resolved','Closed','Rejected','Reopened')),
    escalation_level INTEGER NOT NULL DEFAULT 1 CHECK (escalation_level BETWEEN 1 AND 3),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    due_date TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    file_size INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    officer_id INTEGER NOT NULL REFERENCES users(id),
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 3),
    assigned_at TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    responder_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT NOT NULL,
    is_internal INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    from_level INTEGER NOT NULL,
    to_level INTEGER NOT NULL,
    reason TEXT NOT NULL,
    escalated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL UNIQUE REFERENCES complaints(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    complaint_id INTEGER REFERENCES complaints(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    details TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints(user_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_due ON complaints(due_date);
CREATE INDEX IF NOT EXISTS idx_assign_complaint ON assignments(complaint_id, is_current);
CREATE INDEX IF NOT EXISTS idx_assign_officer ON assignments(officer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_resp_complaint ON responses(complaint_id);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
