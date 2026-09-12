import os
import requests
from contextvars import ContextVar

MCP_BASE = os.getenv("MCP_BASE", "http://localhost:8000/tools")
_execution_id = ContextVar("execution_id", default=None)
_email_id = ContextVar("email_id", default=None)


def set_execution_context(execution_id=None, email_id=None):
    _execution_id.set(execution_id)
    _email_id.set(email_id)


def _headers():
    headers = {}
    if _execution_id.get():
        headers["X-Execution-ID"] = _execution_id.get()
    if _email_id.get():
        headers["X-Email-ID"] = _email_id.get()
    return headers


def _post(name, payload):
    response = requests.post(
        f"{MCP_BASE}/{name}",
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_available_slots(date: str):
    return _post("get_available_slots", {"date": date})


def create_event(requester_email, subject, start_time, end_time):
    return _post("create_event", {
        "requester_email": requester_email,
        "subject": subject,
        "start_time": start_time,
        "end_time": end_time,
    })


def send_email(to, body, subject="Re: Your enquiry", thread_id=None, in_reply_to=None, references=None):
    return _post("send_email", {
        "to": to,
        "body": body,
        "subject": subject,
        "thread_id": thread_id,
        "in_reply_to": in_reply_to,
        "references": references,
    })


def search_documents(query):
    return _post("search_documents", {"query": query})


def call_webhook(url, data):
    return _post("call_webhook", {"url": url, "data": data})


def read_file(filename, location="internal_docs"):
    return _post("read_file", {"filename": filename, "location": location})


def write_transaction_log(entry):
    return _post("write_transaction_log", {"entry": entry})
