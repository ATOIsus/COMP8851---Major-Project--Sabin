import json
import os
import sqlite3
import time
import traceback
import uuid
from datetime import datetime, timezone

from agent.graph import invoke_company_ai
from email_service.gmail_client import get_unread_emails, mark_as_read

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "company.db")


def db_connection():
    return sqlite3.connect(DB_PATH)


def already_processed(gmail_id):
    # The Gmail message number is used as the local identifier.
    # The database check stops the same message being processed twice.
    conn = db_connection()
    row = conn.execute(
        "SELECT status FROM email_events WHERE gmail_id = ?",
        (gmail_id,),
    ).fetchone()
    conn.close()
    return row is not None and row[0] == "success"


def start_email_event(email_data, execution_id):
    conn = db_connection()
    conn.execute(
        """INSERT OR IGNORE INTO email_events
        (gmail_id, thread_id, sender, recipient, subject, received_at,
         processed_at, execution_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            email_data["gmail_id"],
            email_data.get("thread_id"),
            email_data.get("from"),
            email_data.get("to"),
            email_data.get("subject"),
            email_data.get("date"),
            datetime.now(timezone.utc).isoformat(),
            execution_id,
            "processing",
        ),
    )
    conn.commit()
    conn.close()


def finish_email_event(email_data, execution_id, result=None, error=None):
    result = result or {}
    tool_call = result.get("tool_call") or {}
    status = "error" if error else "success"

    conn = db_connection()
    conn.execute(
        """UPDATE email_events SET processed_at=?, execution_id=?, decision=?,
        selected_tool=?, tool_arguments=?, tool_result=?, final_response=?,
        status=?, error=? WHERE gmail_id=?""",
        (
            datetime.now(timezone.utc).isoformat(),
            execution_id,
            result.get("reasoning"),
            tool_call.get("name"),
            json.dumps(tool_call.get("args", {}), ensure_ascii=False),
            json.dumps(
                result.get("tool_result"),
                ensure_ascii=False,
                default=str,
            ),
            result.get("final_response"),
            status,
            str(error) if error else None,
            email_data["gmail_id"],
        ),
    )
    conn.commit()
    conn.close()


def process_email(email_data):
    if already_processed(email_data["gmail_id"]):
        return None

    execution_id = str(uuid.uuid4())
    start_email_event(email_data, execution_id)

    try:
        # The email is passed into the existing AI agent.
        # The agent decides which action should happen next.
        result = invoke_company_ai(
            {
                **email_data,
                "execution_id": execution_id,
            }
        )

        finish_email_event(
            email_data,
            execution_id,
            result=result,
        )

        # We only mark the email as read after the AI process completes.
        mark_as_read(email_data["imap_id"])

        print(
            f"Processed: {email_data.get('subject', '(no subject)')} "
            f"using {result.get('reasoning', 'unknown')}"
        )

        return result

    except Exception as exc:
        finish_email_event(
            email_data,
            execution_id,
            error=exc,
        )
        print(
            f"Could not process {email_data.get('subject', '(no subject)')}: {exc}"
        )
        traceback.print_exc()
        return {
            "error": str(exc),
            "execution_id": execution_id,
        }


def process_unread_emails():
    emails = get_unread_emails()
    results = []

    if emails:
        print(f"Found {len(emails)} unread email(s).")

    for email_data in emails:
        result = process_email(email_data)
        if result is not None:
            results.append(
                {
                    "email": email_data,
                    "result": result,
                }
            )

    return results


def run_forever(interval_seconds=30):
    print("Company AI email listener is running.")
    print(f"The inbox will be checked every {interval_seconds} seconds.")

    while True:
        try:
            process_unread_emails()
        except Exception as exc:
            print(f"Email listener error: {exc}")
            traceback.print_exc()

        time.sleep(interval_seconds)
