CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_email TEXT NOT NULL,
    subject TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    company TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    execution_id TEXT,
    email_id TEXT,
    action TEXT NOT NULL,
    tool_called TEXT,
    input_summary TEXT,
    result TEXT
);

CREATE TABLE IF NOT EXISTS email_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_id TEXT UNIQUE NOT NULL,
    thread_id TEXT,
    sender TEXT,
    recipient TEXT,
    subject TEXT,
    received_at TEXT,
    processed_at TEXT,
    execution_id TEXT,
    decision TEXT,
    selected_tool TEXT,
    tool_arguments TEXT,
    tool_result TEXT,
    final_response TEXT,
    status TEXT NOT NULL,
    error TEXT
);
