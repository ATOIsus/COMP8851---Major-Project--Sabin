import json
import os
import sqlite3

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "company.db")

st.set_page_config(
    page_title="Company AI Dashboard",
    page_icon="📊",
    layout="wide",
)


def query(sql, params=()):
    """Run a small database query and return the result as a table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


st.title("Company AI Dashboard")
st.caption(
    "A simple view of incoming email, AI decisions, actions and audit history."
)

emails = query("SELECT * FROM email_events ORDER BY id DESC")
logs = query("SELECT * FROM audit_logs ORDER BY id DESC")
appointments = query("SELECT * FROM appointments ORDER BY id DESC")

successful = 0
failed = 0
processing = 0

if not emails.empty:
    successful = int((emails["status"] == "success").sum())
    failed = int((emails["status"] == "error").sum())
    processing = int((emails["status"] == "processing").sum())

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Emails received", len(emails))
col2.metric("Emails processed", successful)
col3.metric("Actions performed", len(logs))
col4.metric("Errors", failed)
col5.metric("Appointments", len(appointments))

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("AI decisions")
    if not emails.empty:
        counts = emails["decision"].fillna("unknown").value_counts()
        st.bar_chart(counts)
    else:
        st.info("No email decisions have been recorded yet.")

with right:
    st.subheader("Tool usage")
    if not logs.empty:
        counts = logs["tool_called"].fillna("unknown").value_counts()
        st.bar_chart(counts)
    else:
        st.info("No tool activity has been recorded yet.")

st.subheader("Email activity")

if not emails.empty:
    chart_df = emails.copy()
    chart_df["processed_at"] = pd.to_datetime(
        chart_df["processed_at"],
        errors="coerce",
    )

    daily = (
        chart_df.dropna(subset=["processed_at"])
        .groupby(chart_df["processed_at"].dt.date)
        .size()
    )

    st.line_chart(daily)
else:
    st.info("No email activity has been recorded yet.")

st.subheader("Recent emails")

if not emails.empty:
    columns = [
        "id",
        "processed_at",
        "sender",
        "subject",
        "decision",
        "selected_tool",
        "status",
        "execution_id",
    ]

    visible_columns = [column for column in columns if column in emails.columns]

    st.dataframe(
        emails[visible_columns],
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No emails have been recorded yet.")

st.subheader("Email details")

if not emails.empty:
    selected_id = st.selectbox(
        "Choose an email",
        emails["gmail_id"].tolist(),
    )

    selected = emails[emails["gmail_id"] == selected_id].iloc[0]

    detail_columns = [
        ("Sender", "sender"),
        ("Subject", "subject"),
        ("Decision", "decision"),
        ("Tool", "selected_tool"),
        ("Status", "status"),
        ("Execution ID", "execution_id"),
        ("Received", "received_at"),
        ("Processed", "processed_at"),
    ]

    for label, key in detail_columns:
        st.write(f"**{label}:** {selected.get(key, '')}")

    st.write("**Tool arguments**")
    try:
        st.json(json.loads(selected.get("tool_arguments") or "{}"))
    except Exception:
        st.code(str(selected.get("tool_arguments") or ""))

    st.write("**Tool result**")
    try:
        st.json(json.loads(selected.get("tool_result") or "null"))
    except Exception:
        st.code(str(selected.get("tool_result") or ""))

    st.write("**Final response**")
    st.code(str(selected.get("final_response") or ""))

    if selected.get("error"):
        st.error(str(selected.get("error")))

st.subheader("Full audit log")

if not logs.empty:
    st.dataframe(
        logs,
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No audit logs have been recorded yet.")

st.subheader("Appointments")

if not appointments.empty:
    st.dataframe(
        appointments,
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No appointments have been recorded yet.")

st.caption(f"Messages still being processed: {processing}")
