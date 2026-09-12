import email
import imaplib
import os
import smtplib
import ssl
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# This file uses the normal IMAP and SMTP services provided by Gmail.
# The project is using a test account, so the login details are kept in .env.
# Gmail normally requires an App Password for this kind of connection.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))


def _check_settings():
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise RuntimeError(
            "EMAIL_ADDRESS and EMAIL_PASSWORD must be set in the .env file."
        )


def _decode_header_value(value: str) -> str:
    if not value:
        return ""

    parts = decode_header(value)
    decoded = []

    for text, encoding in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(encoding or "utf8", errors="replace"))
        else:
            decoded.append(text)

    return "".join(decoded)


def _extract_body(message: email.message.Message) -> str:
    # We prefer plain text because the AI agent should receive a simple email body.
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                if "attachment" in str(part.get("Content-Disposition", "")).lower():
                    continue
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(
                        part.get_content_charset() or "utf8",
                        errors="replace",
                    )

    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(
            message.get_content_charset() or "utf8",
            errors="replace",
        )

    if isinstance(payload, str):
        return payload

    return ""


def _parse_message(raw_message: bytes, gmail_id: str) -> Dict[str, Any]:
    message = email.message_from_bytes(raw_message)

    sender_full = _decode_header_value(message.get("From", ""))
    sender_name, sender_address = parseaddr(sender_full)

    message_id = message.get("Message-ID", "").strip()

    return {
        # Message ID is more stable for our local audit record than the IMAP
        # sequence number, which can change when messages are removed.
        "gmail_id": message_id or gmail_id,
        "imap_id": gmail_id,
        "thread_id": None,
        "from": sender_full,
        "from_address": sender_address,
        "to": _decode_header_value(message.get("To", "")),
        "subject": _decode_header_value(message.get("Subject", "")),
        "date": message.get("Date", ""),
        "message_id": message_id,
        "references": message.get("References", ""),
        "body": _extract_body(message),
    }


def _connect_imap():
    _check_settings()

    mailbox = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mailbox.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mailbox.select("INBOX")
    return mailbox


def get_unread_emails() -> List[Dict[str, Any]]:
    """Read unread messages from the Gmail inbox."""
    mailbox = _connect_imap()

    try:
        status, data = mailbox.search(None, "UNSEEN")
        if status != "OK":
            raise RuntimeError("Gmail did not return the unread message list.")

        message_ids = data[0].split() if data and data[0] else []
        emails = []

        for message_number in message_ids:
            status, message_data = mailbox.fetch(
                message_number,
                "(RFC822)",
            )

            if status != "OK":
                continue

            raw_message = None
            for item in message_data:
                if isinstance(item, tuple):
                    raw_message = item[1]
                    break

            if raw_message:
                emails.append(
                    _parse_message(
                        raw_message,
                        message_number.decode("ascii", errors="replace"),
                    )
                )

        return emails

    finally:
        try:
            mailbox.close()
        except Exception:
            pass
        mailbox.logout()


def mark_as_read(message_id: str) -> None:
    """Mark one IMAP message as read after the AI has processed it successfully."""
    mailbox = _connect_imap()

    try:
        mailbox.store(message_id, "+FLAGS", "\\Seen")
    finally:
        try:
            mailbox.close()
        except Exception:
            pass
        mailbox.logout()


def send_email(
    to: str,
    subject: str,
    body: str,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an email using Gmail SMTP."""
    _check_settings()

    message = EmailMessage()
    message["From"] = EMAIL_ADDRESS
    message["To"] = to
    message["Subject"] = subject

    # These headers help Gmail understand that this message is a reply.
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to

    if references:
        message["References"] = references

    message.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        SMTP_SERVER,
        SMTP_PORT,
        context=context,
    ) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(message)

    return {
        "status": "sent",
        "from": EMAIL_ADDRESS,
        "to": to,
        "subject": subject,
        "thread_id": thread_id,
    }
