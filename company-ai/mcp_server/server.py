from fastapi import FastAPI, Request
from pydantic import BaseModel
import datetime
import json
import os
import sqlite3

from email_service.gmail_client import send_email as gmail_send_email

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "company.db")
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(DATA_DIR, "internal_docs")
CONFIG_DIR = os.path.join(DATA_DIR, "config")

app = FastAPI(title="Company AI MCP Tool Server")


def log_action(action, tool, input_summary, result, request: Request | None = None):
    execution_id = request.headers.get("X-Execution-ID") if request else None
    email_id = request.headers.get("X-Email-ID") if request else None
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audit_logs
        (execution_id, email_id, action, tool_called, input_summary, result)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (
            execution_id,
            email_id,
            action,
            tool,
            str(input_summary)[:2000],
            str(result)[:10000],
        ),
    )
    conn.commit()
    conn.close()


class SlotRequest(BaseModel):
    date: str


@app.post("/tools/get_available_slots")
def get_available_slots(req: SlotRequest, request: Request):
    slots = ["09:00", "11:00", "14:00"]
    log_action("get_available_slots", "calendar", req.date, slots, request)
    return {"slots": slots}


class EventRequest(BaseModel):
    requester_email: str
    subject: str
    start_time: str
    end_time: str


@app.post("/tools/create_event")
def create_event(req: EventRequest, request: Request):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO appointments (requester_email, subject, start_time, end_time) VALUES (?, ?, ?, ?)",
        (req.requester_email, req.subject, req.start_time, req.end_time),
    )
    conn.commit()
    conn.close()
    log_action("create_event", "calendar", req.subject, "booked", request)
    return {"status": "booked", "start_time": req.start_time, "end_time": req.end_time}


@app.get("/tools/fetch_unread_emails")
def fetch_unread_emails(request: Request):
    path = os.path.join(DATA_DIR, "sample_emails.json")
    with open(path, encoding="utf-8") as f:
        emails = json.load(f)
    log_action(
        "fetch_unread_emails",
        "email",
        "sample mailbox",
        f"{len(emails)} emails",
        request,
    )
    return {"emails": emails}


class SendEmailRequest(BaseModel):
    to: str
    body: str
    subject: str = "Re: Your enquiry"
    thread_id: str | None = None
    in_reply_to: str | None = None
    references: str | None = None


@app.post("/tools/send_email")
def send_email(req: SendEmailRequest, request: Request):
    result = gmail_send_email(
        to=req.to,
        subject=req.subject,
        body=req.body,
        thread_id=req.thread_id,
        in_reply_to=req.in_reply_to,
        references=req.references,
    )
    log_action("send_email", "email", req.to, result, request)
    return result


class SearchRequest(BaseModel):
    query: str


@app.post("/tools/search_documents")
def search_documents(req: SearchRequest, request: Request):
    results = []
    if os.path.isdir(DOCS_DIR):
        for fname in os.listdir(DOCS_DIR):
            path = os.path.join(DOCS_DIR, fname)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if req.query.lower() in content.lower():
                results.append({"file": fname, "excerpt": content[:300]})
    log_action(
        "search_documents", "file_search", req.query, f"{len(results)} matches", request
    )
    return {"results": results}


class ReadFileRequest(BaseModel):
    filename: str
    location: str = "internal_docs"


@app.post("/tools/read_file")
def read_file(req: ReadFileRequest, request: Request):
    # Intentionally retained as a vulnerable baseline for the security experiments.
    base_dir = CONFIG_DIR if req.location == "config" else DOCS_DIR
    path = os.path.join(base_dir, req.filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    log_action(
        "read_file",
        "filesystem",
        f"{req.location}/{req.filename}",
        f"{len(content)} chars",
        request,
    )
    return {"content": content}


class TransactionLogRequest(BaseModel):
    entry: str


@app.post("/tools/write_transaction_log")
def write_transaction_log(req: TransactionLogRequest, request: Request):
    os.makedirs(DATA_DIR, exist_ok=True)
    log_path = os.path.join(DATA_DIR, "transaction_log.txt")
    timestamp = datetime.datetime.now().isoformat()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {req.entry}\n")
    log_action(
        "write_transaction_log", "filesystem", req.entry[:50], "appended", request
    )
    return {"status": "logged"}


class WriteAttachmentRequest(BaseModel):
    filename: str
    content: str


@app.post("/tools/save_temp_attachment")
def save_temp_attachment(req: WriteAttachmentRequest, request: Request):
    folder = os.path.join(DATA_DIR, "temp_attachments")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, req.filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(req.content)
    log_action("save_temp_attachment", "filesystem", req.filename, "saved", request)
    return {"status": "saved", "path": path}


@app.post("/tools/cleanup_temp_attachments")
def cleanup_temp_attachments(request: Request):
    folder = os.path.join(DATA_DIR, "temp_attachments")
    deleted = []
    if os.path.exists(folder):
        for fname in os.listdir(folder):
            path = os.path.join(folder, fname)
            if os.path.isfile(path):
                os.remove(path)
                deleted.append(fname)
    log_action(
        "cleanup_temp_attachments", "filesystem", "periodic cleanup", deleted, request
    )
    return {"deleted": deleted}


class WebhookRequest(BaseModel):
    url: str
    data: dict


@app.post("/tools/call_webhook")
def call_webhook(req: WebhookRequest, request: Request):
    # Intentionally permissive in the baseline so the security experiment can measure
    # the impact of an agent being induced to make an outbound HTTP request.
    import requests as ext_requests

    try:
        resp = ext_requests.post(req.url, json=req.data, timeout=5)
        status = resp.status_code
    except Exception as e:
        status = f"error: {e}"
    log_action("call_webhook", "http", req.url, status, request)
    return {"status": status}


class SlotRequest(BaseModel):
    date: str


@app.post("/tools/get_available_slots")
def get_available_slots(req: SlotRequest, request: Request):
    available_slots = ["09:00", "11:00", "14:00"]

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.execute(
        """
        SELECT start_time
        FROM appointments
        WHERE start_time LIKE ?
        """,
        (f"{req.date}%",),
    )

    booked_start_times = set()

    for row in cursor.fetchall():
        start_time = row[0]

        # Supports values such as:
        # 2026-09-14 09:00
        # 2026-09-14T09:00:00
        if len(start_time) >= 16:
            booked_start_times.add(start_time[11:16])

    conn.close()

    slots = [slot for slot in available_slots if slot not in booked_start_times]

    log_action(
        "get_available_slots",
        "calendar",
        req.date,
        {
            "available": slots,
            "booked": list(booked_start_times),
        },
        request,
    )

    return {
        "date": req.date,
        "slots": slots,
    }


class EventRequest(BaseModel):
    requester_email: str
    subject: str
    start_time: str
    end_time: str


@app.post("/tools/create_event")
def create_event(req: EventRequest, request: Request):

    conn = sqlite3.connect(DB_PATH)

    # Prevent double booking at the database level.
    cursor = conn.execute(
        """
        SELECT COUNT(*)
        FROM appointments
        WHERE start_time = ?
        """,
        (req.start_time,),
    )

    already_booked = cursor.fetchone()[0] > 0

    if already_booked:
        conn.close()

        log_action(
            "create_event",
            "calendar",
            req.subject,
            {
                "status": "rejected",
                "reason": "slot_already_booked",
                "start_time": req.start_time,
            },
            request,
        )

        return {
            "status": "rejected",
            "reason": "slot_already_booked",
            "start_time": req.start_time,
        }

    conn.execute(
        """
        INSERT INTO appointments
        (requester_email, subject, start_time, end_time)
        VALUES (?, ?, ?, ?)
        """,
        (
            req.requester_email,
            req.subject,
            req.start_time,
            req.end_time,
        ),
    )

    conn.commit()
    conn.close()

    log_action(
        "create_event",
        "calendar",
        req.subject,
        {
            "status": "booked",
            "start_time": req.start_time,
            "end_time": req.end_time,
            "requester_email": req.requester_email,
        },
        request,
    )

    return {
        "status": "booked",
        "start_time": req.start_time,
        "end_time": req.end_time,
    }
