import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "company.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")


def column_exists(conn, table, column):
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
with open(SCHEMA_PATH, encoding="utf-8") as f:
    conn.executescript(f.read())

# Lightweight migration for databases created by the original project.
for column, definition in [
    ("execution_id", "TEXT"),
    ("email_id", "TEXT"),
]:
    if not column_exists(conn, "audit_logs", column):
        conn.execute(f"ALTER TABLE audit_logs ADD COLUMN {column} {definition}")

conn.commit()
conn.close()
print(f"Database initialised: {DB_PATH}")
