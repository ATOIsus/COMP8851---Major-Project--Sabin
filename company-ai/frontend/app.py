import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from agent.graph import company_ai

st.set_page_config(page_title="Company AI", page_icon="📧", layout="centered")
st.title("📧 Company AI — Corporate Executive Assistant")
st.caption("Unguarded baseline — no filtering or validation. For internal testing only.")

# A few one-click examples so you're not retyping test cases every time.
examples = {
    "Book an appointment": {
        "from": "client@example.com",
        "subject": "Meeting request",
        "body": "Can we book a call next week?",
    },
    "Ask a question (info lookup)": {
        "from": "client@example.com",
        "subject": "Pricing question",
        "body": "What's your standard call-out fee?",
    },
    "General thanks (no action needed)": {
        "from": "client@example.com",
        "subject": "Thanks",
        "body": "Just wanted to say thanks for the great service.",
    },
}

st.subheader("Try an example, or write your own")
cols = st.columns(len(examples))
for col, (label, sample) in zip(cols, examples.items()):
    if col.button(label):
        st.session_state["sender"] = sample["from"]
        st.session_state["subject"] = sample["subject"]
        st.session_state["body"] = sample["body"]

st.divider()

sender = st.text_input("From", key="sender", value=st.session_state.get("sender", "client@example.com"))
subject = st.text_input("Subject", key="subject", value=st.session_state.get("subject", "Meeting request"))
body = st.text_area("Body", key="body", value=st.session_state.get("body", "Can we book a call next week?"))

if st.button("Process email", type="primary"):
    email = {"from": sender, "subject": subject, "body": body}
    with st.spinner("Agent is reading the email and deciding what to do..."):
        result = company_ai.invoke({"email": email})

    st.success("Done.")

    # Friendly summary first — this is what makes the trace actually readable
    # instead of scrolling through raw JSON every time.
    st.subheader("What the agent decided")
    decision = result.get("reasoning", "unknown")
    tool_name = result.get("tool_call", {}).get("name", "none")
    extracted = result.get("extracted") or {}
    summary = f"**Decision:** `{decision}`  \n**Tool called:** `{tool_name}`"
    if extracted.get("date"):
        summary += f"  \n**Extracted date:** `{extracted['date']}`"
    if extracted.get("query"):
        summary += f"  \n**Extracted query:** `{extracted['query']}`"
    st.markdown(summary)

    tool_result = result.get("tool_result")
    if tool_result:
        st.subheader("Tool result")
        st.json(tool_result)

    with st.expander("Full agent trace (raw)"):
        st.json(result)