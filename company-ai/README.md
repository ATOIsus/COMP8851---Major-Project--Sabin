# Company AI

This project connects a test Gmail account to the existing Company AI agent. The agent reads incoming messages, decides what the customer needs, uses the available tools and records what happened in SQLite.

The project also has a separate Streamlit dashboard. The dashboard is useful during development because it lets you see the email count, AI decisions, actions, errors and the complete audit history in one place.

## Simple architecture

Gmail inbox

↓

IMAP email reader

↓

Company AI agent

↓

LangGraph and Llama

↓

Tool layer

↓

FastAPI tool server

↓

SQLite database

↓

Streamlit dashboard

The agent can also send a reply through Gmail SMTP.

## 1. Gmail test account

For this testing version, the project does not use Google OAuth.

The application connects to Gmail through IMAP for receiving messages and SMTP for sending messages.

Gmail normally requires an App Password for this type of connection. An App Password is different from the normal Google account password and is intended for applications that cannot use the normal sign in flow.

For safety, use a separate test Gmail account for the project. Do not use an account containing real confidential customer information.

## 2. Create the environment file

Copy `.env.example` to `.env`.

Set these values:

```text
EMAIL_ADDRESS=company-ai@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
MCP_BASE=http://127.0.0.1:8000/tools
```

Do not put the password directly into Python files. The `.env` file is already ignored by Git.

## 3. Install the packages

Open a terminal in the `company-ai` folder and run:

```bash
pip install -r requirements.txt
```

## 4. Prepare the database

Run:

```bash
python db/init_db.py
```

The database contains email events, audit records and appointments.

## 5. Start Ollama

Make sure Ollama is installed and running.

Then make sure the model is available:

```bash
ollama pull llama3.1:8b
```

## 6. Start the tool server

Open a terminal in the `company-ai` folder and run:

```bash
uvicorn mcp_server.server:app --host 127.0.0.1 --port 8000
```

Keep this terminal running.

The server stays on the local machine. Do not expose it to the public Internet while the security testing code is still permissive.

## 7. Test the email connection once

Send a simple test email to the test account.

For example:

```text
Subject: Test enquiry

Hello, I would like to know your pricing information.
```

Then run:

```bash
python run_email_agent.py --once
```

The application checks for unread messages, sends the message to the Company AI agent and records the result.

A successful flow looks like this:

Gmail

↓

IMAP

↓

Email processor

↓

Company AI

↓

search_documents

↓

FastAPI tool server

↓

SQLite audit log

## 8. Run the email listener continuously

To check the inbox every 30 seconds:

```bash
python run_email_agent.py --interval 30
```

You can change `30` to another number of seconds.

The listener only marks a message as read after the AI processing finishes successfully. If processing fails, the message stays unread so that it can be investigated and tried again.

## 9. Start the dashboard

Open another terminal and run:

```bash
streamlit run dashboard/app.py
```

The dashboard shows:

* Total emails received
* Emails processed successfully
* Actions performed
* Errors
* Appointments
* AI decisions
* Tool usage
* Email activity over time
* Details for individual emails
* Tool arguments and results
* The complete audit log

## 10. Gmail connection details

Receiving email uses:

```text
imap.gmail.com
Port 993
SSL
```

Sending email uses:

```text
smtp.gmail.com
Port 465
SSL
```

The same test account is used for both services.

## 11. Important testing note

This project is also being used for security research. The current tool server contains intentionally permissive behaviour around file access and external HTTP requests so that security experiments can be performed against a controlled baseline.

Keep the server on localhost during testing.

Use synthetic test information rather than real passwords, API keys or customer records.

For the MCP tool poisoning experiments, keep a clean version and a poisoned version so the results can be compared fairly.

## 12. Useful commands

Initialise the database:

```bash
python db/init_db.py
```

Start the tool server:

```bash
uvicorn mcp_server.server:app --host 127.0.0.1 --port 8000
```

Check the inbox once:

```bash
python run_email_agent.py --once
```

Keep checking the inbox:

```bash
python run_email_agent.py --interval 30
```

Start the dashboard:

```bash
streamlit run dashboard/app.py
```
